"""Redis connection and cache management"""
import json
import hashlib
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
import logging

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis connection and cache manager"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.pool: Optional[ConnectionPool] = None
        self.settings = get_settings()
    
    async def connect(self):
        """Create Redis connection pool"""
        if self.redis is not None:
            return
        
        logger.info(f"Connecting to Redis: {self.settings.REDIS_URL}")
        
        self.pool = ConnectionPool.from_url(
            self.settings.REDIS_URL,
            max_connections=self.settings.REDIS_MAX_CONNECTIONS,
            encoding="utf-8",
            decode_responses=True,
        )
        
        self.redis = Redis(connection_pool=self.pool)
        
        # Test connection
        await self.redis.ping()
        
        logger.info("Redis connection established")
    
    async def disconnect(self):
        """Close Redis connections"""
        if self.redis is None:
            return
        
        logger.info("Closing Redis connection")
        
        await self.redis.close()
        await self.pool.close()
        
        self.redis = None
        self.pool = None
        
        logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if self.redis is None:
            return None
        
        try:
            value = await self.redis.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis"""
        if self.redis is None:
            return False
        
        try:
            ttl = ttl or self.settings.REDIS_CACHE_TTL
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if self.redis is None:
            return False
        
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if self.redis is None:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment value in Redis"""
        if self.redis is None:
            return 0
        
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis increment error: {e}")
            return 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        if self.redis is None:
            return False
        
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False
    
    async def get_hash(self, key: str, field: Optional[str] = None) -> Any:
        """Get hash field from Redis"""
        if self.redis is None:
            return None
        
        try:
            if field:
                value = await self.redis.hget(key, field)
                if value:
                    return json.loads(value)
                return None
            else:
                hash_data = await self.redis.hgetall(key)
                return {k: json.loads(v) for k, v in hash_data.items()}
        except Exception as e:
            logger.error(f"Redis get_hash error: {e}")
            return None
    
    async def set_hash(self, key: str, field: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set hash field in Redis"""
        if self.redis is None:
            return False
        
        try:
            serialized = json.dumps(value)
            await self.redis.hset(key, field, serialized)
            
            if ttl:
                await self.redis.expire(key, ttl)
            
            return True
        except Exception as e:
            logger.error(f"Redis set_hash error: {e}")
            return False
    
    async def delete_hash(self, key: str, field: Optional[str] = None) -> bool:
        """Delete hash field from Redis"""
        if self.redis is None:
            return False
        
        try:
            if field:
                await self.redis.hdel(key, field)
            else:
                await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete_hash error: {e}")
            return False
    
    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern"""
        if self.redis is None:
            return []
        
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            return keys
        except Exception as e:
            logger.error(f"Redis list_keys error: {e}")
            return []
    
    def generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters"""
        key_data = f"{prefix}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()


# Global Redis instance
redis_manager = RedisManager()


async def init_redis():
    """Initialize Redis connection"""
    await redis_manager.connect()


async def close_redis():
    """Close Redis connection"""
    await redis_manager.disconnect()
