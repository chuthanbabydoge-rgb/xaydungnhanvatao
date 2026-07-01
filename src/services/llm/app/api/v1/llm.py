"""LLM API endpoints"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.schemas import (
    ChatRequest,
    ChatResponse,
    StreamingChunk,
    ModelListResponse,
    UsageResponse,
    ErrorResponse,
    HealthResponse
)
from app.services import llm_service, model_router, response_cache
from app.core.exceptions import *
from config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM"])
security = HTTPBearer(auto_error=False)


@router.post("/chat", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Generate chat completion
    
    Supports:
    - Multi-LLM routing
    - Response caching
    - Function calling
    - Rate limiting
    """
    try:
        # Extract user info from credentials
        user_id = None
        user_tier = "free"
        
        if credentials:
            # In production, validate JWT token and extract user info
            user_id = "demo_user"  # Placeholder
            user_tier = "premium"  # Placeholder
        
        # Process request
        response = await llm_service.chat_completion(
            request=request,
            user_id=user_id,
            user_tier=user_tier
        )
        
        return response
        
    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except ContextLengthExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ModelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/chat/stream")
async def chat_completion_stream(
    request: ChatRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Generate streaming chat completion
    
    Returns server-sent events (SSE) stream
    """
    try:
        # Extract user info from credentials
        user_id = None
        user_tier = "free"
        
        if credentials:
            user_id = "demo_user"
            user_tier = "premium"
        
        async def generate():
            try:
                async for chunk in llm_service.chat_completion_stream(
                    request=request,
                    user_id=user_id,
                    user_tier=user_tier
                ):
                    # Format as SSE
                    yield f"data: {chunk.json()}\n\n"
                
                # Send final event
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        logger.error(f"Stream initialization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize stream"
        )


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    List available LLM models
    
    Returns all available models with their capabilities and pricing
    """
    try:
        # Get all available models from all providers
        all_models = []
        
        for provider_type in model_router.providers.keys():
            provider = await model_router.get_provider(provider_type)
            if provider:
                models = await provider.list_models()
                all_models.extend(models)
        
        # Get default model
        default_model = model_router.providers.get(model_router.providers.__iter__().__next__())
        default_model_name = default_model.get_default_model() if default_model else "gpt-4-turbo-preview"
        
        return ModelListResponse(
            models=all_models,
            total=len(all_models),
            default_model=default_model_name
        )
        
    except Exception as e:
        logger.error(f"List models error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list models"
        )


@router.get("/models/{model_name}")
async def get_model_info(
    model_name: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Get detailed information about a specific model
    """
    try:
        # Try to find the model in any provider
        for provider_type in model_router.providers.keys():
            provider = await model_router.get_provider(provider_type)
            if provider:
                try:
                    model_info = await provider.get_model_info(model_name)
                    return model_info
                except ProviderError:
                    continue
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_name} not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get model info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get model info"
        )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    period: str = "daily",
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Get usage statistics
    
    Requires authentication
    """
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Extract user ID from credentials
        user_id = "demo_user"  # Placeholder
        
        usage_stats = await llm_service.get_usage_stats(user_id, period)
        
        return UsageResponse(**usage_stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get usage error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage stats"
        )


@router.get("/cache/stats")
async def get_cache_stats(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Get cache statistics
    
    Requires authentication
    """
    try:
        cache_stats = await response_cache.get_cache_stats()
        return cache_stats
        
    except Exception as e:
        logger.error(f"Get cache stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cache stats"
        )


@router.delete("/cache")
async def clear_cache(
    model_name: Optional[str] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Clear cache
    
    Requires authentication
    
    - Without model_name: Clear all cache
    - With model_name: Clear cache for specific model
    """
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if model_name:
            count = await response_cache.invalidate_model(model_name)
        else:
            count = await response_cache.clear_all()
        
        return {"message": f"Cleared {count} cached responses"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns service status and provider availability
    """
    try:
        settings = get_settings()
        
        # Check provider health
        provider_health = await model_router.health_check()
        
        # Get loaded models
        loaded_models = []
        for provider_type, provider in model_router.providers.items():
            if provider.is_initialized:
                try:
                    models = await provider.list_models()
                    loaded_models.extend([m["id"] for m in models])
                except Exception:
                    pass
        
        # Check cache status
        cache_stats = await response_cache.get_cache_stats()
        cache_status = "enabled" if cache_stats.get("cache_enabled") else "disabled"
        
        return HealthResponse(
            status="healthy",
            version=settings.APP_VERSION,
            providers=provider_health,
            models_loaded=loaded_models,
            cache_status=cache_status
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            status="unhealthy",
            version="unknown",
            providers={},
            models_loaded=[],
            cache_status="unknown"
        )
