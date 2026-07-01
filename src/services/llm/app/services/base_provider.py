"""Base LLM provider interface"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime
import logging

from app.schemas import ChatRequest, ChatResponse, StreamingChunk, ModelProvider, FunctionDefinition
from app.core.exceptions import ProviderError, ProviderTimeoutError, RateLimitError

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.kwargs = kwargs
        self._initialized = False
    
    @abstractmethod
    async def initialize(self):
        """Initialize the provider"""
        pass
    
    @abstractmethod
    async def chat_completion(
        self,
        request: ChatRequest,
        request_id: str
    ) -> ChatResponse:
        """Generate chat completion"""
        pass
    
    @abstractmethod
    async def chat_completion_stream(
        self,
        request: ChatRequest,
        request_id: str
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Generate streaming chat completion"""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        pass
    
    @abstractmethod
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get model information"""
        pass
    
    @abstractmethod
    def supports_function_calling(self) -> bool:
        """Check if provider supports function calling"""
        pass
    
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if provider supports streaming"""
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get default model name"""
        pass
    
    @property
    def provider_type(self) -> ModelProvider:
        """Get provider type"""
        raise NotImplementedError
    
    @property
    def is_initialized(self) -> bool:
        """Check if provider is initialized"""
        return self._initialized
    
    async def health_check(self) -> bool:
        """Check provider health"""
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"Health check failed for {self.provider_type}: {e}")
            return False
    
    def calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str
    ) -> float:
        """Calculate cost for token usage"""
        # Default implementation - override in subclasses
        return 0.0
    
    def _handle_error(self, error: Exception, request_id: str) -> ProviderError:
        """Handle provider errors"""
        logger.error(f"Provider error for request {request_id}: {error}")
        
        error_message = str(error)
        
        if "timeout" in error_message.lower():
            return ProviderTimeoutError(f"Provider timeout: {error_message}")
        elif "rate limit" in error_message.lower():
            return RateLimitError(f"Rate limit exceeded: {error_message}")
        else:
            return ProviderError(f"Provider error: {error_message}")
