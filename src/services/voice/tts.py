"""
TTS Service - Text-to-Speech conversion
Handles speech synthesis using multiple providers (ElevenLabs, Azure, Google)
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import logging
import asyncio
import io

from .config.settings import settings
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="TTS Service",
    description="Text-to-Speech conversion for AI Companion",
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
class TTSRequest(BaseModel):
    """TTS request model"""
    text: str = Field(..., description="Text to synthesize")
    voice_id: Optional[str] = Field(default=None, description="Voice ID to use")
    language: Optional[str] = Field(default="en", description="Language code (en, vi, etc.)")
    provider: Optional[str] = Field(default=None, description="Preferred provider: elevenlabs, azure, google")
    model: Optional[str] = Field(default=None, description="Specific model to use")
    output_format: str = Field(default="mp3", description="Output format: mp3, wav, ogg")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed (0.5-2.0)")
    pitch: float = Field(default=1.0, ge=0.5, le=2.0, description="Pitch adjustment (0.5-2.0)")
    emotion: Optional[str] = Field(default=None, description="Emotion: neutral, happy, sad, angry")
    enable_streaming: bool = Field(default=False, description="Enable streaming response")


class TTSResponse(BaseModel):
    """TTS response model"""
    audio_data: str = Field(..., description="Base64 encoded audio data")
    audio_format: str = Field(..., description="Audio format")
    duration: float = Field(..., description="Audio duration in seconds")
    provider: str = Field(..., description="Provider used")
    model: str = Field(..., description="Model used")
    voice_id: str = Field(..., description="Voice ID used")
    processing_time: float = Field(..., description="Processing time in seconds")


class VoiceInfo(BaseModel):
    """Voice information model"""
    voice_id: str = Field(..., description="Voice ID")
    name: str = Field(..., description="Voice name")
    language: str = Field(..., description="Language code")
    gender: str = Field(..., description="Gender: male, female, neutral")
    description: Optional[str] = Field(default=None, description="Voice description")


# Provider implementations
class ElevenLabsProvider:
    """ElevenLabs provider implementation"""
    
    def __init__(self):
        self.client = None
        self.voices = {}
        self.models = {
            "eleven_multilingual_v2": {
                "languages": ["en", "vi", "es", "fr", "de", "ja", "ko", "zh", "pt", "ru"],
                "streaming": True,
                "emotion_support": True
            },
            "eleven_turbo_v2": {
                "languages": ["en"],
                "streaming": True,
                "emotion_support": False
            }
        }
    
    async def initialize(self):
        """Initialize ElevenLabs client"""
        if not settings.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key not configured")
        
        try:
            from elevenlabs import AsyncElevenLabs
            self.client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)
            
            # Load available voices
            voices = await self.client.voices.get_all()
            for voice in voices.voices:
                self.voices[voice.voice_id] = {
                    "name": voice.name,
                    "language": voice.labels.get("language", "en"),
                    "gender": voice.labels.get("gender", "neutral"),
                    "description": voice.description
                }
            
            logger.info("ElevenLabs provider initialized")
        except ImportError:
            raise ImportError("ElevenLabs library not installed")
    
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech using ElevenLabs"""
        if not self.client:
            await self.initialize()
        
        model = request.model or "eleven_multilingual_v2"
        voice_id = request.voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default voice
        
        try:
            start_time = datetime.utcnow()
            
            # Generate speech
            if request.enable_streaming:
                # Streaming response
                audio_stream = await self.client.generate(
                    text=request.text,
                    voice=voice_id,
                    model=model,
                    stream=True
                )
                
                # Collect stream data
                audio_data = b""
                async for chunk in audio_stream:
                    audio_data += chunk
            else:
                # Non-streaming response
                audio_data = await self.client.generate(
                    text=request.text,
                    voice=voice_id,
                    model=model
                )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Encode to base64
            import base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Estimate duration (rough estimate)
            duration = len(request.text) / 10  # ~10 chars per second
            
            return TTSResponse(
                audio_data=audio_base64,
                audio_format=request.output_format,
                duration=duration,
                provider="elevenlabs",
                model=model,
                voice_id=voice_id,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"ElevenLabs synthesis failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ElevenLabs synthesis failed: {str(e)}"
            )
    
    async def get_voices(self) -> List[VoiceInfo]:
        """Get available voices"""
        if not self.client:
            await self.initialize()
        
        voices = []
        for voice_id, voice_data in self.voices.items():
            voices.append(VoiceInfo(
                voice_id=voice_id,
                name=voice_data["name"],
                language=voice_data["language"],
                gender=voice_data["gender"],
                description=voice_data.get("description")
            ))
        
        return voices


class AzureProvider:
    """Azure Cognitive Services provider implementation"""
    
    def __init__(self):
        self.client = None
        self.voices = {}
        self.models = {
            "en-US-JennyNeural": {
                "languages": ["en-US"],
                "streaming": True,
                "emotion_support": True
            },
            "vi-VN-HoaiMyNeural": {
                "languages": ["vi-VN"],
                "streaming": True,
                "emotion_support": True
            }
        }
    
    async def initialize(self):
        """Initialize Azure client"""
        if not settings.azure_speech_key:
            raise ValueError("Azure Speech API key not configured")
        
        try:
            import azure.cognitiveservices.speech as speechsdk
            self.speechsdk = speechsdk
            
            # Configure speech service
            self.speech_config = speechsdk.SpeechConfig(
                subscription=settings.azure_speech_key,
                region=settings.azure_speech_region or "eastus"
            )
            
            logger.info("Azure provider initialized")
        except ImportError:
            raise ImportError("Azure Cognitive Services library not installed")
    
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech using Azure"""
        if not self.client:
            await self.initialize()
        
        voice_name = request.voice_id or "en-US-JennyNeural"
        
        try:
            start_time = datetime.utcnow()
            
            # Configure speech synthesis
            self.speech_config.speech_synthesis_voice_name = voice_name
            
            # Create synthesizer
            speech_synthesizer = self.speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None
            )
            
            # Build SSML with emotion if specified
            if request.emotion:
                ssml = f"""
                <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{request.language}">
                    <voice name="{voice_name}">
                        <mstts:express-as style="{request.emotion}">
                            {request.text}
                        </mstts:express-as>
                    </voice>
                </speak>
                """
                result = await asyncio.to_thread(
                    speech_synthesizer.speak_ssml_async,
                    ssml
                ).get()
            else:
                result = await asyncio.to_thread(
                    speech_synthesizer.speak_text_async,
                    request.text
                ).get()
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            if result.reason == self.speechsdk.ResultReason.SynthesizingAudioCompleted:
                # Get audio data
                audio_data = result.audio_data
                
                # Encode to base64
                import base64
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                
                # Estimate duration
                duration = len(request.text) / 10
                
                return TTSResponse(
                    audio_data=audio_base64,
                    audio_format=request.output_format,
                    duration=duration,
                    provider="azure",
                    model=voice_name,
                    voice_id=voice_name,
                    processing_time=processing_time
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Speech synthesis failed: {result.error_details}"
                )
            
        except Exception as e:
            logger.error(f"Azure synthesis failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Azure synthesis failed: {str(e)}"
            )


class GoogleProvider:
    """Google Cloud Text-to-Speech provider implementation"""
    
    def __init__(self):
        self.client = None
        self.voices = {}
        self.models = {
            "en-US-Standard-A": {
                "languages": ["en-US"],
                "streaming": False,
                "emotion_support": False
            },
            "vi-VN-Standard-A": {
                "languages": ["vi-VN"],
                "streaming": False,
                "emotion_support": False
            }
        }
    
    async def initialize(self):
        """Initialize Google client"""
        if not settings.google_api_key:
            raise ValueError("Google API key not configured")
        
        try:
            from google.cloud.texttospeech import TextToSpeechClient
            self.client = TextToSpeechClient()
            
            # Load available voices
            voices = await asyncio.to_thread(self.client.list_voices)
            for voice in voices.voices:
                for language_code in voice.language_codes:
                    self.voices[voice.name] = {
                        "name": voice.name,
                        "language": language_code,
                        "gender": voice.ssml_gender.name,
                        "description": voice.name
                    }
            
            logger.info("Google provider initialized")
        except ImportError:
            raise ImportError("Google Cloud Text-to-Speech library not installed")
    
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech using Google"""
        if not self.client:
            await self.initialize()
        
        voice_name = request.voice_id or "en-US-Standard-A"
        
        try:
            from google.cloud.texttospeech import SynthesisInput, VoiceSelectionParams, AudioConfig
            
            start_time = datetime.utcnow()
            
            # Build synthesis input
            synthesis_input = SynthesisInput(text=request.text)
            
            # Build voice selection
            voice = VoiceSelectionParams(
                language_code=request.language,
                name=voice_name
            )
            
            # Build audio config
            audio_config = AudioConfig(
                audio_encoding=self.client.AudioEncoding.MP3
            )
            
            # Synthesize
            response = await asyncio.to_thread(
                self.client.synthesize_speech,
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Encode to base64
            import base64
            audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
            
            # Estimate duration
            duration = len(request.text) / 10
            
            return TTSResponse(
                audio_data=audio_base64,
                audio_format=request.output_format,
                duration=duration,
                provider="google",
                model=voice_name,
                voice_id=voice_name,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Google synthesis failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Google synthesis failed: {str(e)}"
            )


# Initialize providers
elevenlabs_provider = ElevenLabsProvider()
azure_provider = AzureProvider()
google_provider = GoogleProvider()

providers = {
    "elevenlabs": elevenlabs_provider,
    "azure": azure_provider,
    "google": google_provider
}


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting TTS Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down TTS Service")


# API endpoints
@app.post("/api/v1/tts/synthesize", response_model=TTSResponse)
async def synthesize_speech(request: TTSRequest):
    """
    Synthesize text to speech
    """
    try:
        # Select provider
        provider_name = request.provider or "elevenlabs"
        provider = providers.get(provider_name)
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider '{provider_name}' not supported"
            )
        
        # Synthesize
        response = await provider.synthesize(request)
        
        logger.info(f"Synthesized speech using {provider_name}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speech synthesis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {str(e)}"
        )


@app.get("/api/v1/tts/voices/{provider}")
async def get_voices(provider: str):
    """
    Get available voices for a provider
    """
    try:
        provider_instance = providers.get(provider)
        
        if not provider_instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider '{provider}' not supported"
            )
        
        voices = await provider_instance.get_voices()
        
        return {
            "provider": provider,
            "voices": voices
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get voices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get voices: {str(e)}"
        )


@app.get("/api/v1/tts/providers")
async def get_providers():
    """
    Get available TTS providers
    """
    return {
        "providers": [
            {
                "name": "elevenlabs",
                "models": elevenlabs_provider.models,
                "description": "ElevenLabs - High quality, emotion support"
            },
            {
                "name": "azure",
                "models": azure_provider.models,
                "description": "Azure Cognitive Services - Enterprise-grade"
            },
            {
                "name": "google",
                "models": google_provider.models,
                "description": "Google Cloud TTS - Multi-language support"
            }
        ]
    }


@app.get("/api/v1/tts/languages")
async def get_supported_languages():
    """
    Get supported languages for each provider
    """
    return {
        "elevenlabs": elevenlabs_provider.models["eleven_multilingual_v2"]["languages"],
        "azure": ["en-US", "vi-VN", "es-ES", "fr-FR", "de-DE", "ja-JP", "ko-KR", "zh-CN"],
        "google": ["en-US", "vi-VN", "es-ES", "fr-FR", "de-DE", "ja-JP", "ko-KR", "zh-CN"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "tts-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
