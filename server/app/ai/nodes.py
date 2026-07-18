"""
app/ai/nodes.py — LangGraph node handlers for ShopEase customer-care agent.
Off-topic is refused without calling the LLM (saves API quota).
Shop answers use live DB results; never invent catalog/order data.
"""
import re
from typing import Any, Dict, List, Optional, TypedDict
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.config import settings
from app.core.logger import get_logger
from app.ai.router import classify_intent
from app.ai.tools import (
    db_search_products, db_track_order, db_check_return_status,
    db_get_faq, db_get_product_reviews, db_initiate_return,
)
from app.ai.prompts import (
    SYSTEM_PROMPT,
    OFF_TOPIC_REFUSAL,
    HUMAN_HANDOFF_REPLY,
    GREETING_REPLY,
)

logger = get_logger(__name__)

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "have", "what", "when",
    "where", "which", "your", "you", "can", "please", "want", "need", "show",
    "find", "looking", "about", "tell", "give", "some", "any", "me", "my", "a",
    "an", "is", "are", "do", "does", "how", "much", "many",
    # Roman Urdu fillers
    "kya", "hai", "ha", "hein", "ho", "ka", "ki", "ke", "ko", "se", "mein", "main",
    "mujhe", "mujh", "batao", "btao", "pleasee", "plz", "oye", "yaar", "bhai",
    "price", "rate", "cost", "kitna", "kitne", "kitni", "qeemat",
}

# Common typos / aliases → search tokens
TYPO_MAP = {
    "pvilion": "pavilion",
    "pavillion": "pavilion",
    "pavilon": "pavilion",
    "mac book": "macbook",
    "airpods": "headphones",
    "earphone": "headphones",
    "earbud": "headphones",
    "samsng": "samsung",
    "samung": "samsung",
    "ifone": "iphone",
    "iphon": "iphone",
    "redmi": "redmi",
    "xiomi": "xiaomi",
}


def _normalize_query_text(message: str) -> str:
    text = message.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    for wrong, right in TYPO_MAP.items():
        text = text.replace(wrong, right)
    return re.sub(r"\s+", " ", text).strip()


def _extract_search_keywords(message: str) -> str:
    """Keep brand tokens like hp/lg (len>=2) and drop filler words."""
    text = _normalize_query_text(message)
    words = []
    for w in text.split():
        if w in STOPWORDS:
            continue
        if len(w) >= 2:
            words.append(w)
    # Prefer product-ish tokens; keep up to 10 to prevent truncating long comparison details
    return " ".join(words[:10])


def _is_price_question(message: str) -> bool:
    t = message.lower()
    return any(
        x in t
        for x in ["price", "kitna", "kitne", "kitni", "qeemat", "rate", "cost", "rs", "rupees"]
    ) or bool(re.search(r"kya\s+ha[ei]?", t))


def _format_products(products: List[Dict[str, Any]], message: str = "") -> str:
    if not products:
        return (
            "As-salamu alaykum! I couldn't find matching products in our ShopEase catalog. "
            "Try searching for another name or brand (e.g. HP Pavilion, Sony headphones, Nike) or browse our store /products. Shukriya!"
        )

    price_q = _is_price_question(message)
    
    # Neuromarketing hooks builder
    def get_hooks(p: Dict[str, Any]) -> str:
        hooks = []
        stock = p.get("stock_quantity", 0)
        rating = p.get("rating", 0)
        orig_price = p.get("original_price")
        price = p.get("price", 0)
        
        # Scarcity Hook
        if 0 < stock <= 5:
            hooks.append(f"⚠️ **Hurry! Only {stock} items left!**")
        elif stock == 0:
            hooks.append("❌ **Out of stock**")
            
        # Social Proof Hook
        if rating >= 4.5:
            hooks.append("⭐ **Highly rated by customers!**")
            
        # Value Anchoring / Discount Hook
        if orig_price and orig_price > price:
            savings = int(orig_price - price)
            hooks.append(f"🔥 **Save Rs. {savings:,}! (Special Offer)**")
            
        return " · ".join(hooks) if hooks else ""

    if price_q and len(products) == 1:
        p = products[0]
        price = f"Rs. {int(p['price']):,}"
        orig = (
            f" (was Rs. {int(p['original_price']):,})"
            if p.get("original_price") and p["original_price"] > p["price"]
            else ""
        )
        stock = p.get("stock_quantity", 0)
        stock_txt = f"{stock} items left" if stock > 0 else "Out of stock"
        hook_text = get_hooks(p)
        hook_prefix = f"\n💡 {hook_text}" if hook_text else ""
        
        return (
            f"**{p['name']}** ki current price **{price}**{orig} hai.{hook_prefix}\n\n"
            f"• Brand: {p.get('brand') or '—'} · Category: {p.get('category')}\n"
            f"• Rating: ⭐ {p.get('rating', 0)} ({p.get('review_count', 0)} reviews)\n"
            f"• Stock: {stock_txt}\n\n"
            f"{(p.get('description') or '')[:160]}\n\n"
            "Apke liye isko cart me add karun ya kisi aur product ki specifications chahiye? Shukriya!"
        )

    # Multi-product list (or comparisons/recommendations)
    lines = ["Yeh products hamari live catalog se mile:\n"] if price_q else ["Here are the matching items from our catalog:\n"]
    
    # Distinguish upsells (category fallback match)
    normal_products = [p for p in products if not p.get("is_upsell")]
    upsell_products = [p for p in products if p.get("is_upsell")]

    for p in normal_products:
        price = f"Rs. {int(p['price']):,}"
        hook_text = get_hooks(p)
        hook_suffix = f" — {hook_text}" if hook_text else ""
        lines.append(
            f"• **{p['name']}** ({p.get('brand') or p.get('category')})\n"
            f"  Price: **{price}** · Rating: ⭐ {p.get('rating', 0)}{hook_suffix}"
        )
        
    if upsell_products:
        lines.append("\n🌟 **You might also like these relevant options:**")
        for p in upsell_products:
            price = f"Rs. {int(p['price']):,}"
            hook_text = get_hooks(p)
            hook_suffix = f" — {hook_text}" if hook_text else ""
            lines.append(
                f"• **{p['name']}** ({p.get('brand') or p.get('category')})\n"
                f"  Price: **{price}** · Rating: ⭐ {p.get('rating', 0)}{hook_suffix}"
            )

    lines.append("\nKisi item ki zyada detail chahiye, ya cart mein add karun? Shukriya!")
    return "\n".join(lines)


class AgentState(TypedDict):
    message: str
    history: List[Dict[str, Any]]
    intent: str
    db_results: Optional[Any]
    response: str
    session_key: str
    suggestions: List[str]


def _extract_order_ref(message: str) -> Optional[str]:
    match = re.search(r"\b((?:SE|ORD|RET)[- ]?\d{3,6})\b", message, re.IGNORECASE)
    if match:
        return re.sub(r"\s+", "", match.group(1)).upper().replace(" ", "")
    match = re.search(r"\b(\d{4,6})\b", message)
    if match:
        return match.group(1)
    return None


def _resolve_order_ref(current_msg: str, history_list: List[Dict[str, Any]]) -> Optional[str]:
    # 1. Try to extract from current message
    ref = _extract_order_ref(current_msg)
    if ref:
        return ref
    # 2. Walk history backwards to find last active order reference
    for turn in reversed(history_list):
        content = turn.get("content", "")
        found = _extract_order_ref(content)
        if found:
            return found
    return None


def _format_order(order: Dict[str, Any]) -> str:
    items = order.get("items") or []
    items_txt = ", ".join(items) if items else "See order details in My Orders"
    city = order.get("shipping_city")
    city_txt = f" to **{city}**" if city else ""
    return (
        f"As-salamu alaykum! I found order **#{order['order_number']}** in our database.\n\n"
        f"• Status: **{str(order.get('status', '')).replace('_', ' ').title()}**\n"
        f"• Courier Carrier: **{order.get('carrier')}**\n"
        f"• Tracking ID: `{order.get('tracking_number')}`\n"
        f"• Estimated Delivery: **{order.get('estimated_delivery')}**{city_txt}\n"
        f"• Total Bill: **Rs. {int(order.get('total_amount', 0)):,}** "
        f"({order.get('payment_status', 'n/a')} via {order.get('payment_method') or 'N/A'})\n"
        f"• Items: {items_txt}\n\n"
        "Shukriya! Agar aapko is order ke return ya refund ki details chahiye to batayein."
    )


def _format_return(data: Dict[str, Any]) -> str:
    if data.get("status") == "No return request submitted yet":
        return (
            f"Order **#{data.get('order_number')}** has **no return request** submitted yet. "
            f"Order Status is **{data.get('order_status')}**.\n\n"
            f"💡 **Return Policy**: ShopEase provides a hassle-free 30-day return policy for all delivered products. "
            f"Aap apna order return karna chahte hain? Sirf likhein: "
            f"*'Return karna hai SE-XXXX'* aur hum process shuru kar dete hain. Shukriya!"
        )
    return (
        f"As-salamu alaykum! Aapke order **#{data.get('order_number')}** ka return request status yeh hai:\n\n"
        f"• Return Ticket: `{data.get('return_number')}`\n"
        f"• Request Status: **{data.get('status').replace('_', ' ').title()}**\n"
        f"• Refund Amount: **Rs. {int(data.get('refund_amount') or 0):,}**\n"
        f"• Return Reason: {data.get('reason') or '—'}\n\n"
        f"💡 **Refund Info**: Refund completes within 7-10 working days, direct to EasyPaisa, JazzCash, or bank account. Shukriya!"
    )


def _format_return_initiated(data: Dict[str, Any]) -> str:
    """Confirmation template when agent successfully creates a new return request."""
    return (
        f"✅ **Return Request Successfully Created!**\n\n"
        f"As-salamu alaykum! Aapka return request hamara system me register ho gaya hai.\n\n"
        f"• 🎫 **Return Ticket**: `{data.get('return_number')}`\n"
        f"• 📦 **Order**: **#{data.get('order_number')}**\n"
        f"• 💰 **Refund Amount**: **Rs. {int(data.get('refund_amount') or 0):,}**\n"
        f"• 📋 **Status**: Requested (Under Review)\n\n"
        f"**Agla Step**: ShopEase team 1-2 business days me aapko email karegi. "
        f"Refund **7-10 working days** me EasyPaisa, JazzCash, ya bank account me transfer ho jayega. Shukriya!"
    )


def _format_reviews(reviews: List[Dict[str, Any]], product_name: str = "") -> str:
    """Format real customer review text for display."""
    if not reviews:
        return (
            f"As-salamu alaykum! Abhi tak **{product_name or 'is product'}** ke liye koi customer review "
            "hamara system me registered nahi hai. Aap product ki overall rating aur specifications "
            "product detail page par dekh sakte hain. Shukriya!"
        )
    header = f"**Customer Reviews for {reviews[0].get('product_name', product_name)}:**\n\n"
    parts = [header]
    for r in reviews[:3]:
        stars = "⭐" * r.get("rating", 5)
        parts.append(
            f"{stars} **{r.get('reviewer_name', 'Customer')}**\n"
            f"> {r.get('review_text', '')}\n"
        )
    parts.append("\nAur reviews dekhne ke liye product page visit karein. Shukriya!")
    return "\n".join(parts)


def _get_suggestions(intent: str, db_results: Any) -> List[str]:
    """Return 2-3 contextual quick-reply suggestions based on intent and results."""
    if intent == "PRODUCT_SEARCH" or intent == "PRODUCT_RECOMMENDATION":
        suggestions = ["Show me more products", "Track my order", "What's your return policy?"]
        if isinstance(db_results, list) and db_results:
            name = db_results[0].get("name", "")
            cat = db_results[0].get("category", "")
            suggestions = [
                f"Show reviews for {name[:30]}",
                f"More {cat} options",
                "Add to cart / Buy now",
            ]
        return suggestions
    elif intent == "ORDER_TRACKING":
        return ["Check return policy", "Initiate a return", "Contact support"]
    elif intent == "RETURN_ITEM":
        return ["Check refund status", "Browse products", "Contact support"]
    elif intent == "FAQ":
        return ["Track my order", "Browse products", "Contact human support"]
    elif intent == "GENERAL_CHAT":
        return ["Show laptops", "Track my order", "What's on sale?"]
    return ["Browse products", "Track order", "FAQs"]


def _format_faqs(faqs: List[Dict[str, Any]]) -> str:
    if not faqs:
        return (
            "As-salamu alaykum! ShopEase Policy ke mutabiq hum 3-5 days delivery (free on orders), "
            "Cash on Delivery (COD), EasyPaisa, JazzCash payments, 30-day hassle-free returns, aur 1-year product warranty provide karte hain. "
            "Aapko kis policy ki detail chahiye? Shukriya!"
        )
    parts = ["As-salamu alaykum! Here is the relevant policy information from ShopEase:\n"]
    for f in faqs[:3]:
        parts.append(f"**{f['question']}**\n{f['answer']}\n")
    parts.append("Agar mazeed details chahiye to kindly batayein. Shukriya!")
    return "\n".join(parts)


def build_deterministic_reply(intent: str, message: str, db_results: Any) -> Optional[str]:
    """
    Prefer DB-backed templates for factual intents (no HF needed).
    Returns None when the LLM should polish a more open reply.
    """
    if intent == "OFF_TOPIC":
        return OFF_TOPIC_REFUSAL
    if intent == "HUMAN_SUPPORT":
        return HUMAN_HANDOFF_REPLY
    if intent == "GENERAL_CHAT":
        lower = message.lower().strip()
        if any(w in lower for w in ["thank", "shukriya", "thx"]):
            return "You're welcome! If you need anything else from ShopEase — products, tracking, or returns — just ask."
        if any(w in lower for w in ["bye", "goodbye", "allah hafiz"]):
            return "Thank you for choosing ShopEase. Have a great day — we're here whenever you need us!"
        return GREETING_REPLY

    if intent in ["PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"]:
        if isinstance(db_results, dict) and db_results.get("error"):
            return db_results["error"]
        if isinstance(db_results, list):
            return _format_products(db_results, message)
        return _format_products([], message)

    if intent == "PRODUCT_REVIEW":
        if isinstance(db_results, list):
            return _format_reviews(db_results)
        return _format_reviews([])

    if intent == "ORDER_TRACKING":
        if isinstance(db_results, dict) and db_results.get("error"):
            return db_results["error"]
        if isinstance(db_results, dict) and db_results.get("order_number"):
            return _format_order(db_results)
        return (
            "I couldn't find that order in our database. "
            "Please share your order number (e.g. **SE-9821** or **ORD-1023**)."
        )

    if intent == "RETURN_ITEM":
        if isinstance(db_results, dict) and db_results.get("error"):
            return db_results["error"]
        # Return was successfully initiated → show confirmation
        if isinstance(db_results, dict) and db_results.get("success") is True:
            return _format_return_initiated(db_results)
        # Return status check result
        if isinstance(db_results, dict):
            return _format_return(db_results)
        return (
            "Aap apna return initiate karna chahte hain ya status check karna chahte hain? "
            "Kindly apna order number share karein (e.g. **SE-4392**). Shukriya!"
        )

    if intent == "FAQ":
        if isinstance(db_results, list):
            return _format_faqs(db_results)
        return _format_faqs([])

    return None


async def call_llm(prompt: str) -> str:
    """Optional LLM polish — uses Groq API as primary (Llama 3), with HuggingFace fallback."""
    if settings.GROQ_API_KEY:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 600,
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    res_data = response.json()
                    res_text = res_data["choices"][0]["message"]["content"].strip()
                    logger.info("groq_llm.success", model=settings.GROQ_MODEL)
                    return res_text
                logger.warning("groq_llm.api_error", status_code=response.status_code)
        except Exception as e:
            logger.warning("groq_llm.error", error=str(e))

    # Fallback to Hugging Face
    url = f"https://api-inference.huggingface.co/models/{settings.HF_MODEL_ID}"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 220,
            "temperature": 0.25,
            "return_full_text": False,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                res_data = response.json()
                if isinstance(res_data, list) and res_data:
                    return res_data[0].get("generated_text", "").strip()
                if isinstance(res_data, dict):
                    return res_data.get("generated_text", "").strip()
            logger.warning("hf_llm.api_error", status_code=response.status_code)
    except Exception as e:
        logger.warning("hf_llm.error", error=str(e))
    return ""


async def detect_intent_node(state: AgentState) -> Dict[str, Any]:
    intent = await classify_intent(state["message"])
    return {"intent": intent}


async def query_db_node(state: AgentState, db: AsyncSession) -> Dict[str, Any]:
    intent = state.get("intent", "GENERAL_CHAT")
    message = state["message"]
    history = state.get("history", [])
    db_results: Any = None

    # Skip DB for intents that don't need it
    if intent in ["OFF_TOPIC", "HUMAN_SUPPORT", "GENERAL_CHAT"]:
        return {"db_results": None}

    # ── Session Context Memory Helper ─────────────────────────────────────────
    def _resolve_context_query(current_msg: str) -> Optional[str]:
        """
        If user message has pronouns (this/it/ye/iska) but no product signal,
        scan last 4 turns for a product/brand name and return it as the resolved query.
        """
        lower = current_msg.lower()
        pronoun_triggers = [
            "this", " it ", "is it", "is this", "ye", "iska", "iski", "uska",
            "that one", "woh", "available", "kitna hai", "price kya",
        ]
        has_pronoun = any(p in lower for p in pronoun_triggers)
        if not has_pronoun:
            return None
        # Walk history newest-first to find last mentioned product
        for turn in reversed(history[-8:]):
            content = turn.get("content", "")
            # Look for product names/brands in previous assistant messages
            for word in content.split():
                clean = word.strip("*•:,.()").lower()
                if len(clean) >= 4 and clean not in {
                    "this", "that", "here", "with", "from", "have",
                    "your", "price", "rating", "stock", "brand",
                }:
                    return clean
        return None

    try:
        if intent in ["PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"]:
            lower_msg = message.lower()

            # Review query detection (route to review tool)
            review_kws = ["review", "reviews", "customer review", "ratings", "log kya kehte", "feedback"]
            if any(w in lower_msg for w in review_kws):
                keywords = _extract_search_keywords(message)
                db_results = await db_get_product_reviews(db, keywords)
                # Treat as PRODUCT_REVIEW intent for formatting
                return {"db_results": db_results, "intent": "PRODUCT_REVIEW"}

            # Sale/discount detection
            sale_kws = ["sale", "discount", "offer", "deal", "sasta", "discounts", "sales", "cheap"]
            if any(w in lower_msg for w in sale_kws):
                from sqlalchemy import select as sa_select
                from app.database import models as db_models
                from app.ai.tools import _product_dict
                stmt = sa_select(db_models.Product).where(
                    db_models.Product.original_price > db_models.Product.price,
                    db_models.Product.is_active.is_(True)
                ).order_by(db_models.Product.rating.desc()).limit(5)
                res = await db.execute(stmt)
                db_results = [_product_dict(p) for p in res.scalars().all()]

            # New arrivals detection — fixed: catches "new phones", "naye", "nayi" etc.
            elif any(w in lower_msg for w in [
                "new arrival", "new arrivals", "arrivals", "latest",
                "naya", "nayay", "naye", "nayi", "new product",
            ]) or (
                # Catch "new X" pattern (e.g. "new phones", "new laptops")
                re.search(r"\bnew\s+\w", lower_msg) and
                not any(w in lower_msg for w in ["renewal", "renew", "knew"])
            ):
                from sqlalchemy import select as sa_select
                from app.database import models as db_models
                from app.ai.tools import _product_dict
                stmt = sa_select(db_models.Product).where(
                    db_models.Product.is_active.is_(True)
                ).order_by(db_models.Product.created_at.desc()).limit(5)
                res = await db.execute(stmt)
                db_results = [_product_dict(p) for p in res.scalars().all()]

            else:
                # Session context: resolve pronouns to last mentioned product
                resolved = _resolve_context_query(message)
                keywords = _extract_search_keywords(message)
                if not keywords and resolved:
                    keywords = resolved
                elif resolved and len(keywords.split()) <= 2:
                    # Combine current keywords with context
                    keywords = f"{resolved} {keywords}".strip()
                db_results = await db_search_products(db, keywords)

            # Category Upselling Fallback (if exactly 1 product matched)
            if isinstance(db_results, list) and len(db_results) == 1:
                try:
                    product = db_results[0]
                    category = product.get("category")
                    product_id = product.get("id")
                    if category and product_id:
                        from sqlalchemy import select as sa_select
                        from app.database import models as db_models
                        from app.ai.tools import _product_dict
                        from uuid import UUID
                        stmt = sa_select(db_models.Product).where(
                            db_models.Product.category == category,
                            db_models.Product.id != UUID(product_id),
                            db_models.Product.is_active.is_(True)
                        ).order_by(db_models.Product.rating.desc()).limit(2)
                        alt_res = await db.execute(stmt)
                        alts = alt_res.scalars().all()
                        for alt in alts:
                            alt_dict = _product_dict(alt)
                            alt_dict["is_upsell"] = True
                            db_results.append(alt_dict)
                except Exception as upsell_err:
                    logger.warning("query_db_node.upsell_failed", error=str(upsell_err))

        elif intent == "RETURN_ITEM":
            order_ref = _resolve_order_ref(message, history)
            lower_msg = message.lower()

            # Detect INITIATION intent vs STATUS CHECK
            initiation_kws = [
                "want to return", "return karna", "return karna hai", "wapas karna",
                "initiate return", "return chahta", "return chahti", "return request",
                "return karun", "return kar", "process return", "mujhe return",
                "return lena", "wapsi karna",
            ]
            wants_initiation = any(k in lower_msg for k in initiation_kws)

            if not order_ref:
                db_results = {
                    "error": (
                        "As-salamu alaykum! Kindly apna order number share karein "
                        "(e.g. **SE-9821** ya **ORD-1023**) taake hum return process kar sakein. Shukriya!"
                    )
                }
            elif wants_initiation:
                # Extract reason from message if mentioned
                reason_kws = {
                    "damage": "Product received damaged",
                    "broken": "Product received damaged",
                    "wrong": "Wrong product received",
                    "defect": "Product has defect",
                    "not working": "Product not working",
                    "size": "Wrong size received",
                    "quality": "Quality not as expected",
                }
                reason = "Customer requested return"
                for kw, desc in reason_kws.items():
                    if kw in lower_msg:
                        reason = desc
                        break
                db_results = await db_initiate_return(db, order_ref, reason)
            else:
                # Status check
                found = await db_check_return_status(db, order_ref)
                db_results = found or {
                    "error": (
                        f"Order **{order_ref}** ke liye return details nahi mili. "
                        "Agar aapka order deliver ho chuka hai, to likhein: "
                        "*'Return karna hai {order_ref}'* aur hum process shuru kar denge. Shukriya!"
                    )
                }

        elif intent == "ORDER_TRACKING":
            order_ref = _resolve_order_ref(message, history)
            if not order_ref:
                db_results = {
                    "error": (
                        "As-salamu alaykum! Kindly apna correct order number share karein "
                        "(e.g. **SE-9821** ya **ORD-1023**) taake hum search kar sakein. Shukriya!"
                    )
                }
            else:
                found = await db_track_order(db, order_ref)
                db_results = found or {
                    "error": (
                        f"As-salamu alaykum! Mujhe system me order **{order_ref}** nahi mila. "
                        "Kindly double-check karke correct order ID enter karein. Shukriya!"
                    )
                }

        elif intent == "FAQ":
            lower = message.lower()
            focus_terms = [
                "return", "refund", "shipping", "delivery", "payment", "cod",
                "easypaisa", "jazzcash", "warranty", "contact", "hours", "cancel",
            ]
            focus = next((t for t in focus_terms if t in lower), None)
            keywords = focus or _extract_search_keywords(message) or message
            db_results = await db_get_faq(db, keywords)
            if not db_results:
                db_results = await db_get_faq(db, "")

    except Exception as e:
        logger.error("query_db_node.db_error", error=str(e))
        db_results = {
            "error": (
                "As-salamu alaykum! I'm having trouble reaching our database right now. "
                "Kindly try again in a moment, or contact support@shopease.pk. Shukriya!"
            )
        }

    return {"db_results": db_results}


def _format_offline_comparison(products: List[Dict[str, Any]]) -> str:
    """Format a clean side-by-side comparison and recommendation if the LLM is offline."""
    non_upsells = [p for p in products if not p.get("is_upsell")]
    if len(non_upsells) < 2:
        return ""

    lines = [
        "⚖️ **ShopEase Side-by-Side Comparison (Offline Mode)**\n\n"
        "As-salamu alaykum! AI comparison service temporary offline hone ki wajah se product specifications niche hain:\n"
    ]
    for p in non_upsells[:3]:
        price = f"Rs. {int(p['price']):,}"
        orig = f" ~~Rs. {int(p['original_price']):,}~~" if p.get("original_price") else ""
        lines.append(
            f"• **{p['name']}** ({p.get('brand') or 'Store'})\n"
            f"  - Price: **{price}**{orig}\n"
            f"  - Customer Rating: ⭐ {p['rating']} ({p['review_count']} reviews)\n"
            f"  - Specs: {p['description']}\n"
        )
    lines.append("\n💡 **Mera Mashwara (Recommendation):**")
    best_rated = max(non_upsells[:3], key=lambda x: x.get("rating", 0))
    cheapest = min(non_upsells[:3], key=lambda x: x.get("price", 9999999))
    
    if best_rated["id"] == cheapest["id"]:
        lines.append(
            f"- **{best_rated['name']}** sabse behtareen choice hai kyunki yeh best-rated bhi hai aur budget-friendly bhi."
        )
    else:
        lines.append(
            f"- **Best Quality**: Agar rating aur reliability priority hai, toh **{best_rated['name']}** (⭐ {best_rated['rating']}) behtar hai.\n"
            f"- **Best Budget**: Value-for-money option ke liye **{cheapest['name']}** (Rs. {int(cheapest['price']):,}) behtareen rahega."
        )
    lines.append("\nKya main inme se koi item aapke cart me add karun? Shukriya!")
    return "\n".join(lines)


async def generate_response_node(state: AgentState) -> Dict[str, Any]:
    intent = state.get("intent", "GENERAL_CHAT")
    message = state["message"]
    db_results = state.get("db_results")
    history = state.get("history", [])

    # 1) Deterministic path — preferred (accurate + zero/low API cost)
    deterministic = build_deterministic_reply(intent, message, db_results)
    if deterministic and intent in [
        "OFF_TOPIC",
        "HUMAN_SUPPORT",
        "GENERAL_CHAT",
        "ORDER_TRACKING",
        "RETURN_ITEM",
        "FAQ",
        "PRODUCT_SEARCH",
        "PRODUCT_RECOMMENDATION",
        "PRODUCT_REVIEW",
    ]:
        if intent == "GENERAL_CHAT":
            # Call Groq to reply naturally to greetings/thanks/chat with shop context and memory
            history_str = ""
            for msg in history[-6:]:
                history_str += f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}\n"
            prompt = f"""<s>[INST] {SYSTEM_PROMPT}

Recent Conversation:
{history_str}
User: {message}

Write a short, warm, and friendly response (under 45 words) in Roman Urdu or English acknowledging the user's greeting/chat.
Remember context details (like their name or current topic) if shared in the conversation history. Keep it focused on ShopEase.
STRICT RULE: Do not make up or hallucinate any custom coupon codes, sales events, or extra discount offers. [/INST]"""
            llm = await call_llm(prompt)
            if llm and len(llm) > 10:
                suggestions = _get_suggestions(intent, db_results)
                return {"response": llm, "suggestions": suggestions}
            # Fallback to static
            suggestions = _get_suggestions(intent, db_results)
            return {"response": deterministic, "suggestions": suggestions}

        # For products, optional light LLM polish only if user asked a complex compare/recommend question
        complex_ask = any(
            w in message.lower()
            for w in ["compare", "difference", "vs", "versus", "which is better", "worth", "suggest", "best", "konsa"]
        )
        if intent in ["PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"] and complex_ask and isinstance(db_results, list) and db_results:
            history_str = ""
            for msg in history[-4:]:
                history_str += f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}\n"
            prompt = f"""<s>[INST] {SYSTEM_PROMPT}

[DATABASE RESULTS — use only these products]:
{db_results}

Recent Conversation:
{history_str}
User: {message}

Write a short professional ShopEase reply comparing/recommending ONLY from the database results.
STRICT RULE: Stick strictly to the prices and discount/scarcity details in the database. Never make up or hallucinate any custom coupons, discount codes, or sales offers. [/INST]"""
            llm = await call_llm(prompt)
            if llm and len(llm) > 40:
                suggestions = _get_suggestions(intent, db_results)
                return {"response": llm, "suggestions": suggestions}
            
            # If LLM failed/offline, use the structured offline comparison template
            offline_comp = _format_offline_comparison(db_results)
            if offline_comp:
                suggestions = _get_suggestions(intent, db_results)
                return {"response": offline_comp, "suggestions": suggestions}

        # Generate contextual quick-reply suggestions
        suggestions = _get_suggestions(intent, db_results)
        return {"response": deterministic, "suggestions": suggestions}

    # 2) Fallback safety
    return {
        "response": deterministic or GREETING_REPLY,
        "suggestions": ["Browse products", "Track order", "FAQs"],
    }
