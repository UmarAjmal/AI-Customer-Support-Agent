"""
app/api/users.py — Profiles management endpoints.
"""
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.database import schemas, models

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=schemas.StandardResponse)
async def read_user_me(current_user: models.User = Depends(get_current_user)):
    """Fetch current user model details."""
    res = schemas.UserResponse.model_validate(current_user)
    return schemas.StandardResponse(
        success=True,
        message="Active profile fetched successfully",
        data=res
    )
