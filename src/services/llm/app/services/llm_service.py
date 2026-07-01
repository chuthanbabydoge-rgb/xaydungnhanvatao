"""Main LLM service for chat completions"""
import time
import uuid
import logging
from typing import AsyncGenerator, Optional, Dict, Any

from app.schemas import ChatRequest, ChatResponse, StreamingChunk
from app.services.base_provider import BaseLLMProvider
from app.services.model_router import model_router
from app.services.response_cache import response_cache
from app.db.redis import redis_manager
from app.core.exceptions import RateLimitError
from config import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    """Main LLM service for handling chat completions"""
    
    def __init__(self):
        self.settings = get_settings()
        self.router = model_router
        self.cache = response_cache
    
    async def chat_completion(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        user_tier: str = "free"
    ) -> ChatResponse:
        """Handle chat completion request"""
        
        # Generate request ID
        request_id = request.request_id or str(uuid.uuid4())
        
        # Check rate limit
        if await self._check_rate_limit(user_id):
            raise RateLimitError("Rate limit exceeded")
        
        # Check cache first
        cached_response = await self.cache.get(request)
        if cached_response:
            return cached_response
        
        # Select model
        provider, model_name = await self.router.select_model(request, user_tier)
        
        # Update request with selected model
        request.model = model_name
        
        # Process request
        start_time = time.time()
        
        try:
            response = await provider.chat_completion(request, request_id)
            
            # Cache response
            await self.cache.set(request, response)
            
            # Update rate limit
            await self._update_rate_limit(user_id, response.usage.get("total_tokens", 0))
            
            # Log usage
            await self._log_usage(user_id, request, response)
            
            logger.info(f"Chat completion successful: {request_id}")
            return response
            
        except Exception as e:
            logger.error(f"Chat completion failed: {request_id} - {e}")
            raise
    
    async def chat_completion_stream(
        self,
        request: ChatRequest,
        user_id: Optional[str] = None,
        user_tier: str = "free"
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Handle streaming chat completion request"""
        
        # Generate request ID
        request_id = request.request_id or str(uuid.uuid4())
        
        # Check rate limit
        if await self._check_rate_limit(user_id):
            raise RateLimitError("Rate limit exceeded")
        
        # Select model
        provider, model_name = await self.router.select_model(request, user_tier)
        
        # Update request with selected model
        request.model = model_name
        
        # Process streaming request
        total_tokens = 0
        
        try:
            async for chunk in provider.chat_completion_stream(request, request_id):
                yield chunk
                
                # Estimate tokens from chunk
                if chunk.choices and chunk.choices[0].get("delta", {}).get("content"):
                    total_tokens += len(chunk.choices[0]["delta"]["content"].split())
            
            # Update rate limit
            await self._update_rate_limit(user_id, total_tokens)
            
            logger.info(f"Streaming chat completion successful: {request_id}")
            
        except Exception as e:
            logger.error(f"Streaming chat completion failed: {request_id} - {e}")
            raise
    
    async def _check_rate_limit(self, user_id: Optional[str]) -> bool:
        """Check if user has exceeded rate limit"""
        if not self.settings.RATE_LIMIT_ENABLED:
            return False
        
        if not user_id:
            return False
        
        try:
            # Check requests per minute
            request_key = f"rate_limit:requests:{user_id}"
            request_count = await redis_manager.get(request_key)
            
            if request_count and request_count >= self.settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
                return True
            
            # Check tokens per minute
            token_key = f"rate_limit:tokens:{user_id}"
            token_count = await redis_manager.get(token_key)
            
            if token_count and token_count >= self.settings.RATE_LIMIT_TOKENS_PER_MINUTE:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return False
    
    async def _update_rate_limit(self, user_id: Optional[str], tokens: int):
        """Update rate limit counters"""
        if not self.settings.RATE_LIMIT_ENABLED:
            return
        
        if not user_id:
            return
        
        try:
            # Update request count
            request_key = f"rate_limit:requests:{user_id}"
            await redis_manager.increment(request_key)
            await redis_manager.expire(request_key, 60)  # 1 minute
            
            # Update token count
            token_key = f"rate_limit:tokens:{user_id}"
            await redis_manager.increment(token_key, tokens)
            await redis_manager.expire(token_key, 60)  # 1 minute
            
        except Exception as e:
            logger.error(f"Rate limit update error: {e}")
    
    async def _log_usage(
        self,
        user_id: Optional[str],
        request: ChatRequest,
        response: ChatResponse
    ):
        """Log usage statistics"""
        try:
            usage_key = f"usage:{user_id or 'anonymous'}:{time.strftime('%Y-%m-%d')}"
            
            usage_data = await redis_manager.get_hash(usage_key)
            
            if not usage_data:
                usage_data = {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "by_model": {}
                }
            
            usage_data["total_requests"] += 1
            usage_data["total_tokens"] += response.usage.get("total_tokens", 0)
            usage_data["total_cost"] += response.cost
            
            # Update by model
            model = response.model
            if model not in usage_data["by_model"]:
                usage_data["by_model"][model] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
            
            usage_data["by_model"][model]["requests"] += 1
            usage_data["by_model"][model]["tokens"] += response.usage.get("total_tokens", 0)
            usage_data["by_model"][model]["cost"] += response.cost
            
            await redis_manager.set_hash(usage_key, "data", usage_data, 86400 * 30)  # 30 days
            
        except Exception as e:
            logger.error(f"Usage logging error: {e}")
    
    async def get_usage_stats(
        self,
        user_id: Optional[str],
        period: str = "daily"
    ) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        try:
            date_suffix = time.strftime('%Y-%m-%d')
            if period == "weekly":
                # Get last 7 days
                pass
            elif period == "monthly":
                # Get last 30 days
                pass
            
            usage_key = f"usage:{user_id or 'anonymous'}:{date_suffix}"
            usage_data = await redis_manager.get_hash(usage_key)
            
            if usage_data:
                return usage_data
            
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "by_model": {}
            }
            
        except Exception as e:
            logger.error(f"Usage stats error: {e}")
            return {
                "error": str(e)
            }


# Global LLM service instance
llm_service = LLMService()
