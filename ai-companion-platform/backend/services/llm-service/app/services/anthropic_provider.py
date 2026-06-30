"""Anthropic LLM provider implementation"""
import time
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

import anthropic
from anthropic import Anthropic, AsyncAnthropic
from anthropic import APIError, RateLimitError, APITimeoutError

from app.schemas import ChatRequest, ChatResponse, StreamingChunk, ModelProvider, Message, ChatRole
from app.services.base_provider import BaseLLMProvider
from app.core.exceptions import ProviderError, RateLimitError, ProviderTimeoutError

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider"""
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.base_url = base_url or "https://api.anthropic.com"
        self.client: Optional[AsyncAnthropic] = None
        
        # Model pricing (USD per 1K tokens)
        self.pricing = {
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
            "claude-2.1": {"input": 0.008, "output": 0.024},
            "claude-2.0": {"input": 0.008, "output": 0.024},
        }
        
        # Model capabilities
        self.model_capabilities = {
            "claude-3-opus-20240229": {
                "max_context": 200000,
                "max_output": 4096,
                "function_calling": True,
                "streaming": True,
                "vision": True
            },
            "claude-3-sonnet-20240229": {
                "max_context": 200000,
                "max_output": 4096,
                "function_calling": True,
                "streaming": True,
                "vision": True
            },
            "claude-3-haiku-20240307": {
                "max_context": 200000,
                "max_output": 4096,
                "function_calling": True,
                "streaming": True,
                "vision": True
            },
            "claude-2.1": {
                "max_context": 100000,
                "max_output": 4096,
                "function_calling": False,
                "streaming": True,
                "vision": False
            },
            "claude-2.0": {
                "max_context": 100000,
                "max_output": 4096,
                "function_calling": False,
                "streaming": True,
                "vision": False
            },
        }
    
    async def initialize(self):
        """Initialize Anthropic client"""
        if self._initialized:
            return
        
        try:
            self.client = AsyncAnthropic(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=60.0,
                max_retries=3,
            )
            
            # Test connection
            await self.list_models()
            
            self._initialized = True
            logger.info("Anthropic provider initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic provider: {e}")
            raise ProviderError(f"Anthropic initialization failed: {str(e)}")
    
    async def chat_completion(
        self,
        request: ChatRequest,
        request_id: str
    ) -> ChatResponse:
        """Generate chat completion"""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        first_token_time = None
        
        try:
            # Convert messages to Anthropic format
            messages = self._convert_messages(request.messages)
            system_prompt = request.system_prompt or ""
            
            # Build parameters
            params = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
            }
            
            if system_prompt:
                params["system"] = system_prompt
            
            # Make API call
            response = await self.client.messages.create(**params)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Calculate cost
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            cost = self.calculate_cost(prompt_tokens, completion_tokens, request.model)
            
            # Build response
            chat_response = ChatResponse(
                id=response.id,
                created=int(time.time()),
                model=response.model,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": response.role,
                        "content": response.content[0].text if response.content else ""
                    },
                    "finish_reason": response.stop_reason
                }],
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                processing_time_ms=processing_time,
                first_token_time_ms=first_token_time,
                cached=False,
                cost=cost,
                provider=self.provider_type,
                request_id=request_id
            )
            
            logger.info(f"Anthropic chat completion successful: {request_id}")
            return chat_response
            
        except RateLimitError as e:
            raise RateLimitError(f"Anthropic rate limit exceeded: {str(e)}")
        except APITimeoutError as e:
            raise ProviderTimeoutError(f"Anthropic timeout: {str(e)}")
        except APIError as e:
            raise ProviderError(f"Anthropic API error: {str(e)}")
        except Exception as e:
            raise self._handle_error(e, request_id)
    
    async def chat_completion_stream(
        self,
        request: ChatRequest,
        request_id: str
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Generate streaming chat completion"""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        first_token_time = None
        
        try:
            # Convert messages to Anthropic format
            messages = self._convert_messages(request.messages)
            system_prompt = request.system_prompt or ""
            
            # Build parameters
            params = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": True,
            }
            
            if system_prompt:
                params["system"] = system_prompt
            
            # Make streaming API call
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    if first_token_time is None:
                        first_token_time = (time.time() - start_time) * 1000
                    
                    streaming_chunk = StreamingChunk(
                        id=f"stream-{request_id}",
                        created=int(time.time()),
                        model=request.model,
                        choices=[{
                            "index": 0,
                            "delta": {"content": text},
                            "finish_reason": None
                        }],
                        finish_reason=None,
                        provider=self.provider_type
                    )
                    
                    yield streaming_chunk
            
            # Send final chunk
            streaming_chunk = StreamingChunk(
                id=f"stream-{request_id}",
                created=int(time.time()),
                model=request.model,
                choices=[{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }],
                finish_reason="stop",
                provider=self.provider_type
            )
            
            yield streaming_chunk
            
            logger.info(f"Anthropic streaming completion successful: {request_id}")
            
        except RateLimitError as e:
            raise RateLimitError(f"Anthropic rate limit exceeded: {str(e)}")
        except APITimeoutError as e:
            raise ProviderTimeoutError(f"Anthropic timeout: {str(e)}")
        except APIError as e:
            raise ProviderError(f"Anthropic API error: {str(e)}")
        except Exception as e:
            raise self._handle_error(e, request_id)
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        if not self._initialized:
            await self.initialize()
        
        try:
            model_list = []
            
            for model_id, capabilities in self.model_capabilities.items():
                pricing = self.pricing.get(model_id, {"input": 0.0, "output": 0.0})
                
                model_list.append({
                    "id": model_id,
                    "provider": self.provider_type.value,
                    "display_name": model_id,
                    "max_context_length": capabilities["max_context"],
                    "max_output_tokens": capabilities["max_output"],
                    "supports_function_calling": capabilities["function_calling"],
                    "supports_vision": capabilities["vision"],
                    "supports_streaming": capabilities["streaming"],
                    "input_cost_per_1k": pricing["input"],
                    "output_cost_per_1k": pricing["output"],
                    "quality_score": 0.95 if "opus" in model_id else 0.85 if "sonnet" in model_id else 0.75,
                    "priority": 15 if "opus" in model_id else 10 if "sonnet" in model_id else 5,
                    "enabled": True
                })
            
            return model_list
            
        except Exception as e:
            logger.error(f"Failed to list Anthropic models: {e}")
            raise ProviderError(f"Failed to list models: {str(e)}")
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get model information"""
        if model_name in self.model_capabilities:
            capabilities = self.model_capabilities[model_name]
            pricing = self.pricing.get(model_name, {"input": 0.0, "output": 0.0})
            
            return {
                "id": model_name,
                "provider": self.provider_type.value,
                "display_name": model_name,
                "max_context_length": capabilities["max_context"],
                "max_output_tokens": capabilities["max_output"],
                "supports_function_calling": capabilities["function_calling"],
                "supports_vision": capabilities["vision"],
                "supports_streaming": capabilities["streaming"],
                "input_cost_per_1k": pricing["input"],
                "output_cost_per_1k": pricing["output"],
                "quality_score": 0.95 if "opus" in model_name else 0.85 if "sonnet" in model_name else 0.75,
                "priority": 15 if "opus" in model_name else 10 if "sonnet" in model_name else 5,
                "enabled": True
            }
        
        raise ProviderError(f"Model {model_name} not found")
    
    def supports_function_calling(self) -> bool:
        """Check if provider supports function calling"""
        return True
    
    def supports_streaming(self) -> bool:
        """Check if provider supports streaming"""
        return True
    
    def get_default_model(self) -> str:
        """Get default model name"""
        return "claude-3-sonnet-20240229"
    
    @property
    def provider_type(self) -> ModelProvider:
        """Get provider type"""
        return ModelProvider.ANTHROPIC
    
    def calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str
    ) -> float:
        """Calculate cost for token usage"""
        if model_name not in self.pricing:
            return 0.0
        
        pricing = self.pricing[model_name]
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert messages to Anthropic format"""
        converted = []
        
        for msg in messages:
            if msg.role == ChatRole.USER:
                converted.append({
                    "role": "user",
                    "content": msg.content
                })
            elif msg.role == ChatRole.ASSISTANT:
                converted.append({
                    "role": "assistant",
                    "content": msg.content
                })
        
        return converted
