"""Pydantic schemas for LLM Service"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class ModelProvider(str, Enum):
    """LLM provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    LOCAL = "local"


class ChatRole(str, Enum):
    """Chat message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class Message(BaseModel):
    """Chat message"""
    role: ChatRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Message name for function calls")
    function_call: Optional[Dict[str, Any]] = Field(None, description="Function call data")


class FunctionDefinition(BaseModel):
    """Function definition for function calling"""
    name: str = Field(..., description="Function name")
    description: str = Field(..., description="Function description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Function parameters schema")
    required: List[str] = Field(default_factory=list, description="Required parameters")


class ChatRequest(BaseModel):
    """Chat completion request"""
    model: str = Field(..., description="Model identifier")
    messages: List[Message] = Field(..., description="Chat messages")
    
    # Optional parameters
    system_prompt: Optional[str] = Field(None, description="System prompt")
    max_tokens: int = Field(default=4096, ge=1, le=128000, description="Max tokens to generate")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    
    # Streaming
    stream: bool = Field(default=False, description="Enable streaming")
    
    # Function calling
    functions: Optional[List[FunctionDefinition]] = Field(None, description="Available functions")
    function_call: Optional[str] = Field(None, description="Force function call")
    
    # Model selection
    provider: Optional[ModelProvider] = Field(None, description="Force specific provider")
    enable_routing: bool = Field(default=True, description="Enable intelligent routing")
    
    # Caching
    enable_cache: bool = Field(default=True, description="Enable response caching")
    
    # Metadata
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ChatResponse(BaseModel):
    """Chat completion response"""
    id: str = Field(..., description="Response ID")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    
    choices: List[Dict[str, Any]] = Field(..., description="Response choices")
    
    usage: Dict[str, int] = Field(..., description="Token usage")
    
    # Metrics
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    first_token_time_ms: Optional[float] = Field(None, description="Time to first token")
    cached: bool = Field(default=False, description="Response from cache")
    
    # Cost
    cost: float = Field(default=0.0, description="Estimated cost in USD")
    
    # Provider info
    provider: ModelProvider = Field(..., description="LLM provider used")
    
    # Request metadata
    request_id: str = Field(..., description="Original request ID")


class StreamingChunk(BaseModel):
    """Streaming response chunk"""
    id: str = Field(..., description="Chunk ID")
    object: str = Field(default="chat.completion.chunk", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    
    choices: List[Dict[str, Any]] = Field(..., description="Response choices")
    
    finish_reason: Optional[str] = Field(None, description="Finish reason")
    
    provider: ModelProvider = Field(..., description="LLM provider used")


class ModelInfo(BaseModel):
    """Model information"""
    provider: ModelProvider = Field(..., description="Model provider")
    model_name: str = Field(..., description="Model name")
    display_name: str = Field(..., description="Display name")
    version: str = Field(..., description="Model version")
    
    max_context_length: int = Field(..., description="Max context length")
    max_output_tokens: int = Field(..., description="Max output tokens")
    
    supports_function_calling: bool = Field(default=False, description="Supports function calling")
    supports_vision: bool = Field(default=False, description="Supports vision")
    supports_streaming: bool = Field(default=True, description="Supports streaming")
    
    input_cost_per_1k: float = Field(..., description="Input cost per 1K tokens")
    output_cost_per_1k: float = Field(..., description="Output cost per 1K tokens")
    
    quality_score: float = Field(..., description="Quality score")
    priority: int = Field(..., description="Routing priority")
    enabled: bool = Field(..., description="Model enabled status")


class ModelListResponse(BaseModel):
    """Model list response"""
    models: List[ModelInfo] = Field(..., description="Available models")
    total: int = Field(..., description="Total model count")
    default_model: str = Field(..., description="Default model")


class UsageResponse(BaseModel):
    """Usage statistics response"""
    period: str = Field(..., description="Time period")
    total_requests: int = Field(..., description="Total requests")
    successful_requests: int = Field(..., description="Successful requests")
    failed_requests: int = Field(..., description="Failed requests")
    cached_requests: int = Field(..., description="Cached requests")
    
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost: float = Field(..., description="Total cost")
    
    avg_processing_time_ms: float = Field(..., description="Average processing time")
    
    by_model: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Usage by model")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    request_id: Optional[str] = Field(None, description="Request ID")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    providers: Dict[str, bool] = Field(default_factory=dict, description="Provider availability")
    models_loaded: List[str] = Field(default_factory=list, description="Loaded models")
    cache_status: str = Field(..., description="Cache status")
