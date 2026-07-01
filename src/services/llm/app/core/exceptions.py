"""Core exceptions for LLM Service"""
from typing import Optional, Any


class LLMServiceError(Exception):
    """Base exception for LLM Service"""
    pass


class ProviderError(LLMServiceError):
    """LLM provider error"""
    pass


class ModelNotFoundError(LLMServiceError):
    """Model not found error"""
    pass


class ModelLoadError(LLMServiceError):
    """Model load error"""
    pass


class ContextLengthExceededError(LLMServiceError):
    """Context length exceeded error"""
    pass


class RateLimitError(LLMServiceError):
    """Rate limit exceeded error"""
    pass


class AuthenticationError(LLMServiceError):
    """Authentication error"""
    pass


class QuotaExceededError(LLMServiceError):
    """API quota exceeded error"""
    pass


class InvalidRequestError(LLMServiceError):
    """Invalid request error"""
    pass


class StreamingError(LLMServiceError):
    """Streaming error"""
    pass


class CacheError(LLMServiceError):
    """Cache error"""
    pass


class ProviderTimeoutError(LLMServiceError):
    """Provider timeout error"""
    pass


class ProviderUnavailableError(LLMServiceError):
    """Provider unavailable error"""
    pass


class RoutingError(LLMServiceError):
    """Model routing error"""
    pass


class CostExceededError(LLMServiceError):
    """Cost exceeded error"""
    pass
