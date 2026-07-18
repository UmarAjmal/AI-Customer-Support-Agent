"""
app/ai/router.py — Local-first intent classification (saves HuggingFace quota).
Handles English + Roman Urdu shop queries; HF only for ambiguous cases.
"""
import re
import httpx
from app.core.config import settings
from app.core.logger import get_logger
from app.ai.prompts import INTENT_DETECTION_PROMPT

logger = get_logger(__name__)

API_URL = f"https://api-inference.huggingface.co/models/{settings.HF_MODEL_ID}"
HEADERS = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}

VALID_INTENTS = [
    "PRODUCT_SEARCH",
    "PRODUCT_RECOMMENDATION",
    "ORDER_TRACKING",
    "RETURN_ITEM",
    "FAQ",
    "HUMAN_SUPPORT",
    "GENERAL_CHAT",
    "OFF_TOPIC",
]

# Brands / product nouns (short tokens included)
PRODUCT_SIGNALS = [
    "product", "products", "item", "items", "catalog", "catalogue",
    "price", "prices", "rate", "cost", "kitna", "kitne", "kitni", "qeemat", "rs", "rupees",
    "stock", "available", "availability", "in stock", "out of stock",
    "laptop", "laptops", "phone", "phones", "mobile", "mobiles", "smartphone",
    "shoes", "shoe", "sneakers", "headphones", "headphone", "earbuds", "mouse",
    "shirt", "dress", "mug", "lamp", "charger", "powerbank", "keyboard", "monitor",
    "iphone", "samsung", "macbook", "sony", "nike", "adidas", "puma", "xiaomi",
    "pixel", "google", "dell", "hp", "pavilion", "pvilion", "anker", "logitech",
    "galaxy", "redmi", "ultraboost", "air max", "wh-1000", "xps",
    "buy", "purchase", "order this", "add to cart", "cart",
    "search", "find", "looking for", "show me", "do you have", "have you",
    "details", "specs", "specification", "review", "rating",
    # Roman Urdu signals
    "dikhao", "dikhain", "dikhayein", "chahiye", "chahye", "dhoondo", "dhandho",
    "khareedna", "kharidna", "kharid", "buy karna", "lena ha", "lena hai",
    "milega", "mileyga", "milga", "rate kya", "price kya",
]

URDU_PRICE_PATTERNS = [
    r"\bprice\b",
    r"\brate\b",
    r"\bcost\b",
    r"\bkitn[aei]\b",
    r"\bqeemat\b",
    r"\brs\.?\b",
    r"\bkya\s+ha[ei]?\b",
    r"\bkya\s+hai\b",
    r"\bkitne\s+ka\b",
    r"\bkitni\s+hai\b",
    r"\bprice\s+kya\b",
    r"\bprice\s+batao\b",
    r"\bbatao\b",
    r"\bbtao\b",
]

SHOP_KEYWORDS = PRODUCT_SIGNALS + [
    "order", "orders", "track", "tracking", "parcel", "delivery",
    "ship", "shipping", "return", "refund", "exchange", "payment", "cod",
    "easypaisa", "jazzcash", "warranty", "shop", "shopease", "recommend",
    "suggest", "faq", "policy", "support", "agent", "human", "brand",
    "category", "fashion", "electronics", "checkout",
]

OFF_TOPIC_KEYWORDS = [
    "capital of", "who is the president", "prime minister", "weather", "cricket score",
    "football", "recipe", "cook", "homework", "essay", "write code", "python script",
    "javascript", "bitcoin", "stock market", "crypto", "religion", "politics", "election",
    "joke", "poem", "story", "movie", "netflix", "chatgpt", "openai", "medical advice",
    "doctor", "lawyer", "immigration", "visa application", "translate this long",
    "solve this math", "calculus", "physics exam", "chemistry",
]

GREETING_PATTERNS = [
    r"^\s*(hi|hello|hey|yo|salam|as[- ]?salam|assalamu|aoa|good\s+(morning|afternoon|evening))\s*[!.]*\s*$",
    r"^\s*(thanks|thank you|shukriya|thx|bye|goodbye|allah hafiz|ok|okay|great)\s*[!.]*\s*$",
    r"^\s*(who are you|what can you do|help)\s*[?.!]*\s*$",
]


def _has_product_signal(text: str) -> bool:
    if any(k in text for k in PRODUCT_SIGNALS):
        return True
    if any(re.search(p, text, re.I) for p in URDU_PRICE_PATTERNS):
        return True
    # Model numbers like "15", "s24" next to brand-ish tokens already covered;
    # catch "pavilion"/"pvilion" style typos via fuzzy-ish contains
    fuzzy_brands = ["pavil", "pvil", "macbook", "iphone", "galaxy", "airmax", "ultraboost"]
    return any(b in text.replace(" ", "") for b in fuzzy_brands)


def _local_classify(message: str) -> tuple[str, float]:
    """
    Rule-based classifier. Returns (intent, confidence 0..1).
    High confidence (>=0.85) means skip HuggingFace.
    """
    text = message.strip().lower()
    if not text:
        return "GENERAL_CHAT", 0.9

    # Instant jailbreak / prompt injection block
    jailbreak_terms = [
        "ignore instructions", "ignore rules", "ignore previous", "you are now",
        "system prompt", "dan mode", "jailbreak", "developer mode", "override",
        "print your rules", "reveal your instructions", "forget your support domain",
        "write a python", "write python", "write a script", "programming code",
    ]
    if any(term in text for term in jailbreak_terms):
        return "OFF_TOPIC", 1.0

    has_order_ref = bool(re.search(r"\b(?:se|ord|ret)[- ]?\d{3,6}\b", text, re.I))

    if any(k in text for k in OFF_TOPIC_KEYWORDS):
        if not _has_product_signal(text) and not any(
            k in text for k in ["order", "product", "shopease", "return", "track", "shipping"]
        ):
            return "OFF_TOPIC", 0.95

    # Pure greetings only (short standalone) — NOT "kya ha" inside product questions
    if any(re.search(p, text, re.I) for p in GREETING_PATTERNS) and len(text.split()) <= 6:
        if not _has_product_signal(text) and not any(
            k in text for k in ["order", "return", "track", "shipping", "payment", "policy"]
        ):
            return "GENERAL_CHAT", 0.92

    if any(
        k in text
        for k in [
            "human", "real person", "live agent", "talk to agent",
            "speak to", "complaint", "manager", "insan se baat",
        ]
    ):
        return "HUMAN_SUPPORT", 0.9

    # Policy / FAQ before return-item
    if (
        any(k in text for k in ["return policy", "refund policy", "how do i return", "how to return", "can i return"])
        or (("return" in text or "refund" in text) and "policy" in text)
        or (
            ("return" in text or "refund" in text)
            and any(k in text for k in ["how", "what is", "what's", "tell me about", "kya hai", "kaisa"])
            and not has_order_ref
        )
    ):
        return "FAQ", 0.93

    if any(
        k in text
        for k in [
            "shipping", "delivery time", "payment method", "payment options",
            "cod", "cash on delivery", "easypaisa", "jazzcash", "warranty",
            "contact", "phone number", "support email", "office hours",
            "policy", "free shipping", "delivery kitne", "delivery kitni",
            "delivery charges", "charges kitne", "charges kitni", "tax kitna",
            "easy paisa", "jazz cash", "whatsapp number", "call number",
        ]
    ):
        return "FAQ", 0.9

    if any(k in text for k in ["return", "refund", "exchange", "wapis", "wapsi", "tabdeel", "badalna", "wapas"]) or (
        has_order_ref and any(k in text for k in ["return", "refund", "ret-"])
    ):
        return "RETURN_ITEM", 0.9

    if has_order_ref or any(
        k in text
        for k in [
            "track", "tracking", "where is my", "parcel", "delivery status",
            "order status", "my order", "mera order", "meraa order", "order kahan",
            "order kab", "kab aega", "kab aayega", "kab milega", "kahan pohncha", "kahan pacha",
        ]
    ):
        return "ORDER_TRACKING", 0.92

    if any(
        k in text
        for k in ["recommend", "suggest", "gift", "best for", "what should i", "konsa best", "kaunsa best"]
    ):
        return "PRODUCT_RECOMMENDATION", 0.9

    # Product search — MUST catch price/brand/Urdu asks (this was the bug)
    if _has_product_signal(text):
        return "PRODUCT_SEARCH", 0.95

    if not any(k in text for k in SHOP_KEYWORDS) and len(text.split()) > 3:
        return "OFF_TOPIC", 0.88

    if not any(k in text for k in SHOP_KEYWORDS):
        return "OFF_TOPIC", 0.8

    # Shop-related but unclear → try product search rather than greeting
    return "PRODUCT_SEARCH", 0.7


async def _hf_classify(message: str) -> str | None:
    prompt = INTENT_DETECTION_PROMPT.format(message=message)
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 12,
            "temperature": 0.1,
            "return_full_text": False,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(API_URL, json=payload, headers=HEADERS)
            if response.status_code != 200:
                logger.warning(
                    "intent.hf_failed",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                return None

            result = response.json()
            if isinstance(result, list) and result:
                text = result[0].get("generated_text", "").strip().upper()
            elif isinstance(result, dict):
                text = result.get("generated_text", "").strip().upper()
            else:
                text = str(result).strip().upper()

            for intent in VALID_INTENTS:
                if intent in text:
                    return intent
    except Exception as e:
        logger.warning("intent.hf_exception", error=str(e))
    return None


async def classify_intent(message: str) -> str:
    """Classify intent. Prefer local rules; HF only when ambiguous."""
    local_intent, confidence = _local_classify(message)

    if confidence >= 0.85:
        logger.info("intent.classified", intent=local_intent, source="local", confidence=confidence)
        return local_intent

    hf_intent = await _hf_classify(message)
    if hf_intent:
        if local_intent == "OFF_TOPIC" and hf_intent == "GENERAL_CHAT":
            logger.info("intent.classified", intent="OFF_TOPIC", source="local_override")
            return "OFF_TOPIC"
        # Prefer local product signal over HF greeting mistakes
        if local_intent == "PRODUCT_SEARCH" and hf_intent in ["GENERAL_CHAT", "OFF_TOPIC"]:
            logger.info("intent.classified", intent="PRODUCT_SEARCH", source="local_override")
            return "PRODUCT_SEARCH"
        logger.info("intent.classified", intent=hf_intent, source="hf_api")
        return hf_intent

    logger.info("intent.classified", intent=local_intent, source="local_fallback", confidence=confidence)
    return local_intent
