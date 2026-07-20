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
from app.ai.router import classify_intent, _local_classify
from app.ai.tools import (
    db_search_products, db_track_order, db_check_return_status,
    db_get_faq, db_get_product_reviews, db_initiate_return,
    db_get_user_profile, db_get_upsell_recommendations,
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


URDU_ENGLISH_SYNONYMS = {
    "garmi": "summer",
    "garmiyon": "summer",
    "sardi": "winter jacket",
    "sardiyon": "winter jacket",
    "sasta": "discount sale",
    "sasti": "discount sale",
    "saste": "discount sale",
    "achha": "featured rating",
    "achhi": "featured rating",
    "achhe": "featured rating",
    "kapde": "fashion shirt dress",
    "kapra": "fashion shirt dress",
    "kapray": "fashion shirt dress",
    "joota": "shoes sneakers",
    "jootay": "shoes sneakers",
    "mobile": "mobiles phone",
    "mobiles": "mobiles phone",
    "earphone": "headphones",
    "earbuds": "headphones",
}


def _extract_search_keywords(message: str) -> str:
    """Keep brand tokens like hp/lg (len>=2), drop filler words, and expand synonyms for Hybrid RAG search."""
    text = _normalize_query_text(message)
    words = []
    expanded = []
    for w in text.split():
        if w in STOPWORDS:
            continue
        if len(w) >= 2:
            words.append(w)
            if w in URDU_ENGLISH_SYNONYMS:
                expanded.extend(URDU_ENGLISH_SYNONYMS[w].split())
                
    # Combine original keywords with expanded synonyms
    all_tokens = words + expanded
    seen = set()
    unique_tokens = [x for x in all_tokens if not (x in seen or seen.add(x))]
    
    return " ".join(unique_tokens[:10])


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
    next_agent: str


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
    # 2. Walk history backwards — check user messages first, then assistant messages
    # This allows recalling order numbers the agent already mentioned (multi-turn context)
    for turn in reversed(history_list):
        if turn.get("role") == "user":
            found = _extract_order_ref(turn.get("content", ""))
            if found:
                return found
    for turn in reversed(history_list):
        if turn.get("role") == "assistant":
            found = _extract_order_ref(turn.get("content", ""))
            if found:
                return found
    return None


def _is_already_greeted(history: List[Dict[str, Any]]) -> bool:
    """Returns True if the assistant has already responded at least once in this session."""
    return any(m.get("role") == "assistant" for m in history)


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
            "max_tokens": 200,
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


def _extract_user_name(history: List[Dict[str, Any]], current_msg: str) -> str:
    combined = [current_msg] + [m.get("content", "") for m in reversed(history) if m.get("role") == "user"]
    question_fillers = {"kya", "kab", "kon", "kaun", "kis", "koon", "what", "who", "kya hai", "kya ha", "nam kya", "naam kya"}
    for text in combined:
        lower = text.lower()
        m1 = re.search(r"\bmera\s+na+m\s+([a-z0-9 ]+?)(?:\s+ha|hai|ba?ta|$)|\bmera\s+na+m\s+([a-z0-9 ]+)", lower)
        if m1:
            val = m1.group(1) or m1.group(2)
            if val and val.strip().lower() not in question_fillers:
                return val.strip().title()
        m2 = re.search(r"\bmy\s+name\s+is\s+([a-z0-9 ]+?)(?:$|\.)", lower)
        if m2:
            val = m2.group(1)
            if val and val.strip().lower() not in question_fillers:
                return val.strip().title()
        m3 = re.search(r"\bi\s+am\s+([a-z0-9 ]+?)(?:$|\.)", lower)
        if m3:
            val = m3.group(1)
            if val and val.strip().lower() not in question_fillers:
                return val.strip().title()
    return "Valued Customer"


def _resolve_context_query(current_msg: str, history_list: List[Dict[str, Any]]) -> Optional[str]:
    lower = current_msg.lower()
    pronoun_triggers = [
        "this", " it ", "is it", "is this", "ye", "iska", "iski", "uska",
        "that one", "woh", "available", "kitna hai", "price kya",
    ]
    has_pronoun = any(p in lower for p in pronoun_triggers)
    if not has_pronoun:
        return None
    # Walk history newest-first to find last mentioned product
    for turn in reversed(history_list[-8:]):
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


async def get_user_profile(db: Optional[AsyncSession], name: str) -> Dict[str, Any]:
    """
    Fetch live user profile from DB. Falls back to a lightweight mock if:
    - db is not available
    - no order record found for this customer name
    """
    if db is not None:
        try:
            live = await db_get_user_profile(db, name)
            if live:
                return live
        except Exception:
            pass

    # Graceful mock fallback for anonymous / unrecognised users
    clean_name = name if name != "Valued Customer" else "Guest"
    return {
        "full_name": clean_name,
        "email": "",
        "phone": "",
        "city": "",
        "recent_purchases": [],
        "active_cart": [],
        "preferred_categories": [],
    }


# Keep alias so existing calls to get_mock_user_profile still work
def get_mock_user_profile(name: str) -> Dict[str, Any]:
    clean_name = name if name != "Valued Customer" else "Guest"
    return {
        "full_name": clean_name,
        "email": "",
        "phone": "",
        "city": "",
        "recent_purchases": [],
        "active_cart": [],
        "preferred_categories": [],
    }


def _detect_sentiment(current_msg: str, history: List[Dict[str, Any]]) -> str:
    text = current_msg.lower()
    for m in history[-4:]:
        if m.get("role") == "user":
            text += " " + m.get("content", "").lower()
            
    negative_words = [
        "angry", "disappointed", "worst", "bad ", "slow", "late", "scam", "cheat",
        "ghalat", "bekar", "bakwas", "kharab", "waste", "useless", "annoyed", "frustrated",
        "disappoint", "shoking", "rubbish", "poor", "frazool", "fazool", "sad"
    ]
    if any(w in text for w in negative_words):
        return "FRUSTRATED"
    return "NORMAL"


SUPERVISOR_SYSTEM_PROMPT = """You are the Captain (Supervisor) of the ShopEase support agent team.
Your job is to analyze the user message and history, and route to the correct specialized sub-agent:

- PRODUCT_AGENT: For product searches, brand availability, specifications, recommendations, comparisons, or customer reviews.
- ORDER_AGENT: For order tracking, delivery status, refund status, or returning/exchanging items.
- FAQ_AGENT: For general shop policies, shipping speeds, payment options, COD, contact details, or office hours.
- FINISH: For general greetings, introductions, small talk, acknowledgments ("thank you", "bye"), or off-topic questions.

Output ONLY the target label (PRODUCT_AGENT, ORDER_AGENT, FAQ_AGENT, or FINISH)."""


async def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Captain/Supervisor agent. Decides next worker routing or exits directly for off-topic/general chat.
    """
    message = state["message"]
    history = state.get("history", [])

    # 1. API COST OPTIMIZATION: Raw order code bypass
    is_raw_code = bool(re.match(r"^\s*(?:se|ord|ret)[- ]?\d{3,6}\s*$", message.strip(), re.I))
    if is_raw_code:
        return {"next_agent": "ORDER_AGENT"}

    # 2. API COST OPTIMIZATION: Local classifier check (Bypasses LLM for off-topic and escalations)
    local_intent, _ = _local_classify(message)
    if local_intent == "OFF_TOPIC":
        return {
            "next_agent": "FINISH",
            "intent": "OFF_TOPIC",
            "response": OFF_TOPIC_REFUSAL,
            "suggestions": ["Browse products", "Track order", "FAQs"]
        }
    if local_intent == "HUMAN_SUPPORT":
        return {
            "next_agent": "FINISH",
            "intent": "HUMAN_SUPPORT",
            "response": HUMAN_HANDOFF_REPLY,
            "suggestions": ["Browse products", "Track order", "FAQs"]
        }

    # 3. Call LLM Supervisor to route
    history_str = ""
    for msg in history[-4:]:
        history_str += f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}\n"

    prompt = f"""<s>[INST] {SUPERVISOR_SYSTEM_PROMPT}

Recent Conversation History:
{history_str}
User Message: {message}

Route Label: [/INST]"""

    route = await call_llm(prompt)
    route_clean = route.strip().upper()

    next_agent = "FINISH"
    for candidate in ["PRODUCT_AGENT", "ORDER_AGENT", "FAQ_AGENT", "FINISH"]:
        if candidate in route_clean:
            next_agent = candidate
            break

    # If FINISH, generate general chat response directly
    response = ""
    suggestions = ["Browse products", "Track order", "FAQs"]
    if next_agent == "FINISH":
        user_name = _extract_user_name(history, message)
        profile = get_mock_user_profile(user_name)

        already_greeted = _is_already_greeted(history)
        greeting_instruction = (
            "Do NOT start with 'As-salamu alaykum' or any greeting — the user has already been welcomed."
            if already_greeted else
            "Start with 'As-salamu alaykum' as a warm welcome."
        )
        chat_prompt = f"""<s>[INST] {SYSTEM_PROMPT}

Recent Conversation History:
{history_str}
User Message: {message}
Customer Name: {profile['full_name']}

Instructions:
- Write a short, warm, and friendly response (under 45 words) in Roman Urdu or English.
- Address them by their name (e.g. Umar bhai) if appropriate.
- Keep it focused on ShopEase. Do not offer promotions.
- {greeting_instruction} [/INST]"""
        response = await call_llm(chat_prompt)
        if not response:
            response = build_deterministic_reply("GENERAL_CHAT", message, None) or GREETING_REPLY
        suggestions = _get_suggestions("GENERAL_CHAT", None)

    return {
        "next_agent": next_agent,
        "response": response,
        "suggestions": suggestions,
        "intent": "GENERAL_CHAT" if next_agent == "FINISH" else next_agent
    }


async def product_agent_node(state: AgentState, db: AsyncSession) -> Dict[str, Any]:
    """
    Catalog worker. Specialized in specifications, recommendations, and reviews.
    """
    message = state["message"]
    history = state.get("history", [])

    # 1. Fetch DB Results
    lower_msg = message.lower()
    db_results = None
    intent = "PRODUCT_SEARCH"

    # Check reviews
    review_kws = ["review", "reviews", "customer review", "ratings", "log kya kehte", "feedback"]
    if any(w in lower_msg for w in review_kws):
        keywords = _extract_search_keywords(message)
        db_results = await db_get_product_reviews(db, keywords)
        intent = "PRODUCT_REVIEW"
    # Check sales
    elif any(w in lower_msg for w in ["sale", "discount", "offer", "deal", "sasta", "cheap"]):
        from sqlalchemy import select as sa_select
        from app.database import models as db_models
        from app.ai.tools import _product_dict
        stmt = sa_select(db_models.Product).where(
            db_models.Product.original_price > db_models.Product.price,
            db_models.Product.is_active.is_(True)
        ).order_by(db_models.Product.rating.desc()).limit(3)
        res = await db.execute(stmt)
        db_results = [_product_dict(p) for p in res.scalars().all()]
    else:
        # Standard Hybrid Search
        resolved = _resolve_context_query(message, history)
        keywords = _extract_search_keywords(message)
        if not keywords and resolved:
            keywords = resolved
        elif resolved and len(keywords.split()) <= 2:
            keywords = f"{resolved} {keywords}".strip()
        db_results = await db_search_products(db, keywords)

        # Category upselling fallback
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
            except Exception:
                pass

    # 2. Build RAG context & user profile (real DB first, mock fallback)
    user_name = _extract_user_name(history, message)
    profile = await get_user_profile(db, user_name)
    sentiment = _detect_sentiment(message, history)
    suggestions = _get_suggestions(intent, db_results)

    # Proactive upsell: suggest products from preferred categories
    if profile["preferred_categories"] and not suggestions:
        try:
            bought_names = [item for p in profile["recent_purchases"] for item in p.get("items", [])]
            upsell = await db_get_upsell_recommendations(db, profile["preferred_categories"], exclude_names=bought_names)
            if upsell:
                suggestions = [f"Check out: {u['name']}" for u in upsell[:2]] + suggestions
        except Exception:
            pass

    context_str = (
        f"LOGGED-IN CUSTOMER PROFILE:\n"
        f"- Name: {profile['full_name']}\n"
        f"- Active Cart: {', '.join(profile['active_cart'])}\n"
        f"- Purchase History:\n"
    )
    for p in profile["recent_purchases"]:
        context_str += f"  * Order {p['order_number']}: {', '.join(p['items'])} ({p['status']})\n"
    context_str += "\n"

    if intent == "PRODUCT_REVIEW" and db_results:
        context_str += "CUSTOMER REVIEWS:\n"
        for r in db_results[:3] if isinstance(db_results, list) else []:
            context_str += f"- ⭐{r.get('rating')} by {r.get('reviewer_name')}: {r.get('review_text')}\n"
    else:
        context_str += "DATABASE PRODUCTS AVAILABLE:\n"
        for p in db_results[:3] if isinstance(db_results, list) else []:
            orig = f" (Original Price: Rs. {int(p['original_price']):,})" if p.get("original_price") and p["original_price"] > p["price"] else ""
            upsell = " [Alternative]" if p.get("is_upsell") else ""
            context_str += f"- {p['name']}{upsell}: Rs. {int(p['price']):,}{orig}. Rating: ⭐{p['rating']}. Stock: {p['stock_quantity']}. Info: {p['description']}\n"

    # 3. Call LLM
    history_str = ""
    for msg in history[-6:]:
        history_str += f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}\n"

    already_greeted = _is_already_greeted(history)
    greeting_instruction = (
        "Do NOT start with 'As-salamu alaykum' — the user was already welcomed earlier."
        if already_greeted else
        "Start with 'As-salamu alaykum'."
    )
    sentiment_instructions = ""
    if sentiment == "FRUSTRATED":
        sentiment_instructions = (
            "The customer is frustrated. Adjust tone to be highly empathetic and apologetic. Do NOT offer promotions or upselling."
        )
        suggestions = ["Contact support", "Check return policy", "Track my order"]
    else:
        sentiment_instructions = (
            "Be conversational and match their language (Roman Urdu or English). You may friendly reference their profile history if they ask."
        )

    prompt = f"""<s>[INST] {SYSTEM_PROMPT}

[DATABASE / RAG CONTEXT]:
{context_str}

Recent Conversation History:
{history_str}
User Message: {message}

Instructions:
- Provide a direct, natural response under 50 words in Roman Urdu/English recommending or comparing products.
- Address them by name '{profile['full_name']}' if appropriate.
- Stick strictly to prices and specs in database. Never make up discount codes.
- {greeting_instruction}
- {sentiment_instructions} [/INST]"""

    response = await call_llm(prompt)
    if not response:
        response = build_deterministic_reply(intent, message, db_results) or GREETING_REPLY
    # Sentiment escalation: append human handoff offer if frustrated
    if sentiment == "FRUSTRATED" and "contact" not in response.lower():
        response += "\n\nAgar aapko further help chahiye to hum aapko human support agent se connect kar sakte hain. 🙏"

    return {
        "response": response,
        "suggestions": suggestions,
        "db_results": db_results,
        "intent": intent
    }


async def order_agent_node(state: AgentState, db: AsyncSession) -> Dict[str, Any]:
    """
    Orders worker. Handles tracking, checking returns, and return requests.
    """
    message = state["message"]
    history = state.get("history", [])

    # 1. Fetch DB Results
    order_ref = _resolve_order_ref(message, history)
    lower_msg = message.lower()
    intent = "ORDER_TRACKING"

    # Check if return creation or return status check
    initiation_kws = ["return", "wapas", "refund", "exchange", "wapsi", "initiate return"]
    is_return = any(k in lower_msg for k in initiation_kws) or (order_ref and "ret-" in order_ref.lower())

    if is_return:
        intent = "RETURN_ITEM"
        wants_initiation = any(k in lower_msg for k in ["want to return", "return karna", "wapas karna", "initiate"])
        if not order_ref:
            db_results = {
                "error": "Kindly apna order number share karein (e.g. SE-4392) taake return process ho sake. Shukriya!"
            }
        elif wants_initiation:
            db_results = await db_initiate_return(db, order_ref, "Customer requested return")
        else:
            db_results = await db_check_return_status(db, order_ref) or {
                "error": f"Order {order_ref} ke liye return record nahi mila."
            }
    else:
        # Order tracking
        if not order_ref:
            db_results = {
                "error": "Kindly apna correct order number share karein (e.g. SE-4392) taake track kiya ja sake. Shukriya!"
            }
        else:
            db_results = await db_track_order(db, order_ref) or {
                "error": f"Order {order_ref} system me nahi mila. Check/re-enter correct ID."
            }

    # 2. Build RAG context & user profile (real DB first, mock fallback)
    user_name = _extract_user_name(history, message)
    profile = await get_user_profile(db, user_name)
    sentiment = _detect_sentiment(message, history)
    suggestions = _get_suggestions(intent, db_results)

    context_str = (
        f"LOGGED-IN CUSTOMER PROFILE:\n"
        f"- Name: {profile['full_name']}\n"
        f"- Active Cart: {', '.join(profile['active_cart'])}\n"
    )
    if isinstance(db_results, dict) and db_results.get("error"):
        context_str += f"ERROR/STATUS: {db_results.get('error')}\n"
    else:
        context_str += f"DATABASE ORDER/RETURN DATA:\n{db_results}\n"

    # 3. Call LLM
    history_str = ""
    for msg in history[-6:]:
        history_str += f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}\n"

    already_greeted = _is_already_greeted(history)
    greeting_instruction = (
        "Do NOT start with 'As-salamu alaykum' — the user was already welcomed earlier."
        if already_greeted else
        "Start with 'As-salamu alaykum'."
    )
    sentiment_instructions = ""
    if sentiment == "FRUSTRATED":
        sentiment_instructions = (
            "The customer is frustrated. Adjust tone to be highly empathetic and apologetic. Do NOT offer promotions. Focus strictly on order status/return."
        )
        suggestions = ["Contact support", "Check return policy", "Track my order"]
    else:
        sentiment_instructions = (
            "Be direct, polite, and match their language (Roman Urdu or English). Assist them with the order/return status facts."
        )

    prompt = f"""<s>[INST] {SYSTEM_PROMPT}

[DATABASE / RAG CONTEXT]:
{context_str}

Recent Conversation History:
{history_str}
User Message: {message}

Instructions:
- Write a direct, natural response under 50 words in Roman Urdu/English about order/return status.
- Address them by name '{profile['full_name']}' if appropriate.
- Stick strictly to tracking numbers and facts in context. Never hallucinate refund amounts.
- {greeting_instruction}
- {sentiment_instructions} [/INST]"""

    response = await call_llm(prompt)
    if not response:
        response = build_deterministic_reply(intent, message, db_results) or GREETING_REPLY
    # Sentiment escalation: offer human handoff if frustrated
    if sentiment == "FRUSTRATED" and "contact" not in response.lower():
        response += "\n\nAgar aapko further help chahiye to hum aapko human support agent se connect kar sakte hain. 🙏"

    return {
        "response": response,
        "suggestions": suggestions,
        "db_results": db_results,
        "intent": intent
    }


async def faq_agent_node(state: AgentState, db: AsyncSession) -> Dict[str, Any]:
    """
    Policy worker. Answers FAQ policies regarding shipping, payment, contact, etc.
    """
    message = state["message"]
    history = state.get("history", [])

    # 1. Fetch DB Results
    lower_msg = message.lower()
    focus_terms = ["return", "refund", "shipping", "delivery", "payment", "cod", "easypaisa", "jazzcash", "warranty"]
    focus = next((t for t in focus_terms if t in lower_msg), None)
    keywords = focus or _extract_search_keywords(message) or message
    db_results = await db_get_faq(db, keywords)
    if not db_results:
        db_results = await db_get_faq(db, "")

    # 2. Build RAG context & user profile (real DB first, mock fallback)
    user_name = _extract_user_name(history, message)
    profile = await get_user_profile(db, user_name)
    sentiment = _detect_sentiment(message, history)
    suggestions = _get_suggestions("FAQ", db_results)

    context_str = "RELEVANT FAQ POLICY:\n"
    for f in db_results[:2] if isinstance(db_results, list) else []:
        context_str += f"Q: {f['question']}\nA: {f['answer']}\n\n"

    # 3. Call LLM
    history_str = ""
    for msg in history[-6:]:
        history_str += f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}\n"

    already_greeted = _is_already_greeted(history)
    greeting_instruction = (
        "Do NOT start with 'As-salamu alaykum' — the user was already welcomed earlier."
        if already_greeted else
        "Start with 'As-salamu alaykum'."
    )
    sentiment_instructions = ""
    if sentiment == "FRUSTRATED":
        sentiment_instructions = (
            "The customer is frustrated. Adjust tone to be highly empathetic and apologetic. Answer their query clearly and directly."
        )
        suggestions = ["Contact support", "Check return policy", "Track my order"]
    else:
        sentiment_instructions = (
            "Be helpful and match their language (Roman Urdu or English) explaining the shop policies."
        )

    prompt = f"""<s>[INST] {SYSTEM_PROMPT}

[DATABASE / RAG CONTEXT]:
{context_str}

Recent Conversation History:
{history_str}
User Message: {message}

Instructions:
- Write a direct, natural response under 50 words in Roman Urdu/English explaining the shop policy facts.
- Address them by name '{profile['full_name']}' if appropriate.
- Stick strictly to policy facts in context. Never make up discount rules.
- {greeting_instruction}
- {sentiment_instructions} [/INST]"""

    response = await call_llm(prompt)
    if not response:
        response = build_deterministic_reply("FAQ", message, db_results) or GREETING_REPLY
    # Sentiment escalation: offer human handoff if frustrated
    if sentiment == "FRUSTRATED" and "contact" not in response.lower():
        response += "\n\nAgar aapko further help chahiye to hum aapko human support agent se connect kar sakte hain. 🙏"

    return {
        "response": response,
        "suggestions": suggestions,
        "db_results": db_results,
        "intent": "FAQ"
    }
