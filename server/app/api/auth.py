"""
app/api/auth.py — Authentication endpoints for registration, login, and profile fetching.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.dependencies import get_db, get_current_user
from app.database import crud, schemas, models

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.StandardResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: schemas.UserRegister, db: AsyncSession = Depends(get_db)):
    """Create a new user customer account."""
    existing_user = await crud.get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )
    
    user = await crud.create_user(db, user_in)
    user_res = schemas.UserResponse.model_validate(user)
    return schemas.StandardResponse(
        success=True,
        message="User account registered successfully",
        data=user_res
    )


@router.post("/login", response_model=schemas.StandardResponse)
async def login(credentials: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate email/password and yield access + refresh tokens."""
    user = await crud.get_user_by_email(db, credentials.email)
    if not user or not security.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    access_token = security.create_access_token(subject=user.id)
    refresh_token = security.create_refresh_token(subject=user.id)
    
    token_data = schemas.Token(
        access_token=access_token,
        refresh_token=refresh_token
    )
    return schemas.StandardResponse(
        success=True,
        message="Logged in successfully",
        data=token_data
    )


@router.get("/me", response_model=schemas.StandardResponse)
async def get_me(current_user: models.User = Depends(get_current_user)):
    """Fetch profile data of the currently logged-in caller."""
    user_res = schemas.UserResponse.model_validate(current_user)
    return schemas.StandardResponse(
        success=True,
        message="User profile retrieved successfully",
        data=user_res
    )


@router.post("/logout", response_model=schemas.StandardResponse)
async def logout():
    """Invalidate session locally on client-side."""
    return schemas.StandardResponse(
        success=True,
        message="Logged out successfully (client should drop stored tokens)",
        data=None
    )
