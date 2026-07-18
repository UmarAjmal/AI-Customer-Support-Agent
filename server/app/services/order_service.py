"""
app/services/order_service.py — Business logic layer for placing, tracking, and managing orders.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import crud, schemas, models


async def place_order(
    db: AsyncSession, user_email: str, user_name: str, order_in: schemas.OrderCreate
) -> models.Order:
    if not order_in.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item",
        )

    # Validate each item in the request
    for item in order_in.items:
        pid = item.get("product_id")
        qty = item.get("quantity", 1)
        if not pid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each item must have a valid product_id"
            )
        
        try:
            prod_uuid = UUID(pid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID format for product ID: {pid}"
            )

        prod = await crud.get_product_by_id(db, prod_uuid)
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {pid} not found",
            )
            
        if prod.stock_quantity < qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product '{prod.name}'. Available: {prod.stock_quantity}, Requested: {qty}",
            )

    # Set user details from login credentials if not filled in order schema
    if not order_in.customer_email:
        order_in.customer_email = user_email
    if not order_in.customer_name:
        order_in.customer_name = user_name

    return await crud.create_order(db, order_in)


async def get_user_orders(db: AsyncSession, email: str) -> List[models.Order]:
    return await crud.get_orders(db, email=email)


async def get_order_details(db: AsyncSession, order_id: UUID) -> Optional[models.Order]:
    return await crud.get_order_by_id(db, order_id)


async def track_order_by_id(db: AsyncSession, order_id: UUID) -> Optional[models.Order]:
    return await crud.get_order_by_id(db, order_id)


async def update_order_status(
    db: AsyncSession, order_id: UUID, update_data: schemas.OrderUpdate
) -> Optional[models.Order]:
    order = await crud.get_order_by_id(db, order_id)
    if not order:
        return None
    return await crud.update_order(db, order, update_data)
