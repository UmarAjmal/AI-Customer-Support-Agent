"""
app/services/product_service.py — Business logic layer for product catalog & search.
"""
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import crud, schemas, models


async def list_products(
    db: AsyncSession,
    search: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None,
    page: int = 1,
    page_size: int = 12
) -> Tuple[List[models.Product], int]:
    skip = (page - 1) * page_size
    return await crud.get_products(
        db=db,
        search=search,
        category=category,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        skip=skip,
        limit=page_size
    )


async def get_product(db: AsyncSession, product_id: UUID) -> Optional[models.Product]:
    return await crud.get_product_by_id(db, product_id)




async def list_categories(db: AsyncSession) -> List[models.Category]:
    return await crud.get_categories(db)


async def create_new_product(db: AsyncSession, product_in: schemas.ProductCreate) -> models.Product:
    return await crud.create_product(db, product_in)


async def update_existing_product(
    db: AsyncSession, product_id: UUID, update_data: schemas.ProductUpdate
) -> Optional[models.Product]:
    product = await crud.get_product_by_id(db, product_id)
    if not product:
        return None
    return await crud.update_product(db, product, update_data)


async def remove_product(db: AsyncSession, product_id: UUID) -> bool:
    product = await crud.get_product_by_id(db, product_id)
    if not product:
        return False
    await crud.delete_product(db, product)
    return True
