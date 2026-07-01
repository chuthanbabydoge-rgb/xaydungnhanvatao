"""OpenAI LLM provider implementation"""
import time
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

import httpx
from openai import AsyncOpenAI
from openai import APIError, RateLimitError, APITimeoutError

from app.schemas import ChatRequest, ChatResponse, StreamingChunk, ModelProvider, Message, ChatRole
from app.services.base_provider import BaseLLMProvider
from app.core.exceptions import ProviderError, RateLimitError, ProviderTimeoutError

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider"""
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        org_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.base_url = base_url or "https://api.openai.com/v1"
        self.org_id = org_id
        self.client: Optional[AsyncOpenAI] = None
        
        # Model pricing (USD per 1K tokens)
        self.pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-32k": {"input": 0.06, "output": 0.12},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
        }
        
        # Model capabilities
        self.model_capabilities = {
            "gpt-4": {
                "max_context": 8192,
                "max_output": 4096,
                "function_calling": True,
                "streaming": True,
                "vision": False
            },
            "gpt-4-32k": {
                "max_context": 32768,
                "max_output": 4096,
                "function_calling": True,
                "streaming": True,
                "vision": False
            },
            "gpt-4-turbo": {
                "max_context": 128000,
                "max_output": 4096,
                "function_calling": True,
                "streaming": True,
                "vision": True
            },
            "gpt-4-turbo-preview": {
                "max_context": 128000,
                "max_output": 4096,
                "function_calling": True,
                "streaming": True,
                "vision": True
            },
            "gpt-3.5-turbo": {
                "max_context": 4096,
                "max_output": 4096,
                "function_calling": True,
                "streaming": True,
                "vision": False
            },
            "gpt-3.5-turbo-16k": {
                "max_context": 16384,
                "max_output": 4096,
                "function_calling": True,
                "streaming": True,
                "vision": False
            },
        }
    
    async def initialize(self):
        """Initialize OpenAI client"""
        if self._initialized:
            return
        
        try:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                organization=self.org_id,
                timeout=60.0,
                max_retries=3,
            )
            
            # Test connection
            await self.list_models()
            
            self._initialized = True
            logger.info("OpenAI provider initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI provider: {e}")
            raise ProviderError(f"OpenAI initialization failed: {str(e)}")
    
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
            # Convert messages to OpenAI format
            messages = self._convert_messages(request.messages, request.system_prompt)
            
            # Build parameters
            params = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
            }
            
            # Add function calling if enabled
            if request.functions and self.supports_function_calling():
                params["functions"] = [f.dict() for f in request.functions]
                if request.function_call:
                    params["function_call"] = request.function_call
            
            # Make API call
            response = await self.client.chat.completions.create(**params)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Calculate cost
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(prompt_tokens, completion_tokens, request.model)
            
            # Build response
            chat_response = ChatResponse(
                id=response.id,
                created=int(response.created),
                model=response.model,
                choices=[{
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                        "function_call": choice.message.function_call.dict() if choice.message.function_call else None
                    },
                    "finish_reason": choice.finish_reason
                } for choice in response.choices],
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                processing_time_ms=processing_time,
                first_token_time_ms=first_token_time,
                cached=False,
                cost=cost,
                provider=self.provider_type,
                request_id=request_id
            )
            
            logger.info(f"OpenAI chat completion successful: {request_id}")
            return chat_response
            
        except RateLimitError as e:
            raise RateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
        except APITimeoutError as e:
            raise ProviderTimeoutError(f"OpenAI timeout: {str(e)}")
        except APIError as e:
            raise ProviderError(f"OpenAI API error: {str(e)}")
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
            # Convert messages to OpenAI format
            messages = self._convert_messages(request.messages, request.system_prompt)
            
            # Build parameters
            params = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
                "stream": True,
            }
            
            # Add function calling if enabled
            if request.functions and self.supports_function_calling():
                params["functions"] = [f.dict() for f in request.functions]
                if request.function_call:
                    params["function_call"] = request.function_call
            
            # Make streaming API call
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if first_token_time is None:
                    first_token_time = (time.time() - start_time) * 1000
                
                streaming_chunk = StreamingChunk(
                    id=chunk.id,
                    created=int(chunk.created),
                    model=chunk.model,
                    choices=[{
                        "index": choice.index,
                        "delta": {
                            "role": choice.delta.role,
                            "content": choice.delta.content,
                            "function_call": choice.delta.function_call.dict() if choice.delta.function_call else None
                        } if choice.delta else {},
                        "finish_reason": choice.finish_reason
                    } for choice in chunk.choices],
                    finish_reason=chunk.choices[0].finish_reason if chunk.choices else None,
                    provider=self.provider_type
                )
                
                yield streaming_chunk
            
            logger.info(f"OpenAI streaming completion successful: {request_id}")
            
        except RateLimitError as e:
            raise RateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
        except APITimeoutError as e:
            raise ProviderTimeoutError(f"OpenAI timeout: {str(e)}")
        except APIError as e:
            raise ProviderError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise self._handle_error(e, request_id)
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        if not self._initialized:
            await self.initialize()
        
        try:
            models = await self.client.models.list()
            
            model_list = []
            for model in models.data:
                if model.id in self.model_capabilities:
                    capabilities = self.model_capabilities[model.id]
                    pricing = self.pricing.get(model.id, {"input": 0.0, "output": 0.0})
                    
                    model_list.append({
                        "id": model.id,
                        "provider": self.provider_type.value,
                        "display_name": model.id,
                        "max_context_length": capabilities["max_context"],
                        "max_output_tokens": capabilities["max_output"],
                        "supports_function_calling": capabilities["function_calling"],
                        "supports_vision": capabilities["vision"],
                        "supports_streaming": capabilities["streaming"],
                        "input_cost_per_1k": pricing["input"],
                        "output_cost_per_1k": pricing["output"],
                        "quality_score": 0.9 if "gpt-4" in model.id else 0.7,
                        "priority": 10 if "gpt-4" in model.id else 5,
                        "enabled": True
                    })
            
            return model_list
            
        except Exception as e:
            logger.error(f"Failed to list OpenAI models: {e}")
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
                "quality_score": 0.9 if "gpt-4" in model_name else 0.7,
                "priority": 10 if "gpt-4" in model_name else 5,
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
        return "gpt-4-turbo-preview"
    
    @property
    def provider_type(self) -> ModelProvider:
        """Get provider type"""
        return ModelProvider.OPENAI
    
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
    
    def _convert_messages(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Convert messages to OpenAI format"""
        converted = []
        
        # Add system prompt if provided
        if system_prompt:
            converted.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Convert messages
        for msg in messages:
            converted.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return converted
