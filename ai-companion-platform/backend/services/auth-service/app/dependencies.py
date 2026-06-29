"""
Dependency Injection
Auth Service
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import AsyncGenerator

from app.config import settings
from app.db.session import get_db as get_postgres_db
from app.db.redis import get_redis as get_redis_client


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_postgres_db():
        yield session


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Get Redis client."""
    async for redis in get_redis_client():
        yield redis
