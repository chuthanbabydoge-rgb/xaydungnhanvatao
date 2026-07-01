"""Core exceptions for Voice Service"""
from typing import Optional, Any


class VoiceServiceError(Exception):
    """Base exception for Voice Service"""
    pass


class AudioProcessingError(VoiceServiceError):
    """Audio processing error"""
    pass


class UnsupportedFormatError(VoiceServiceError):
    """Unsupported audio format error"""
    pass


class AudioTooLargeError(VoiceServiceError):
    """Audio file too large error"""
    pass


class STTError(VoiceServiceError):
    """Speech-to-text error"""
    pass


class TTSError(VoiceServiceError):
    """Text-to-speech error"""
    pass


class VoiceCloningError(VoiceServiceError):
    """Voice cloning error"""
    pass


class ProviderError(VoiceServiceError):
    """Provider error"""
    pass


class RateLimitError(VoiceServiceError):
    """Rate limit exceeded error"""
    pass


class AuthenticationError(VoiceServiceError):
    """Authentication error"""
    pass


class QuotaExceededError(VoiceServiceError):
    """API quota exceeded error"""
    pass
