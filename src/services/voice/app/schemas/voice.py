"""Pydantic schemas for Voice Service"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class STTProvider(str, Enum):
    """Speech-to-text providers"""
    OPENAI = "openai"
    DEEPGRAM = "deepgram"
    WHISPER_LOCAL = "whisper_local"


class TTSProvider(str, Enum):
    """Text-to-speech providers"""
    ELEVENLABS = "elevenlabs"
    TTS_LOCAL = "tts_local"


class STTRequest(BaseModel):
    """Speech-to-text request"""
    audio_data: bytes = Field(..., description="Audio data bytes")
    audio_format: str = Field(..., description="Audio format (wav, mp3, etc.)")
    language: str = Field(default="en", description="Language code")
    provider: Optional[STTProvider] = Field(None, description="STT provider")
    model: Optional[str] = Field(None, description="Specific model to use")
    enable_timestamps: bool = Field(default=False, description="Enable word timestamps")
    enable_diarization: bool = Field(default=False, description="Enable speaker diarization")
    
    @validator('audio_format')
    def validate_format(cls, v):
        """Validate audio format"""
        supported = ["wav", "mp3", "ogg", "flac", "m4a"]
        if v.lower() not in supported:
            raise ValueError(f"Unsupported format: {v}")
        return v.lower()


class STTResponse(BaseModel):
    """Speech-to-text response"""
    text: str = Field(..., description="Transcribed text")
    language: str = Field(..., description="Detected language")
    confidence: float = Field(..., description="Overall confidence score")
    duration: float = Field(..., description="Audio duration in seconds")
    
    # Timestamps
    words: Optional[List[Dict[str, Any]]] = Field(None, description="Word-level timestamps")
    segments: Optional[List[Dict[str, Any]]] = Field(None, description="Segment-level timestamps")
    
    # Diarization
    speakers: Optional[List[Dict[str, Any]]] = Field(None, description="Speaker segments")
    
    # Metadata
    provider: STTProvider = Field(..., description="Provider used")
    model: str = Field(..., description="Model used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class TTSRequest(BaseModel):
    """Text-to-speech request"""
    text: str = Field(..., description="Text to synthesize")
    voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM", description="Voice ID")
    language: str = Field(default="en", description="Language code")
    provider: Optional[TTSProvider] = Field(None, description="TTS provider")
    model: Optional[str] = Field(None, description="Specific model to use")
    
    # Audio settings
    output_format: str = Field(default="mp3", description="Output audio format")
    sample_rate: int = Field(default=24000, description="Sample rate in Hz")
    quality: str = Field(default="high", description="Audio quality")
    
    # Voice settings
    stability: float = Field(default=0.5, ge=0.0, le=1.0, description="Voice stability")
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0, description="Similarity boost")
    style: float = Field(default=0.0, ge=0.0, le=1.0, description="Voice style")
    use_speaker_boost: bool = Field(default=True, description="Use speaker boost")
    
    @validator('text')
    def validate_text_length(cls, v):
        """Validate text length"""
        if len(v) > 5000:
            raise ValueError("Text too long (max 5000 characters)")
        return v


class TTSResponse(BaseModel):
    """Text-to-speech response"""
    audio_data: bytes = Field(..., description="Generated audio data")
    audio_format: str = Field(..., description="Audio format")
    duration: float = Field(..., description="Audio duration in seconds")
    sample_rate: int = Field(..., description="Sample rate")
    
    # Metadata
    provider: TTSProvider = Field(..., description="Provider used")
    model: str = Field(..., description="Model used")
    voice_id: str = Field(..., description="Voice ID used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class VoiceCloneRequest(BaseModel):
    """Voice cloning request"""
    name: str = Field(..., description="Voice name")
    description: Optional[str] = Field(None, description="Voice description")
    samples: List[bytes] = Field(..., description="Audio samples for cloning")
    language: str = Field(default="en", description="Language code")
    
    @validator('samples')
    def validate_samples(cls, v):
        """Validate number of samples"""
        if len(v) < 30:
            raise ValueError("Need at least 30 samples for cloning")
        if len(v) > 100:
            raise ValueError("Maximum 100 samples allowed")
        return v


class VoiceCloneResponse(BaseModel):
    """Voice cloning response"""
    voice_id: str = Field(..., description="Generated voice ID")
    name: str = Field(..., description="Voice name")
    status: str = Field(..., description="Cloning status")
    samples_used: int = Field(..., description="Number of samples used")
    quality_score: float = Field(..., description="Voice quality score")
    
    # Metadata
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class VoiceInfo(BaseModel):
    """Voice information"""
    voice_id: str = Field(..., description="Voice ID")
    name: str = Field(..., description="Voice name")
    language: str = Field(..., description="Language")
    gender: Optional[str] = Field(None, description="Gender")
    age: Optional[str] = Field(None, description="Age group")
    description: Optional[str] = Field(None, description="Description")
    is_custom: bool = Field(default=False, description="Is custom voice")
    created_at: str = Field(..., description="Creation timestamp")


class VoicesListResponse(BaseModel):
    """Voices list response"""
    voices: List[VoiceInfo] = Field(..., description="Available voices")
    total: int = Field(..., description="Total voice count")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    providers: Dict[str, bool] = Field(default_factory=dict, description="Provider availability")
