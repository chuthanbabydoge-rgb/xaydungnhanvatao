"""Response cache service for LLM responses"""
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.schemas import ChatRequest, ChatResponse
from app.db.redis import redis_manager
from app.core.exceptions import CacheError

logger = logging.getLogger(__name__)


class ResponseCache:
    """Response cache service"""
    
    def __init__(self):
        self.enabled = True
        self.cache_ttl = 3600  # 1 hour default
        self.cache_enabled_models = {"gpt-3.5-turbo", "claude-3-haiku"}
    
    def set_cache_ttl(self, ttl: int):
        """Set cache TTL in seconds"""
        self.cache_ttl = ttl
    
    def set_cache_enabled_models(self, models: set[str]):
        """Set models that can be cached"""
        self.cache_enabled_models = models
    
    def is_cacheable(self, request: ChatRequest) -> bool:
        """Check if request is cacheable"""
        if not self.enabled:
            return False
        
        if not request.enable_cache:
            return False
        
        # Only cache certain models
        if request.model not in self.cache_enabled_models:
            return False
        
        # Don't cache function calls
        if request.functions:
            return False
        
        # Don't cache streaming requests
        if request.stream:
            return False
        
        return True
    
    def generate_cache_key(self, request: ChatRequest) -> str:
        """Generate cache key from request"""
        # Create a deterministic key from request parameters
        key_data = {
            "model": request.model,
            "messages": [{"role": m.role.value, "content": m.content} for m in request.messages],
            "system_prompt": request.system_prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        hash_key = hashlib.sha256(key_string.encode()).hexdigest()
        
        return f"llm_cache:{hash_key}"
    
    async def get(self, request: ChatRequest) -> Optional[ChatResponse]:
        """Get cached response"""
        if not self.is_cacheable(request):
            return None
        
        try:
            cache_key = self.generate_cache_key(request)
            cached_data = await redis_manager.get(cache_key)
            
            if cached_data:
                logger.info(f"Cache hit for key: {cache_key}")
                
                # Update hit count
                await redis_manager.increment(f"{cache_key}:hits")
                await redis_manager.set(f"{cache_key}:last_accessed", datetime.utcnow().isoformat())
                
                return ChatResponse(**cached_data)
            
            logger.debug(f"Cache miss for key: {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, request: ChatRequest, response: ChatResponse) -> bool:
        """Cache response"""
        if not self.is_cacheable(request):
            return False
        
        try:
            cache_key = self.generate_cache_key(request)
            
            # Prepare cache data
            cache_data = response.dict()
            cache_data["cached"] = True
            cache_data["cached_at"] = datetime.utcnow().isoformat()
            
            # Store in Redis
            success = await redis_manager.set(cache_key, cache_data, self.cache_ttl)
            
            if success:
                # Initialize hit count
                await redis_manager.set(f"{cache_key}:hits", 0, self.cache_ttl)
                await redis_manager.set(f"{cache_key}:last_accessed", datetime.utcnow().isoformat(), self.cache_ttl)
                
                logger.info(f"Cached response for key: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def invalidate(self, request: ChatRequest) -> bool:
        """Invalidate cached response"""
        try:
            cache_key = self.generate_cache_key(request)
            success = await redis_manager.delete(cache_key)
            
            if success:
                # Delete hit count
                await redis_manager.delete(f"{cache_key}:hits")
                await redis_manager.delete(f"{cache_key}:last_accessed")
                
                logger.info(f"Invalidated cache for key: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
            return False
    
    async def invalidate_model(self, model_name: str) -> int:
        """Invalidate all cached responses for a model"""
        try:
            pattern = f"llm_cache:*"
            keys = await redis_manager.list_keys(pattern)
            
            count = 0
            for key in keys:
                cached_data = await redis_manager.get(key)
                if cached_data and cached_data.get("model") == model_name:
                    await redis_manager.delete(key)
                    await redis_manager.delete(f"{key}:hits")
                    await redis_manager.delete(f"{key}:last_accessed")
                    count += 1
            
            logger.info(f"Invalidated {count} cached responses for model: {model_name}")
            return count
            
        except Exception as e:
            logger.error(f"Cache invalidate model error: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            pattern = f"llm_cache:*"
            keys = await redis_manager.list_keys(pattern)
            
            total_keys = len(keys)
            total_hits = 0
            
            for key in keys:
                hits = await redis_manager.get(f"{key}:hits")
                if hits:
                    total_hits += hits
            
            hit_rate = (total_hits / total_keys) if total_keys > 0 else 0.0
            
            return {
                "total_cached_responses": total_keys,
                "total_hits": total_hits,
                "hit_rate": hit_rate,
                "cache_enabled": self.enabled,
                "cache_ttl": self.cache_ttl,
                "cache_enabled_models": list(self.cache_enabled_models)
            }
            
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {
                "error": str(e)
            }
    
    async def clear_all(self) -> int:
        """Clear all cached responses"""
        try:
            pattern = f"llm_cache:*"
            keys = await redis_manager.list_keys(pattern)
            
            count = 0
            for key in keys:
                await redis_manager.delete(key)
                await redis_manager.delete(f"{key}:hits")
                await redis_manager.delete(f"{key}:last_accessed")
                count += 1
            
            logger.info(f"Cleared {count} cached responses")
            return count
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0


# Global cache instance
response_cache = ResponseCache()
