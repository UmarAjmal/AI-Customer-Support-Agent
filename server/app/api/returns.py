"""
app/api/returns.py — Returns processing endpoints (lodging return requests and status checks).
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.database import schemas, models
from app.services import return_service, order_service

router = APIRouter(prefix="/returns", tags=["Returns"])


@router.post("", response_model=schemas.StandardResponse, status_code=status.HTTP_201_CREATED)
async def create_return_request(
    return_in: schemas.ReturnCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """File a new refund return ticket for a delivered order."""
    ret = await return_service.request_return(db, current_user.email, return_in)
    res = schemas.ReturnResponse.model_validate(ret)
    return schemas.StandardResponse(
        success=True,
        message="Return request filed successfully",
        data=res
    )


@router.get("", response_model=schemas.StandardResponse)
async def list_my_returns(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List history of returns requested by the currently logged-in caller."""
    returns = await return_service.get_user_returns(db, current_user.email)
    serialized = [schemas.ReturnResponse.model_validate(r) for r in returns]
    return schemas.StandardResponse(
        success=True,
        message="Returns log history fetched successfully",
        data=serialized
    )


@router.get("/{id}", response_model=schemas.StandardResponse)
async def get_return(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Fetch detail breakdown of a specific return request by UUID."""
    ret = await return_service.get_return_details(db, id)
    if not ret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return request with ID {id} not found."
        )
    
    order = await order_service.get_order_details(db, ret.order_id)
    if not order or (order.customer_email != current_user.email and current_user.role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this return ticket."
        )
        
    res = schemas.ReturnResponse.model_validate(ret)
    return schemas.StandardResponse(
        success=True,
        message="Return request details found",
        data=res
    )
