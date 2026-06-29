"""
LLM Service - Multi-provider LLM routing and generation
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import logging
import asyncio

from config.settings import settings
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="LLM Service",
    description="Multi-provider LLM routing and generation for AI Companion",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class LLMRequest(BaseModel):
    """LLM generation request"""
    prompt: str = Field(..., description="User prompt")
    system_prompt: Optional[str] = Field(default=None, description="System prompt")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    provider: Optional[str] = Field(default=None, description="Preferred provider: openai, anthropic, google, deepseek")
    model: Optional[str] = Field(default=None, description="Specific model to use")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=4096, description="Maximum tokens to generate")
    stream: bool = Field(default=False, description="Enable streaming response")
    functions: Optional[List[Dict[str, Any]]] = Field(default=None, description="Function calling definitions")


class LLMResponse(BaseModel):
    """LLM generation response"""
    text: str = Field(..., description="Generated text")
    model: str = Field(..., description="Model used")
    provider: str = Field(..., description="Provider used")
    tokens_used: int = Field(..., description="Total tokens used")
    finish_reason: str = Field(..., description="Reason for completion")
    function_call: Optional[Dict[str, Any]] = Field(default=None, description="Function call if any")


class RoutingDecision(BaseModel):
    """Routing decision response"""
    provider: str = Field(..., description="Selected provider")
    model: str = Field(..., description="Selected model")
    reasoning: str = Field(..., description="Reasoning for selection")
    estimated_cost: float = Field(..., description="Estimated cost in USD")
    estimated_latency: float = Field(..., description="Estimated latency in seconds")


class ModelInfo(BaseModel):
    """Model information"""
    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model name")
    capabilities: List[str] = Field(..., description="Model capabilities")
    context_window: int = Field(..., description="Context window size")
    input_cost_per_1k: float = Field(..., description="Input cost per 1K tokens")
    output_cost_per_1k: float = Field(..., description="Output cost per 1K tokens")


# Provider implementations
class OpenAIProvider:
    """OpenAI provider implementation"""
    
    def __init__(self):
        self.client = None
        self.models = {
            "gpt-4-turbo-preview": {
                "context_window": 128000,
                "input_cost": 0.01,
                "output_cost": 0.03,
                "capabilities": ["text", "vision", "function_calling", "streaming"]
            },
            "gpt-4": {
                "context_window": 8192,
                "input_cost": 0.03,
                "output_cost": 0.06,
                "capabilities": ["text", "function_calling", "streaming"]
            },
            "gpt-3.5-turbo": {
                "context_window": 16385,
                "input_cost": 0.0005,
                "output_cost": 0.0015,
                "capabilities": ["text", "function_calling", "streaming"]
            }
        }
    
    async def initialize(self):
        """Initialize OpenAI client"""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("OpenAI provider initialized")
        except ImportError:
            raise ImportError("OpenAI library not installed")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "gpt-4-turbo-preview"
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        
        if request.context:
            context_str = self._format_context(request.context)
            messages.append({"role": "system", "content": f"Context: {context_str}"})
        
        messages.append({"role": "user", "content": request.prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                functions=request.functions if request.functions else None
            )
            
            return LLMResponse(
                text=response.choices[0].message.content,
                model=response.model,
                provider="openai",
                tokens_used=response.usage.total_tokens,
                finish_reason=response.choices[0].finish_reason,
                function_call=response.choices[0].message.function_call if response.choices[0].message.function_call else None
            )
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OpenAI generation failed: {str(e)}"
            )
    
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate streaming response using OpenAI"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "gpt-4-turbo-preview"
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        
        if request.context:
            context_str = self._format_context(request.context)
            messages.append({"role": "system", "content": f"Context: {context_str}"})
        
        messages.append({"role": "user", "content": request.prompt})
        
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OpenAI streaming failed: {str(e)}"
            )
    
    def _format_context(self, context: Dict) -> str:
        """Format context dictionary into string"""
        parts = []
        for key, value in context.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            parts.append(f"{key}: {value}")
        return "; ".join(parts)


class AnthropicProvider:
    """Anthropic provider implementation"""
    
    def __init__(self):
        self.client = None
        self.models = {
            "claude-3-opus-20240229": {
                "context_window": 200000,
                "input_cost": 0.015,
                "output_cost": 0.075,
                "capabilities": ["text", "vision", "function_calling", "streaming"]
            },
            "claude-3-sonnet-20240229": {
                "context_window": 200000,
                "input_cost": 0.003,
                "output_cost": 0.015,
                "capabilities": ["text", "vision", "function_calling", "streaming"]
            },
            "claude-3-haiku-20240307": {
                "context_window": 200000,
                "input_cost": 0.00025,
                "output_cost": 0.00125,
                "capabilities": ["text", "vision", "function_calling", "streaming"]
            }
        }
    
    async def initialize(self):
        """Initialize Anthropic client"""
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            logger.info("Anthropic provider initialized")
        except ImportError:
            raise ImportError("Anthropic library not installed")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Anthropic"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "claude-3-opus-20240229"
        
        messages = [{"role": "user", "content": request.prompt}]
        
        if request.context:
            context_str = self._format_context(request.context)
            messages[0]["content"] = f"Context: {context_str}\n\n{request.prompt}"
        
        try:
            response = await self.client.messages.create(
                model=model,
                system=request.system_prompt if request.system_prompt else None,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            return LLMResponse(
                text=response.content[0].text,
                model=response.model,
                provider="anthropic",
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                finish_reason=response.stop_reason,
                function_call=None
            )
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Anthropic generation failed: {str(e)}"
            )
    
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate streaming response using Anthropic"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "claude-3-opus-20240229"
        
        messages = [{"role": "user", "content": request.prompt}]
        
        if request.context:
            context_str = self._format_context(request.context)
            messages[0]["content"] = f"Context: {context_str}\n\n{request.prompt}"
        
        try:
            stream = await self.client.messages.create(
                model=model,
                system=request.system_prompt if request.system_prompt else None,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.type == "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        yield chunk.delta.text
                        
        except Exception as e:
            logger.error(f"Anthropic streaming failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Anthropic streaming failed: {str(e)}"
            )
    
    def _format_context(self, context: Dict) -> str:
        """Format context dictionary into string"""
        parts = []
        for key, value in context.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            parts.append(f"{key}: {value}")
        return "; ".join(parts)


class GoogleProvider:
    """Google provider implementation"""
    
    def __init__(self):
        self.client = None
        self.models = {
            "gemini-pro": {
                "context_window": 32768,
                "input_cost": 0.0,
                "output_cost": 0.0,
                "capabilities": ["text", "vision", "function_calling", "streaming"]
            }
        }
    
    async def initialize(self):
        """Initialize Google client"""
        if not settings.google_api_key:
            raise ValueError("Google API key not configured")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            self.client = genai.GenerativeModel('gemini-pro')
            logger.info("Google provider initialized")
        except ImportError:
            raise ImportError("Google Generative AI library not installed")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Google"""
        if not self.client:
            await self.initialize()
        
        try:
            full_prompt = request.prompt
            if request.system_prompt:
                full_prompt = f"{request.system_prompt}\n\n{request.prompt}"
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                full_prompt,
                generation_config={
                    "temperature": request.temperature,
                    "max_output_tokens": request.max_tokens
                }
            )
            
            return LLMResponse(
                text=response.text,
                model="gemini-pro",
                provider="google",
                tokens_used=0,  # Google doesn't provide token count
                finish_reason="stop",
                function_call=None
            )
            
        except Exception as e:
            logger.error(f"Google generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Google generation failed: {str(e)}"
            )
    
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate streaming response using Google"""
        if not self.client:
            await self.initialize()
        
        try:
            full_prompt = request.prompt
            if request.system_prompt:
                full_prompt = f"{request.system_prompt}\n\n{request.prompt}"
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                full_prompt,
                generation_config={
                    "temperature": request.temperature,
                    "max_output_tokens": request.max_tokens
                },
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Google streaming failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Google streaming failed: {str(e)}"
            )


class DeepSeekProvider:
    """DeepSeek provider implementation"""
    
    def __init__(self):
        self.client = None
        self.models = {
            "deepseek-chat": {
                "context_window": 16384,
                "input_cost": 0.001,
                "output_cost": 0.002,
                "capabilities": ["text", "function_calling", "streaming"]
            }
        }
    
    async def initialize(self):
        """Initialize DeepSeek client"""
        if not settings.deepseek_api_key:
            raise ValueError("DeepSeek API key not configured")
        
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
            logger.info("DeepSeek provider initialized")
        except ImportError:
            raise ImportError("OpenAI library not installed")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using DeepSeek"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "deepseek-chat"
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        
        if request.context:
            context_str = self._format_context(request.context)
            messages.append({"role": "system", "content": f"Context: {context_str}"})
        
        messages.append({"role": "user", "content": request.prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            return LLMResponse(
                text=response.choices[0].message.content,
                model=response.model,
                provider="deepseek",
                tokens_used=response.usage.total_tokens,
                finish_reason=response.choices[0].finish_reason,
                function_call=None
            )
            
        except Exception as e:
            logger.error(f"DeepSeek generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"DeepSeek generation failed: {str(e)}"
            )
    
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Generate streaming response using DeepSeek"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "deepseek-chat"
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        
        if request.context:
            context_str = self._format_context(request.context)
            messages.append({"role": "system", "content": f"Context: {context_str}"})
        
        messages.append({"role": "user", "content": request.prompt})
        
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"DeepSeek streaming failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"DeepSeek streaming failed: {str(e)}"
            )
    
    def _format_context(self, context: Dict) -> str:
        """Format context dictionary into string"""
        parts = []
        for key, value in context.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            parts.append(f"{key}: {value}")
        return "; ".join(parts)


# Router
class LLMRouter:
    """LLM router for intelligent provider selection"""
    
    def __init__(self):
        self.providers = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "google": GoogleProvider(),
            "deepseek": DeepSeekProvider()
        }
        self.performance_metrics = {}
        
        for provider_name in self.providers:
            self.performance_metrics[provider_name] = {
                "latency": [],
                "success_rate": 1.0,
                "error_count": 0,
                "total_requests": 0
            }
    
    async def route(self, request: LLMRequest) -> RoutingDecision:
        """Route request to optimal provider"""
        if request.provider and request.provider in self.providers:
            provider = self.providers[request.provider]
            model = request.model or list(provider.models.keys())[0]
            
            return RoutingDecision(
                provider=request.provider,
                model=model,
                reasoning="User preferred provider",
                estimated_cost=self._estimate_cost(request.provider, model, request),
                estimated_latency=self._estimate_latency(request.provider)
            )
        
        # Hybrid routing
        return self._hybrid_routing(request)
    
    def _hybrid_routing(self, request: LLMRequest) -> RoutingDecision:
        """Hybrid routing considering multiple factors"""
        scores = {}
        
        for provider_name, provider in self.providers.items():
            score = 0.0
            
            # Latency score (0-40 points)
            latency_metrics = self.performance_metrics[provider_name]
            if latency_metrics["latency"]:
                avg_latency = sum(latency_metrics["latency"]) / len(latency_metrics["latency"])
                latency_score = max(0, 40 - avg_latency * 10)
                score += latency_score
            else:
                score += 20
            
            # Cost score (0-30 points)
            cost = self._estimate_cost(provider_name, None, request)
            cost_score = max(0, 30 - cost * 10)
            score += cost_score
            
            # Quality score (0-30 points)
            quality_ranking = {
                "openai": 30,
                "anthropic": 30,
                "google": 25,
                "deepseek": 20
            }
            score += quality_ranking.get(provider_name, 10)
            
            scores[provider_name] = score
        
        best_provider = max(scores, key=scores.get)
        best_model = list(self.providers[best_provider].models.keys())[0]
        
        return RoutingDecision(
            provider=best_provider,
            model=best_model,
            reasoning=f"Hybrid routing (score: {scores[best_provider]:.1f})",
            estimated_cost=self._estimate_cost(best_provider, best_model, request),
            estimated_latency=self._estimate_latency(best_provider)
        )
    
    def _estimate_cost(self, provider_name: str, model: str, request: LLMRequest) -> float:
        """Estimate cost for request"""
        provider = self.providers[provider_name]
        
        if not model:
            model = list(provider.models.keys())[0]
        
        model_info = provider.models.get(model, {})
        input_cost = model_info.get("input_cost", 0.01)
        output_cost = model_info.get("output_cost", 0.02)
        
        # Estimate tokens (rough estimate: 4 chars per token)
        estimated_input_tokens = len(request.prompt) // 4
        estimated_output_tokens = request.max_tokens
        
        cost = (estimated_input_tokens / 1000) * input_cost + (estimated_output_tokens / 1000) * output_cost
        return cost
    
    def _estimate_latency(self, provider_name: str) -> float:
        """Estimate latency for provider"""
        latency_metrics = self.performance_metrics[provider_name]
        
        if latency_metrics["latency"]:
            return sum(latency_metrics["latency"]) / len(latency_metrics["latency"])
        
        # Default latency estimates
        default_latencies = {
            "openai": 2.0,
            "anthropic": 2.5,
            "google": 1.5,
            "deepseek": 3.0
        }
        
        return default_latencies.get(provider_name, 2.0)


# Global router instance
router = LLMRouter()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting LLM Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down LLM Service")


# API endpoints
@app.post("/api/v1/llm/generate")
async def generate(request: LLMRequest):
    """
    Generate response using LLM
    """
    try:
        # Get routing decision
        decision = await router.route(request)
        
        # Get provider
        provider = router.providers[decision.provider]
        
        # Generate response
        if request.stream:
            return StreamingResponse(
                provider.generate_stream(request),
                media_type="text/plain"
            )
        else:
            response = await provider.generate(request)
            return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )


@app.post("/api/v1/llm/route")
async def route_llm(request: LLMRequest):
    """
    Get routing decision without generating
    """
    try:
        decision = await router.route(request)
        return decision
    except Exception as e:
        logger.error(f"Failed to route request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to route request: {str(e)}"
        )


@app.get("/api/v1/llm/models")
async def list_models():
    """
    List available models from all providers
    """
    try:
        models = []
        
        for provider_name, provider in router.providers.items():
            for model_name, model_info in provider.models.items():
                models.append(ModelInfo(
                    provider=provider_name,
                    model=model_name,
                    capabilities=model_info["capabilities"],
                    context_window=model_info["context_window"],
                    input_cost_per_1k=model_info["input_cost"],
                    output_cost_per_1k=model_info["output_cost"]
                ))
        
        return {
            "models": models,
            "count": len(models)
        }
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "llm-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
