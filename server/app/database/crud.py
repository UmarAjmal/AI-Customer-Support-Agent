"""
app/database/crud.py — CRUD database operations matching the updated schema structure.
"""
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone, date
import uuid
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import models, schemas
from app.core.security import hash_password
from app.core.logger import get_logger

logger = get_logger(__name__)


# ─── User CRUD ────────────────────────────────────────────────────────────────
async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_in: schemas.UserRegister) -> models.User:
    hashed_pw = hash_password(user_in.password)
    user = models.User(
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        phone=user_in.phone,
        role="customer"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ─── Category CRUD ────────────────────────────────────────────────────────────
async def get_categories(db: AsyncSession) -> List[models.Category]:
    stmt = select(models.Category).order_by(models.Category.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_category_by_slug(db: AsyncSession, slug: str) -> Optional[models.Category]:
    stmt = select(models.Category).where(models.Category.slug == slug)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ─── Product CRUD ─────────────────────────────────────────────────────────────
async def get_products(
    db: AsyncSession,
    search: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None,
    skip: int = 0,
    limit: int = 12
) -> Tuple[List[models.Product], int]:
    stmt = select(models.Product).where(models.Product.is_active == True)

    if search:
        q = f"%{search}%"
        stmt = stmt.where(
            or_(
                models.Product.name.ilike(q),
                models.Product.description.ilike(q),
                models.Product.brand.ilike(q)
            )
        )

    if category:
        stmt = stmt.where(models.Product.category.ilike(category))

    if min_price is not None:
        stmt = stmt.where(models.Product.price >= min_price)

    if max_price is not None:
        stmt = stmt.where(models.Product.price <= max_price)

    # Count before pagination (reuse filters without subquery materialization cost)
    count_stmt = select(func.count()).select_from(models.Product).where(models.Product.is_active == True)
    if search:
        q = f"%{search}%"
        count_stmt = count_stmt.where(
            or_(
                models.Product.name.ilike(q),
                models.Product.description.ilike(q),
                models.Product.brand.ilike(q),
            )
        )
    if category:
        count_stmt = count_stmt.where(models.Product.category.ilike(category))
    if min_price is not None:
        count_stmt = count_stmt.where(models.Product.price >= min_price)
    if max_price is not None:
        count_stmt = count_stmt.where(models.Product.price <= max_price)

    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar_one()

    # Sorting
    if sort_by == "price_asc":
        stmt = stmt.order_by(models.Product.price.asc())
    elif sort_by == "price_desc":
        stmt = stmt.order_by(models.Product.price.desc())
    elif sort_by == "rating":
        stmt = stmt.order_by(models.Product.rating.desc())
    else:
        stmt = stmt.order_by(models.Product.is_featured.desc(), models.Product.created_at.desc())

    # Pagination
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total_count


async def get_product_by_id(db: AsyncSession, product_id: UUID) -> Optional[models.Product]:
    stmt = select(models.Product).where(models.Product.id == product_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, prod_in: schemas.ProductCreate) -> models.Product:
    product = models.Product(**prod_in.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(db: AsyncSession, product: models.Product, update_data: schemas.ProductUpdate) -> models.Product:
    for k, v in update_data.model_dump(exclude_unset=True).items():
        setattr(product, k, v)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, product: models.Product) -> None:
    await db.delete(product)
    await db.commit()


# ─── Product Reviews CRUD ─────────────────────────────────────────────────────
async def create_product_review(
    db: AsyncSession, product_id: UUID, review_in: schemas.ProductReviewCreate
) -> models.ProductReview:
    review = models.ProductReview(
        product_id=product_id,
        reviewer_name=review_in.reviewer_name,
        rating=review_in.rating,
        review_text=review_in.review_text,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def get_product_reviews(
    db: AsyncSession, product_id: UUID, limit: int = 5
) -> list[models.ProductReview]:
    stmt = (
        select(models.ProductReview)
        .where(models.ProductReview.product_id == product_id)
        .order_by(models.ProductReview.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─── Order CRUD ───────────────────────────────────────────────────────────────
async def create_order(db: AsyncSession, order_in: schemas.OrderCreate) -> models.Order:
    # 1. Deduct stock quantities for items
    for item in order_in.items:
        prod_id = item.get("product_id")
        qty = item.get("quantity", 1)
        if prod_id:
            stmt = select(models.Product).where(models.Product.id == UUID(prod_id))
            res = await db.execute(stmt)
            prod = res.scalar_one_or_none()
            if prod:
                prod.stock_quantity = max(0, prod.stock_quantity - qty)

    # 2. Create the order
    order_num = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    order = models.Order(
        order_number=order_num,
        customer_name=order_in.customer_name,
        customer_email=order_in.customer_email,
        customer_phone=order_in.customer_phone,
        items=order_in.items,
        total_amount=order_in.total_amount,
        status="processing",
        payment_method=order_in.payment_method,
        payment_status="pending",
        shipping_address=order_in.shipping_address,
        tracking_number=f"TCS-{order_num}",
        estimated_delivery=order_in.estimated_delivery or date.fromordinal(date.today().toordinal() + 4)
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_orders(db: AsyncSession, email: Optional[str] = None) -> List[models.Order]:
    stmt = select(models.Order)
    if email:
        stmt = stmt.where(models.Order.customer_email == email)
    stmt = stmt.order_by(models.Order.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_order_by_id(db: AsyncSession, order_id: UUID) -> Optional[models.Order]:
    stmt = select(models.Order).where(models.Order.id == order_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_order_by_number(db: AsyncSession, order_number: str) -> Optional[models.Order]:
    stmt = select(models.Order).where(models.Order.order_number == order_number)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_order(db: AsyncSession, order: models.Order, update_data: schemas.OrderUpdate) -> models.Order:
    for k, v in update_data.model_dump(exclude_unset=True).items():
        setattr(order, k, v)
    await db.commit()
    await db.refresh(order)
    return order


# ─── Return CRUD ──────────────────────────────────────────────────────────────
async def create_return(db: AsyncSession, return_in: schemas.ReturnCreate, refund_amount: float) -> models.Return:
    ret_num = f"RET-{uuid.uuid4().hex[:6].upper()}"
    ret = models.Return(
        return_number=ret_num,
        order_id=return_in.order_id,
        reason=return_in.reason,
        status="requested",
        refund_amount=refund_amount
    )
    db.add(ret)
    await db.commit()
    await db.refresh(ret)
    return ret


async def get_returns(db: AsyncSession, order_id: Optional[UUID] = None) -> List[models.Return]:
    stmt = select(models.Return)
    if order_id:
        stmt = stmt.where(models.Return.order_id == order_id)
    stmt = stmt.order_by(models.Return.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_return_by_id(db: AsyncSession, return_id: UUID) -> Optional[models.Return]:
    stmt = select(models.Return).where(models.Return.id == return_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_return(db: AsyncSession, ret: models.Return, update_data: schemas.ReturnUpdate) -> models.Return:
    for k, v in update_data.model_dump(exclude_unset=True).items():
        setattr(ret, k, v)
    await db.commit()
    await db.refresh(ret)
    return ret


# ─── Chat Sessions CRUD ───────────────────────────────────────────────────────
async def get_or_create_chat_session(db: AsyncSession, session_key: str) -> models.ChatSession:
    stmt = select(models.ChatSession).where(models.ChatSession.session_id == session_key)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        session = models.ChatSession(
            session_id=session_key,
            messages=[]
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    return session


async def add_chat_message(db: AsyncSession, session_id: UUID, role: str, content: str) -> models.ChatSession:
    stmt = select(models.ChatSession).where(models.ChatSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if session:
        # Load and append message to JSONB array field
        updated_messages = list(session.messages)
        updated_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        session.messages = updated_messages
        await db.commit()
        await db.refresh(session)
        
    return session


# ─── FAQ CRUD ─────────────────────────────────────────────────────────────────
async def get_faqs(db: AsyncSession, search: Optional[str] = None) -> List[models.FAQ]:
    stmt = select(models.FAQ)
    if search:
        q = f"%{search}%"
        stmt = stmt.where(
            or_(
                models.FAQ.question.ilike(q),
                models.FAQ.answer.ilike(q),
                models.FAQ.category.ilike(q)
            )
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())
