"""
STT Service - Speech-to-Text conversion
Handles audio transcription using multiple providers (Whisper, Deepgram, Google)
"""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import logging
import asyncio
import io

from config.settings import settings
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="STT Service",
    description="Speech-to-Text conversion for AI Companion",
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
class STTRequest(BaseModel):
    """STT request model"""
    audio_data: str = Field(..., description="Base64 encoded audio data")
    audio_format: str = Field(default="wav", description="Audio format: wav, mp3, ogg, flac")
    language: Optional[str] = Field(default="en", description="Language code (en, vi, etc.)")
    provider: Optional[str] = Field(default=None, description="Preferred provider: whisper, deepgram, google")
    model: Optional[str] = Field(default=None, description="Specific model to use")
    enable_punctuation: bool = Field(default=True, description="Enable punctuation")
    enable_timestamps: bool = Field(default=False, description="Enable word timestamps")
    enable_vad: bool = Field(default=True, description="Enable voice activity detection")


class STTResponse(BaseModel):
    """STT response model"""
    text: str = Field(..., description="Transcribed text")
    language: str = Field(..., description="Detected language")
    confidence: float = Field(..., description="Confidence score (0-1)")
    duration: float = Field(..., description="Audio duration in seconds")
    provider: str = Field(..., description="Provider used")
    model: str = Field(..., description="Model used")
    words: Optional[List[Dict[str, Any]]] = Field(default=None, description="Word-level timestamps")
    processing_time: float = Field(..., description="Processing time in seconds")


class StreamSTTRequest(BaseModel):
    """Streaming STT request"""
    language: Optional[str] = Field(default="en", description="Language code")
    provider: Optional[str] = Field(default="whisper", description="Provider to use")
    sample_rate: int = Field(default=16000, description="Audio sample rate")


# Provider implementations
class WhisperProvider:
    """OpenAI Whisper provider implementation"""
    
    def __init__(self):
        self.client = None
        self.models = {
            "whisper-1": {
                "languages": ["en", "vi", "es", "fr", "de", "ja", "ko", "zh"],
                "max_duration": 300,  # 5 minutes
                "supports_timestamps": True
            }
        }
    
    async def initialize(self):
        """Initialize Whisper client"""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("Whisper provider initialized")
        except ImportError:
            raise ImportError("OpenAI library not installed")
    
    async def transcribe(self, audio_data: bytes, request: STTRequest) -> STTResponse:
        """Transcribe audio using Whisper"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "whisper-1"
        
        try:
            # Create audio file from bytes
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{request.audio_format}"
            
            start_time = datetime.utcnow()
            
            # Transcribe
            response = await self.client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=request.language,
                response_format="verbose" if request.enable_timestamps else "text",
                timestamp_granularities=["word"] if request.enable_timestamps else None
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Extract words with timestamps if enabled
            words = None
            if request.enable_timestamps and hasattr(response, 'words'):
                words = [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end
                    }
                    for word in response.words
                ]
            
            # Get text
            text = response.text if hasattr(response, 'text') else response
            
            return STTResponse(
                text=text,
                language=request.language,
                confidence=0.95,  # Whisper doesn't provide confidence
                duration=0,  # Whisper doesn't provide duration
                provider="whisper",
                model=model,
                words=words,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Whisper transcription failed: {str(e)}"
            )


class DeepgramProvider:
    """Deepgram provider implementation"""
    
    def __init__(self):
        self.client = None
        self.models = {
            "nova-2": {
                "languages": ["en", "vi", "es", "fr", "de", "ja", "ko", "zh", "pt", "ru"],
                "max_duration": 3600,  # 1 hour
                "supports_timestamps": True,
                "streaming": True
            }
        }
    
    async def initialize(self):
        """Initialize Deepgram client"""
        if not settings.deepgram_api_key:
            raise ValueError("Deepgram API key not configured")
        
        try:
            from deepgram import DeepgramClient
            self.client = DeepgramClient(settings.deepgram_api_key)
            logger.info("Deepgram provider initialized")
        except ImportError:
            raise ImportError("Deepgram library not installed")
    
    async def transcribe(self, audio_data: bytes, request: STTRequest) -> STTResponse:
        """Transcribe audio using Deepgram"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "nova-2"
        
        try:
            start_time = datetime.utcnow()
            
            # Transcribe
            response = await asyncio.to_thread(
                self.client.listen.rest.v("1").transcribe_file,
                audio_data,
                {
                    "model": model,
                    "language": request.language,
                    "punctuate": request.enable_punctuation,
                    "timestamps": request.enable_timestamps,
                    "smart_format": True
                }
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Extract results
            result = response.results.channels[0]
            alternatives = result.alternatives[0]
            
            # Extract words with timestamps if enabled
            words = None
            if request.enable_timestamps and hasattr(alternatives, 'words'):
                words = [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "confidence": word.confidence
                    }
                    for word in alternatives.words
                ]
            
            return STTResponse(
                text=alternatives.transcript,
                language=request.language,
                confidence=alternatives.confidence if hasattr(alternatives, 'confidence') else 0.9,
                duration=result.duration if hasattr(result, 'duration') else 0,
                provider="deepgram",
                model=model,
                words=words,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Deepgram transcription failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Deepgram transcription failed: {str(e)}"
            )


class GoogleProvider:
    """Google Speech-to-Text provider implementation"""
    
    def __init__(self):
        self.client = None
        self.models = {
            "latest_long": {
                "languages": ["en-US", "vi-VN", "es-ES", "fr-FR", "de-DE", "ja-JP", "ko-KR", "zh-CN"],
                "max_duration": 480,  # 8 minutes
                "supports_timestamps": True
            }
        }
    
    async def initialize(self):
        """Initialize Google client"""
        if not settings.google_api_key:
            raise ValueError("Google API key not configured")
        
        try:
            from google.cloud.speech import SpeechClient
            self.client = SpeechClient()
            logger.info("Google provider initialized")
        except ImportError:
            raise ImportError("Google Cloud Speech library not installed")
    
    async def transcribe(self, audio_data: bytes, request: STTRequest) -> STTResponse:
        """Transcribe audio using Google Speech-to-Text"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "latest_long"
        
        try:
            from google.cloud.speech import RecognitionConfig, RecognitionAudio
            
            start_time = datetime.utcnow()
            
            # Configure recognition
            config = RecognitionConfig(
                encoding=RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=request.language,
                enable_automatic_punctuation=request.enable_punctuation,
                enable_word_time_offsets=request.enable_timestamps
            )
            
            audio = RecognitionAudio(content=audio_data)
            
            # Transcribe
            response = await asyncio.to_thread(
                self.client.recognize,
                config=config,
                audio=audio
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Extract results
            results = response.results
            if not results:
                return STTResponse(
                    text="",
                    language=request.language,
                    confidence=0.0,
                    duration=0,
                    provider="google",
                    model=model,
                    words=None,
                    processing_time=processing_time
                )
            
            # Get transcript
            transcript = " ".join(
                result.alternatives[0].transcript
                for result in results
            )
            
            # Extract words with timestamps if enabled
            words = None
            if request.enable_timestamps:
                words = []
                for result in results:
                    for word_info in result.alternatives[0].words:
                        words.append({
                            "word": word_info.word,
                            "start": word_info.start_time.total_seconds(),
                            "end": word_info.end_time.total_seconds()
                        })
            
            return STTResponse(
                text=transcript,
                language=request.language,
                confidence=results[0].alternatives[0].confidence,
                duration=0,  # Google doesn't provide duration directly
                provider="google",
                model=model,
                words=words,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Google transcription failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Google transcription failed: {str(e)}"
            )


# Initialize providers
whisper_provider = WhisperProvider()
deepgram_provider = DeepgramProvider()
google_provider = GoogleProvider()

providers = {
    "whisper": whisper_provider,
    "deepgram": deepgram_provider,
    "google": google_provider
}


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting STT Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down STT Service")


# API endpoints
@app.post("/api/v1/stt/transcribe", response_model=STTResponse)
async def transcribe_audio(request: STTRequest):
    """
    Transcribe audio to text
    """
    try:
        import base64
        
        # Decode base64 audio data
        audio_data = base64.b64decode(request.audio_data)
        
        # Select provider
        provider_name = request.provider or "whisper"
        provider = providers.get(provider_name)
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider '{provider_name}' not supported"
            )
        
        # Transcribe
        response = await provider.transcribe(audio_data, request)
        
        logger.info(f"Transcribed audio using {provider_name}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )


@app.post("/api/v1/stt/transcribe/file", response_model=STTResponse)
async def transcribe_audio_file(
    file: UploadFile = File(...),
    language: str = "en",
    provider: str = "whisper",
    enable_timestamps: bool = False
):
    """
    Transcribe audio file to text
    """
    try:
        # Read audio file
        audio_data = await file.read()
        
        # Get file extension
        audio_format = file.filename.split(".")[-1] if file.filename else "wav"
        
        # Create request
        request = STTRequest(
            audio_data="",  # Not used for file upload
            audio_format=audio_format,
            language=language,
            provider=provider,
            enable_timestamps=enable_timestamps
        )
        
        # Select provider
        provider_instance = providers.get(provider)
        
        if not provider_instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider '{provider}' not supported"
            )
        
        # Transcribe
        response = await provider_instance.transcribe(audio_data, request)
        
        logger.info(f"Transcribed audio file using {provider}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File transcription failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File transcription failed: {str(e)}"
        )


@app.get("/api/v1/stt/providers")
async def get_providers():
    """
    Get available STT providers
    """
    return {
        "providers": [
            {
                "name": "whisper",
                "models": whisper_provider.models,
                "description": "OpenAI Whisper - High accuracy, multi-language"
            },
            {
                "name": "deepgram",
                "models": deepgram_provider.models,
                "description": "Deepgram Nova - Real-time, streaming support"
            },
            {
                "name": "google",
                "models": google_provider.models,
                "description": "Google Speech-to-Text - Enterprise-grade"
            }
        ]
    }


@app.get("/api/v1/stt/languages")
async def get_supported_languages():
    """
    Get supported languages for each provider
    """
    return {
        "whisper": whisper_provider.models["whisper-1"]["languages"],
        "deepgram": deepgram_provider.models["nova-2"]["languages"],
        "google": google_provider.models["latest_long"]["languages"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "stt-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8019)
