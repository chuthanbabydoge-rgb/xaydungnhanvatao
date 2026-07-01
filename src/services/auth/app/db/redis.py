"""
Redis Connection
Auth Service
"""

from redis.asyncio import Redis, from_url
from typing import AsyncGenerator

from app.config import settings


redis_client: Redis = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Get Redis client."""
    global redis_client
    
    if redis_client is None:
        redis_client = await from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    
    try:
        yield redis_client
    finally:
        await redis_client.close()


async def init_redis():
    """Initialize Redis connection."""
    global redis_client
    redis_client = await from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def blacklist_token(token: str, expires_in: int = 604800):
    """Add token to blacklist with expiration (default 7 days)."""
    global redis_client
    if redis_client:
        await redis_client.setex(f"blacklist:{token}", expires_in, "1")


async def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted."""
    global redis_client
    if redis_client:
        return await redis_client.exists(f"blacklist:{token}") == 1
    return False
