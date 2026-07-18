"""
app/core/dependencies.py — Reusable FastAPI dependency injection.
"""
from typing import AsyncGenerator, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.logger import get_logger
from app.database.db import AsyncSessionFactory
from app.database import crud, models

logger = get_logger(__name__)

# ── Bearer token extractor ────────────────────────────────────────────────────
_bearer = HTTPBearer(auto_error=False)


# ── DB Session dependency ──────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, closed automatically after the request."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Current user dependency ────────────────────────────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract and verify Bearer JWT.
    Returns the User ORM object for the authenticated caller.
    Raises HTTP 401 if token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    user_id: str = payload.get("sub", "")

    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    user = await crud.get_user_by_id(db, uid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[models.User]:
    """
    Extract and verify Bearer JWT if present.
    Returns the User ORM object if authenticated, or None if guest.
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub", "")
        uid = UUID(user_id)
        return await crud.get_user_by_id(db, uid)
    except Exception:
        return None


async def get_current_active_user(current_user=Depends(get_current_user)):
    """Raise 403 if the account has been deactivated."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )
    return current_user


async def get_current_admin(current_user=Depends(get_current_active_user)):
    """Raise 403 if the caller is not an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
