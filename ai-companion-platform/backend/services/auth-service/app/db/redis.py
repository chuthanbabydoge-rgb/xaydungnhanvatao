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
