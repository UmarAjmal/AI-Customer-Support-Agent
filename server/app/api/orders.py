"""
app/api/orders.py — Ordering process endpoints (placing, tracking, and details).
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, get_current_user_optional
from app.core import ttl_cache
from app.database import schemas, models, crud
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=schemas.StandardResponse, status_code=status.HTTP_201_CREATED)
async def place_new_order(
    order_in: schemas.OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional)
):
    """Place a new order check-out, updating inventory stocks."""
    user_email = current_user.email if current_user else order_in.customer_email
    user_name = current_user.full_name if current_user else order_in.customer_name

    if not user_email or not user_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="customer_email and customer_name are required for guest checkout."
        )

    order = await order_service.place_order(db, user_email, user_name, order_in)
    
    # Invalidate cached demo orders list so updates show up in real-time
    ttl_cache.invalidate("orders:")
    
    res = schemas.OrderResponse.model_validate(order)
    return schemas.StandardResponse(
        success=True,
        message="Order placed successfully",
        data=res
    )


@router.get("/demo", response_model=schemas.StandardResponse)
async def list_demo_orders(response: Response, db: AsyncSession = Depends(get_db)):
    """Public demo list of storefront orders (no auth) for UI + agent widgets."""
    cached = ttl_cache.get("orders:demo")
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["Cache-Control"] = "public, max-age=20"
        return schemas.StandardResponse(
            success=True,
            message="Demo orders fetched successfully",
            data=cached,
        )

    orders = await crud.get_orders(db, email=None)
    serialized = [schemas.OrderResponse.model_validate(o).model_dump(mode="json") for o in orders]
    ttl_cache.set("orders:demo", serialized, 30.0)
    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = "public, max-age=20"
    return schemas.StandardResponse(
        success=True,
        message="Demo orders fetched successfully",
        data=serialized,
    )


@router.get("", response_model=schemas.StandardResponse)
async def list_my_orders(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List purchase history of the currently logged-in caller."""
    orders = await order_service.get_user_orders(db, current_user.email)
    serialized = [schemas.OrderResponse.model_validate(o) for o in orders]
    return schemas.StandardResponse(
        success=True,
        message="Orders history fetched successfully",
        data=serialized
    )


@router.get("/{id}", response_model=schemas.StandardResponse)
async def get_order(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Fetch detail breakdown of a specific order card by UUID."""
    order = await order_service.get_order_details(db, id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {id} not found."
        )

    # Ownership via customer_email (Order model has no user_id column)
    is_owner = (
        order.customer_email
        and order.customer_email.lower() == current_user.email.lower()
    )
    if not is_owner and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this order details."
        )

    res = schemas.OrderResponse.model_validate(order)
    return schemas.StandardResponse(
        success=True,
        message="Order found",
        data=res
    )


@router.post("/track", response_model=schemas.StandardResponse)
async def track_order(
    track_req: schemas.OrderUpdate, # Using OrderUpdate or general tracking request body
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Query shipment delivery details about an active tracking transaction."""
    # Custom tracking request schema or extract ID from parameter
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Please provide order ID in the tracking endpoint /orders/{id} or check with the AI support agent."
    )
