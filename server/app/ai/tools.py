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


async def db_search_products(db: AsyncSession, query: str) -> List[Dict[str, Any]]:
    """
    Search active products with token OR matching + light typo tolerance.
    Example: "HP Pvilion 15 price" → tokens hp, pavilion, 15
    """
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

    # OR across tokens (any token match in name/brand/category/description)
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
    products = list(result.scalars().all())

    # Rank: prefer products matching more tokens in name/brand
    def score(p: models.Product) -> int:
        name = (p.name or "").lower()
        brand = (p.brand or "").lower()
        cat = (p.category or "").lower()
        blob = f"{name} {brand} {cat}"
        s = 0
        for t in tokens:
            if t in name:
                s += 4
            elif t in brand:
                s += 4
            elif t in blob:
                s += 1
        if q_norm in name:
            s += 6
        # Prefer fuller name overlap
        overlap = sum(1 for t in tokens if t in name)
        s += overlap * 2
        return s

    products.sort(key=score, reverse=True)
    ranked = [p for p in products if score(p) > 0] or products

    # If query includes a known brand, keep products matching that brand first
    brand_tokens = {
        "hp", "dell", "apple", "samsung", "sony", "nike", "adidas", "puma",
        "xiaomi", "google", "anker", "logitech", "iphone", "macbook",
    }
    brands_in_q = [t for t in tokens if t in brand_tokens]
    if brands_in_q:
        def brand_ok(p: models.Product) -> bool:
            blob = f"{p.name} {p.brand or ''}".lower()
            return any(b in blob for b in brands_in_q)

        branded = [p for p in ranked if brand_ok(p)]
        if branded:
            ranked = branded

    # For tight brand+model queries, prefer top match only when clearly ahead
    if len(ranked) > 1 and score(ranked[0]) >= score(ranked[1]) + 3:
        ranked = ranked[:1]

    return [_product_dict(p) for p in ranked[:5]]


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
