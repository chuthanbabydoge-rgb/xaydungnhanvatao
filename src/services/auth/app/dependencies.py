"""
Dependency Injection
Auth Service
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import AsyncGenerator, Optional

from app.config import settings
from app.db.session import get_db as get_postgres_db
from app.db.redis import get_redis as get_redis_client
from app.core.security import verify_token_async
from app.models.user import User
from sqlalchemy import select


security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_postgres_db():
        yield session


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Get Redis client."""
    async for redis in get_redis_client():
        yield redis


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    try:
        token = credentials.credentials
        payload = await verify_token_async(token, token_type="access")
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user from JWT token (optional)."""
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = await verify_token_async(token, token_type="access")
        user_id = payload.get("sub")

        if not user_id:
            return None

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            return None

        return user

    except Exception:
        return None
