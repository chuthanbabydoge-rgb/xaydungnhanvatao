"""
Redis connection and management
"""
import redis.asyncio as redis
from typing import Optional
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# Redis client
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """
    Initialize Redis connection
    """
    global redis_client
    
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis connection: {e}")
        raise


async def close_redis():
    """
    Close Redis connection
    """
    global redis_client
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


def get_redis():
    """
    Get Redis client instance
    """
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client
