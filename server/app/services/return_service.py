"""
app/services/return_service.py — Business logic layer for order returns and refunds.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import crud, schemas, models


async def request_return(
    db: AsyncSession, user_email: str, return_in: schemas.ReturnCreate
) -> models.Return:
    # 1. Fetch order and check ownership
    order = await crud.get_order_by_id(db, return_in.order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    
    if order.customer_email != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to return items from this order",
        )

    # 2. Check status (Only allow returns on delivered orders)
    # Note: In development/demo, we can allow processing or shipped too, but let's stick to the rule
    if order.status != "delivered" and order.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot return items for order that is '{order.status}'. Order must be delivered first.",
        )

    # 3. Check if return request already exists for this order
    existing_returns = await crud.get_returns(db, order_id=return_in.order_id)
    if existing_returns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A return request has already been submitted for this order.",
        )

    # Calculate refund amount (default to full order total)
    refund_amount = float(order.total_amount)

    # 4. Create return
    return await crud.create_return(db, return_in, refund_amount)


async def get_user_returns(db: AsyncSession, user_email: str) -> List[models.Return]:
    # Fetch user's orders first to get their IDs
    orders = await crud.get_orders(db, email=user_email)
    order_ids = [o.id for o in orders]
    
    all_returns = []
    for oid in order_ids:
        rets = await crud.get_returns(db, order_id=oid)
        all_returns.extend(rets)
    return all_returns


async def get_return_details(db: AsyncSession, return_id: UUID) -> Optional[models.Return]:
    return await crud.get_return_by_id(db, return_id)


async def update_return_request(
    db: AsyncSession, return_id: UUID, update_data: schemas.ReturnUpdate
) -> Optional[models.Return]:
    ret = await crud.get_return_by_id(db, return_id)
    if not ret:
        return None
    return await crud.update_return(db, ret, update_data)
