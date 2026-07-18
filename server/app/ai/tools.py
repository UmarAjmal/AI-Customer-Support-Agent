"""
app/ai/tools.py — Live Supabase/Postgres tools for the ShopEase support agent.
Never invent data — only return what exists in the database.
"""
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.database import models


def _derive_carrier(tracking: Optional[str]) -> str:
    if not tracking:
        return "ShopEase Logistics"
    t = tracking.upper()
    if t.startswith("TCS"):
        return "TCS"
    if t.startswith("DHL"):
        return "DHL Express"
    if t.startswith("FX") or t.startswith("FEDEX"):
        return "FedEx"
    return "ShopEase Logistics"


def _product_dict(p: models.Product) -> Dict[str, Any]:
    return {
        "id": str(p.id),
        "name": p.name,
        "description": (p.description or "")[:220],
        "price": float(p.price),
        "original_price": float(p.original_price) if p.original_price else None,
        "category": p.category,
        "brand": p.brand,
        "image_url": p.image_url,
        "stock_quantity": p.stock_quantity,
        "rating": float(p.rating),
        "review_count": p.review_count,
        "is_featured": p.is_featured,
    }


import math
from collections import Counter

class SimpleTFIDF:
    def __init__(self, products_list: List[Dict[str, Any]]):
        self.products = products_list
        self.doc_tokens = []
        self.vocab = set()
        self.num_docs = len(products_list)
        
        # Tokenize and build vocabulary
        for p in products_list:
            text = f"{p.get('name', '')} {p.get('brand', '') or ''} {p.get('category', '') or ''} {p.get('description', '') or ''}".lower()
            tokens = [t for t in re.split(r"\W+", text) if len(t) >= 2]
            self.doc_tokens.append(tokens)
            self.vocab.update(tokens)
            
        self.vocab = sorted(list(self.vocab))
        self.vocab_index = {w: i for i, w in enumerate(self.vocab)}
        
        # Compute IDF
        self.idf = {}
        for token in self.vocab:
            df = sum(1 for tokens in self.doc_tokens if token in tokens)
            self.idf[token] = math.log((1 + self.num_docs) / (1 + df)) + 1.0
            
        # Vectorize all products
        self.doc_vectors = []
        for tokens in self.doc_tokens:
            self.doc_vectors.append(self._vectorize(tokens))

    def _vectorize(self, tokens: List[str]) -> Dict[int, float]:
        counts = Counter(tokens)
        vec = {}
        total_words = len(tokens) if tokens else 1
        for token, count in counts.items():
            if token in self.vocab_index:
                tf = count / total_words
                vec[self.vocab_index[token]] = tf * self.idf[token]
        return vec

    def search(self, query: str, top_n: int = 5) -> List[tuple[Dict[str, Any], float]]:
        query_tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) >= 2]
        if not query_tokens:
            return []
            
        query_vec = self._vectorize(query_tokens)
        q_sum_sq = sum(val ** 2 for val in query_vec.values())
        if q_sum_sq == 0.0:
            return []
        q_norm = math.sqrt(q_sum_sq)
        
        scored_products = []
        for idx, doc_vec in enumerate(self.doc_vectors):
            dot = 0.0
            for term_idx, q_val in query_vec.items():
                if term_idx in doc_vec:
                    dot += q_val * doc_vec[term_idx]
                    
            d_sum_sq = sum(val ** 2 for val in doc_vec.values())
            d_norm = math.sqrt(d_sum_sq) if d_sum_sq > 0 else 0.0
            
            sim = (dot / (q_norm * d_norm)) if (q_norm > 0 and d_norm > 0) else 0.0
            if sim > 0.02:
                scored_products.append((self.products[idx], sim))
                
        scored_products.sort(key=lambda x: x[1], reverse=True)
        return scored_products[:top_n]


_tfidf_index: Optional[SimpleTFIDF] = None

async def _init_tfidf(db: AsyncSession):
    global _tfidf_index
    if _tfidf_index is not None:
        return
    try:
        stmt = select(models.Product).where(models.Product.is_active.is_(True))
        result = await db.execute(stmt)
        products_db = result.scalars().all()
        products_list = [_product_dict(p) for p in products_db]
        if products_list:
            _tfidf_index = SimpleTFIDF(products_list)
    except Exception as e:
        # Graceful fallback if query fails
        _tfidf_index = None


async def db_search_products(db: AsyncSession, query: str) -> List[Dict[str, Any]]:
    """
    Search active products using a Hybrid RAG search (Lexical SQL + Cosine Similarity TF-IDF vector).
    """
    await _init_tfidf(db)
    base = and_(models.Product.is_active.is_(True))

    q = (query or "").strip()
    if not q or q in {"%", "%%"}:
        stmt = (
            select(models.Product)
            .where(base)
            .order_by(models.Product.is_featured.desc(), models.Product.rating.desc())
            .limit(5)
        )
        result = await db.execute(stmt)
        return [_product_dict(p) for p in result.scalars().all()]

    # Typo normalize
    typo_map = {
        "pvilion": "pavilion",
        "pavillion": "pavilion",
        "pavilon": "pavilion",
        "samsng": "samsung",
        "ifone": "iphone",
        "xiomi": "xiaomi",
    }
    q_norm = q.lower()
    for wrong, right in typo_map.items():
        q_norm = q_norm.replace(wrong, right)

    tokens = [t for t in re.split(r"\s+", q_norm) if len(t) >= 2]
    if not tokens:
        tokens = [q_norm]

    # 1. Lexical SQL Match
    clauses = []
    for t in tokens:
        like = f"%{t}%"
        clauses.extend(
            [
                models.Product.name.ilike(like),
                models.Product.brand.ilike(like),
                models.Product.category.ilike(like),
                models.Product.description.ilike(like),
            ]
        )

    stmt = select(models.Product).where(base, or_(*clauses)).limit(25)
    result = await db.execute(stmt)
    lexical_db = list(result.scalars().all())
    lexical_matches = [_product_dict(p) for p in lexical_db]

    # 2. Vector Cosine Similarity Match
    vector_matches = []
    if _tfidf_index:
        vector_matches = _tfidf_index.search(q_norm, top_n=10)

    # 3. Hybrid Fusion scoring
    merged_map = {}
    for doc, sim in vector_matches:
        merged_map[doc["id"]] = {"doc": doc, "vector_score": sim, "lexical_score": 0.0}

    for doc in lexical_matches:
        lex_score = 1.0
        if doc["id"] in merged_map:
            merged_map[doc["id"]]["lexical_score"] = lex_score
        else:
            merged_map[doc["id"]] = {"doc": doc, "vector_score": 0.0, "lexical_score": lex_score}

    hybrid_ranked = []
    for item in merged_map.values():
        doc = item["doc"]
        v_score = item["vector_score"]
        l_score = item["lexical_score"]

        # Boost brand and exact name overlaps
        brand_boost = 0.0
        name_lower = doc["name"].lower()
        brand_lower = (doc.get("brand") or "").lower()
        for token in tokens:
            if token in name_lower:
                brand_boost += 0.2
            if brand_lower and token in brand_lower:
                brand_boost += 0.3

        hybrid_score = (v_score * 0.6) + (l_score * 0.4) + brand_boost
        hybrid_ranked.append((doc, hybrid_score))

    hybrid_ranked.sort(key=lambda x: x[1], reverse=True)
    ranked = [x[0] for x in hybrid_ranked if x[1] > 0.02] or [x[0] for x in hybrid_ranked]

    return ranked[:5]


async def db_track_order(db: AsyncSession, query_str: str) -> Optional[Dict[str, Any]]:
    """Track an order by order_number (SE-/ORD-) or UUID."""
    clean = query_str.strip().upper().replace(" ", "")
    candidates = {clean}
    digits = re.sub(r"[^A-Z0-9]", "", clean)
    if digits and not clean.startswith(("SE-", "ORD-", "RET-")):
        candidates.add(f"SE-{digits}")
        candidates.add(f"ORD-{digits}")
        candidates.add(digits)

    stmt = select(models.Order).where(models.Order.order_number.in_(list(candidates)))

    try:
        order_uuid = UUID(query_str.strip())
        stmt = select(models.Order).where(
            or_(models.Order.id == order_uuid, models.Order.order_number.in_(list(candidates)))
        )
    except ValueError:
        pass

    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        return None

    items = order.items if isinstance(order.items, list) else []
    item_summary = [
        f"{i.get('name', 'Item')} x{i.get('quantity', 1)}"
        for i in items
        if isinstance(i, dict)
    ]

    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "status": order.status,
        "total_amount": float(order.total_amount),
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "carrier": _derive_carrier(order.tracking_number),
        "tracking_number": order.tracking_number or "Pending assignment",
        "estimated_delivery": (
            order.estimated_delivery.isoformat()
            if order.estimated_delivery
            else "Usually 3–5 business days"
        ),
        "items": item_summary,
        "shipping_city": (order.shipping_address or {}).get("city")
        if isinstance(order.shipping_address, dict)
        else None,
    }


async def db_check_return_status(db: AsyncSession, query_str: str) -> Optional[Dict[str, Any]]:
    """Return request status for an order number."""
    clean = query_str.strip().upper().replace(" ", "")
    candidates = {clean}
    digits = re.sub(r"[^A-Z0-9]", "", clean)
    if digits and not clean.startswith(("SE-", "ORD-", "RET-")):
        candidates.add(f"SE-{digits}")
        candidates.add(f"ORD-{digits}")

    if clean.startswith("RET"):
        stmt_ret = select(models.Return).where(
            or_(
                models.Return.return_number == clean,
                models.Return.return_number == f"RET-{digits}",
            )
        )
        ret = (await db.execute(stmt_ret)).scalar_one_or_none()
        if ret:
            order = (
                await db.execute(select(models.Order).where(models.Order.id == ret.order_id))
            ).scalar_one_or_none()
            return {
                "return_number": ret.return_number,
                "order_number": order.order_number if order else None,
                "status": ret.status,
                "refund_amount": float(ret.refund_amount) if ret.refund_amount else 0.0,
                "reason": ret.reason,
                "created_at": ret.created_at.isoformat(),
            }

    stmt = select(models.Order).where(models.Order.order_number.in_(list(candidates)))
    order = (await db.execute(stmt)).scalar_one_or_none()
    if not order:
        return None

    ret = (
        await db.execute(select(models.Return).where(models.Return.order_id == order.id))
    ).scalar_one_or_none()

    if not ret:
        return {
            "order_number": order.order_number,
            "order_status": order.status,
            "status": "No return request submitted yet",
            "note": "Eligible delivered orders can request a return within 30 days.",
        }

    return {
        "return_number": ret.return_number,
        "order_number": order.order_number,
        "status": ret.status,
        "refund_amount": float(ret.refund_amount) if ret.refund_amount else 0.0,
        "reason": ret.reason,
        "created_at": ret.created_at.isoformat(),
    }


async def db_get_faq(db: AsyncSession, query: str) -> List[Dict[str, Any]]:
    """Query FAQ policies from the database."""
    q = (query or "").strip()
    if not q or q in {"%", "%%"}:
        stmt = select(models.FAQ).order_by(models.FAQ.created_at.desc()).limit(5)
    else:
        like = f"%{q}%"
        tokens = [t for t in q.split() if len(t) > 2][:4]
        clauses = [
            models.FAQ.question.ilike(like),
            models.FAQ.answer.ilike(like),
            models.FAQ.category.ilike(like),
        ]
        for t in tokens:
            clauses.append(models.FAQ.question.ilike(f"%{t}%"))
            clauses.append(models.FAQ.category.ilike(f"%{t}%"))
        stmt = select(models.FAQ).where(or_(*clauses)).limit(4)

    result = await db.execute(stmt)
    faqs = result.scalars().all()
    return [
        {"question": f.question, "answer": f.answer, "category": f.category}
        for f in faqs
    ]


async def db_get_product_reviews(
    db: AsyncSession, query: str, limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Fetch real review text for a product by name/brand keyword.
    Returns list of {reviewer_name, rating, review_text, product_name}.
    """
    if not query:
        return []

    tokens = [t for t in re.split(r"\s+", query.lower()) if len(t) >= 2]
    if not tokens:
        return []

    # First find the matching product(s)
    name_clauses = []
    for t in tokens:
        like = f"%{t}%"
        name_clauses.extend([
            models.Product.name.ilike(like),
            models.Product.brand.ilike(like),
        ])

    prod_stmt = (
        select(models.Product)
        .where(models.Product.is_active.is_(True), or_(*name_clauses))
        .limit(3)
    )
    prod_result = await db.execute(prod_stmt)
    products = prod_result.scalars().all()

    if not products:
        return []

    product_ids = [p.id for p in products]
    product_name_map = {p.id: p.name for p in products}

    # Fetch reviews for those products
    rev_stmt = (
        select(models.ProductReview)
        .where(models.ProductReview.product_id.in_(product_ids))
        .order_by(models.ProductReview.rating.desc(), models.ProductReview.created_at.desc())
        .limit(limit)
    )
    rev_result = await db.execute(rev_stmt)
    reviews = rev_result.scalars().all()

    return [
        {
            "product_name": product_name_map.get(r.product_id, "Product"),
            "reviewer_name": r.reviewer_name,
            "rating": r.rating,
            "review_text": r.review_text,
        }
        for r in reviews
    ]


async def db_initiate_return(
    db: AsyncSession, order_ref: str, reason: str = "Customer requested return"
) -> Dict[str, Any]:
    """
    Full return initiation pipeline:
    1. Find order by number
    2. Check eligibility (status must be delivered/completed)
    3. Check no existing return
    4. Create return record → RET-XXXXXX
    Returns structured dict with success/error info.
    """
    # Step 1: Resolve order
    clean = order_ref.strip().upper().replace(" ", "")
    digits = re.sub(r"[^A-Z0-9]", "", clean)
    candidates = {clean, f"SE-{digits}", f"ORD-{digits}", digits}

    stmt = select(models.Order).where(models.Order.order_number.in_(list(candidates)))
    try:
        order_uuid = UUID(order_ref.strip())
        stmt = select(models.Order).where(
            or_(models.Order.id == order_uuid, models.Order.order_number.in_(list(candidates)))
        )
    except (ValueError, AttributeError):
        pass

    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        return {
            "success": False,
            "error": (
                f"As-salamu alaykum! Order **{order_ref}** hamara system me nahi mila. "
                "Kindly apna correct order number share karein (e.g. **SE-9821** ya **ORD-1023**). Shukriya!"
            ),
        }

    # Step 2: Eligibility check
    eligible_statuses = {"delivered", "completed"}
    if order.status.lower() not in eligible_statuses:
        return {
            "success": False,
            "error": (
                f"Order **#{order.order_number}** abhi **{order.status.replace('_',' ').title()}** status me hai. "
                "Return sirf **delivered** orders ke liye available hai. "
                "Jab order deliver ho jaye to return initiate kar saktay hain. Shukriya!"
            ),
        }

    # Step 3: Check existing return
    existing_stmt = select(models.Return).where(models.Return.order_id == order.id)
    existing_result = await db.execute(existing_stmt)
    existing_return = existing_result.scalar_one_or_none()

    if existing_return:
        return {
            "success": False,
            "already_exists": True,
            "return_number": existing_return.return_number,
            "status": existing_return.status,
            "error": (
                f"Order **#{order.order_number}** ke liye pehle se return request **{existing_return.return_number}** "
                f"exist karti hai — status: **{existing_return.status.replace('_',' ').title()}**. "
                "Agar aur help chahiye to humse sampark karein. Shukriya!"
            ),
        }

    # Step 4: Create return record
    import uuid as _uuid
    ret_num = f"RET-{_uuid.uuid4().hex[:6].upper()}"
    new_return = models.Return(
        return_number=ret_num,
        order_id=order.id,
        reason=reason,
        status="requested",
        refund_amount=float(order.total_amount),
    )
    db.add(new_return)
    await db.commit()
    await db.refresh(new_return)

    return {
        "success": True,
        "return_number": ret_num,
        "order_number": order.order_number,
        "refund_amount": float(order.total_amount),
        "status": "requested",
        "reason": reason,
    }
