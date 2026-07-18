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
from app.ai.tools import db_search_products, db_track_order, db_check_return_status, db_get_faq
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
    # Prefer product-ish tokens; keep up to 6
    return " ".join(words[:6])


def _is_price_question(message: str) -> bool:
    t = message.lower()
    return any(
        x in t
        for x in ["price", "kitna", "kitne", "kitni", "qeemat", "rate", "cost", "rs", "rupees"]
    ) or bool(re.search(r"kya\s+ha[ei]?", t))


def _format_products(products: List[Dict[str, Any]], message: str = "") -> str:
    if not products:
        return (
            "I couldn't find matching products in our ShopEase catalog. "
            "Try another name/brand (e.g. HP Pavilion, Sony headphones, Nike) or browse /products."
        )

    price_q = _is_price_question(message)
    if price_q and len(products) == 1:
        p = products[0]
        price = f"Rs. {int(p['price']):,}"
        orig = (
            f" (was Rs. {int(p['original_price']):,})"
            if p.get("original_price")
            else ""
        )
        stock = p.get("stock_quantity", 0)
        stock_txt = f"{stock} in stock" if stock > 0 else "Out of stock"
        return (
            f"**{p['name']}** ki current price **{price}**{orig} hai.\n\n"
            f"• Brand: {p.get('brand') or '—'} · Category: {p.get('category')}\n"
            f"• Rating: ⭐ {p.get('rating', 0)} ({p.get('review_count', 0)} reviews)\n"
            f"• Stock: {stock_txt}\n\n"
            f"{(p.get('description') or '')[:160]}\n\n"
            "Cart mein add karna hai ya kisi aur product ka price chahiye?"
        )

    lines = ["Yeh products hamari live catalog se mile:\n"] if price_q else ["Here are matching items from our live catalog:\n"]
    for p in products:
        price = f"Rs. {int(p['price']):,}"
        stock = p.get("stock_quantity", 0)
        stock_txt = f"{stock} in stock" if stock > 0 else "Out of stock"
        lines.append(
            f"• **{p['name']}** ({p.get('brand') or p.get('category')})\n"
            f"  **{price}** · ⭐ {p.get('rating', 0)} ({p.get('review_count', 0)} reviews) · {stock_txt}"
        )
    lines.append("\nKisi item ki zyada detail chahiye, ya cart mein add karun?")
    return "\n".join(lines)


class AgentState(TypedDict):
    message: str
    history: List[Dict[str, Any]]
    intent: str
    db_results: Optional[Any]
    response: str
    session_key: str


def _extract_order_ref(message: str) -> Optional[str]:
    match = re.search(r"\b((?:SE|ORD|RET)[- ]?\d{3,6})\b", message, re.IGNORECASE)
    if match:
        return re.sub(r"\s+", "", match.group(1)).upper().replace(" ", "")
    match = re.search(r"\b(\d{4,6})\b", message)
    if match:
        return match.group(1)
    return None


def _format_order(order: Dict[str, Any]) -> str:
    items = order.get("items") or []
    items_txt = ", ".join(items) if items else "See order details in My Orders"
    city = order.get("shipping_city")
    city_txt = f" to **{city}**" if city else ""
    return (
        f"I found order **#{order['order_number']}** in our system.\n\n"
        f"• Status: **{str(order.get('status', '')).replace('_', ' ')}**\n"
        f"• Courier: **{order.get('carrier')}**\n"
        f"• Tracking: `{order.get('tracking_number')}`\n"
        f"• Estimated delivery: **{order.get('estimated_delivery')}**{city_txt}\n"
        f"• Total: **Rs. {int(order.get('total_amount', 0)):,}** "
        f"({order.get('payment_status', 'n/a')} / {order.get('payment_method') or 'N/A'})\n"
        f"• Items: {items_txt}\n\n"
        "Need a return check or anything else on this order?"
    )


def _format_return(data: Dict[str, Any]) -> str:
    if data.get("status") == "No return request submitted yet":
        return (
            f"Order **#{data.get('order_number')}** currently has **no return request**. "
            f"Order status: **{data.get('order_status')}**. "
            f"{data.get('note', '')} "
            "Share your order number if you'd like guidance on starting a return."
        )
    return (
        f"Return update for order **#{data.get('order_number')}**:\n\n"
        f"• Return ticket: `{data.get('return_number')}`\n"
        f"• Status: **{data.get('status')}**\n"
        f"• Refund amount: **Rs. {int(data.get('refund_amount') or 0):,}**\n"
        f"• Reason: {data.get('reason') or '—'}\n"
    )


def _format_faqs(faqs: List[Dict[str, Any]]) -> str:
    if not faqs:
        return (
            "I can help with shipping (free 3–5 days), payments (COD / EasyPaisa / JazzCash / cards), "
            "30-day returns, warranty, and contact details. Which topic do you need?"
        )
    parts = ["Here's what our ShopEase policy says:\n"]
    for f in faqs[:3]:
        parts.append(f"**{f['question']}**\n{f['answer']}\n")
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
        if isinstance(db_results, list):
            return _format_products(db_results, message)
        return _format_products([], message)

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
        if isinstance(db_results, dict):
            return _format_return(db_results)
        return (
            "To check a return, please share your order number (e.g. **SE-4392**) "
            "or return ticket (e.g. **RET-1001**)."
        )

    if intent == "FAQ":
        if isinstance(db_results, list):
            return _format_faqs(db_results)
        return _format_faqs([])

    return None


async def call_llm(prompt: str) -> str:
    """Optional LLM polish — used sparingly for complex shop replies."""
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
    db_results: Any = None

    # Skip DB for intents that don't need it
    if intent in ["OFF_TOPIC", "HUMAN_SUPPORT", "GENERAL_CHAT"]:
        return {"db_results": None}

    try:
        if intent in ["PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"]:
            keywords = _extract_search_keywords(message)
            db_results = await db_search_products(db, keywords)

        elif intent in ["ORDER_TRACKING", "RETURN_ITEM"]:
            order_ref = _extract_order_ref(message)
            if not order_ref:
                db_results = {
                    "error": (
                        "Please share your order number so I can look it up "
                        "(e.g. **SE-9821** or **ORD-1023**)."
                    )
                }
            elif intent == "ORDER_TRACKING":
                found = await db_track_order(db, order_ref)
                db_results = found or {
                    "error": (
                        f"I couldn't find order **{order_ref}** in our system. "
                        "Double-check the number or try another (e.g. SE-9821)."
                    )
                }
            else:
                found = await db_check_return_status(db, order_ref)
                db_results = found or {
                    "error": (
                        f"No return record found for **{order_ref}**. "
                        "If this was a delivered order, I can guide you on starting a return."
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
                "I'm having trouble reaching our store database right now. "
                "Please try again in a moment, or email support@shopease.pk."
            )
        }

    return {"db_results": db_results}


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
    ]:
        # For products, optional light LLM polish only if HF is healthy AND user asked a complex compare question
        complex_ask = any(
            w in message.lower()
            for w in ["compare", "difference", "vs", "versus", "which is better", "worth"]
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

Write a short professional ShopEase reply comparing/recommending ONLY from the database results. [/INST]"""
            llm = await call_llm(prompt)
            if llm and len(llm) > 40:
                return {"response": llm}
        return {"response": deterministic}

    # 2) Fallback safety
    return {
        "response": deterministic
        or GREETING_REPLY
    }
