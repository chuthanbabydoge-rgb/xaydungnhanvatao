"""
Voice Service - Speech-to-text, text-to-speech, voice synthesis, and audio processing
Handles voice input/output for the AI character pipeline
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, WebSocket
from pydantic import BaseModel
import wave
import io
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from prometheus_client import Counter, Histogram, Gauge, start_http_server


class VoiceTaskType(Enum):
    """Types of voice tasks"""
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    VOICE_CLONING = "voice_cloning"
    VOICE_CONVERSION = "voice_conversion"
    AUDIO_PROCESSING = "audio_processing"
    LIP_SYNC = "lip_sync"
    NOISE_REDUCTION = "noise_reduction"


class AudioFormat(Enum):
    """Audio format options"""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"
    PCM = "pcm"


class VoiceQuality(Enum):
    """Voice quality presets"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass
class AudioData:
    """Represents audio data"""
    audio_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: bytes = b""
    format: AudioFormat = AudioFormat.WAV
    sample_rate: int = 16000
    channels: int = 1
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "audio_id": self.audio_id,
            "format": self.format.value,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration": self.duration,
            "size": len(self.data),
            "metadata": self.metadata
        }


@dataclass
class TranscriptionResult:
    """Represents speech-to-text result"""
    transcription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    confidence: float = 0.0
    language: str = "en"
    segments: List[Dict[str, Any]] = field(default_factory=list)
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcription_id": self.transcription_id,
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "segments": self.segments,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SynthesisResult:
    """Represents text-to-speech result"""
    synthesis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    audio_data: AudioData = field(default_factory=AudioData)
    text: str = ""
    voice_id: str = ""
    quality: VoiceQuality = VoiceQuality.MEDIUM
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "audio_data": self.audio_data.to_dict(),
            "text": self.text,
            "voice_id": self.voice_id,
            "quality": self.quality.value,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class VoiceProfile:
    """Represents a voice profile for synthesis"""
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    gender: str = "neutral"
    age_range: str = "adult"
    accent: str = "neutral"
    pitch: float = 1.0
    speed: float = 1.0
    emotion: str = "neutral"
    characteristics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "gender": self.gender,
            "age_range": self.age_range,
            "accent": self.accent,
            "pitch": self.pitch,
            "speed": self.speed,
            "emotion": self.emotion,
            "characteristics": self.characteristics
        }


@dataclass
class LipSyncData:
    """Represents lip sync animation data"""
    sync_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phonemes: List[str] = field(default_factory=list)
    visemes: List[Dict[str, Any]] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "phonemes": self.phonemes,
            "visemes": self.visemes,
            "timestamps": self.timestamps,
            "duration": self.duration
        }


class VoiceService:
    """
    Voice Service - Handles speech-to-text, text-to-speech, and audio processing
    Provides voice input/output capabilities for the AI pipeline
    """
    
    def __init__(self):
        # Voice profiles
        self.voice_profiles: Dict[str, VoiceProfile] = {}
        
        # Audio cache
        self.audio_cache: Dict[str, AudioData] = {}
        
        # Processing parameters
        self.default_sample_rate = 16000
        self.default_channels = 1
        
        # Metrics
        self.stt_requests = Counter('voice_stt_requests_total', 'Total STT requests', ['status'])
        self.tts_requests = Counter('voice_tts_requests_total', 'Total TTS requests', ['status'])
        self.audio_processing_time = Histogram('voice_processing_seconds', 'Audio processing time', ['operation'])
        self.audio_duration = Gauge('voice_audio_duration_seconds', 'Audio duration')
        self.cache_size = Gauge('voice_cache_size', 'Audio cache size')
        
        # Tracing
        self.setup_tracing()
        self.tracer = trace.get_tracer(__name__)
        
        # Logger
        self.logger = logging.getLogger("voice_service")
    
    def setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()
        
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        tracer_provider.add_span_processor(span_processor)
    
    async def initialize(self):
        """Initialize voice service with default voice profiles"""
        with self.tracer.start_as_current_span("initialize_voice") as span:
            try:
                # Load default voice profiles
                await self._load_default_voice_profiles()
                
                self.logger.info("Voice service initialized successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize voice service: {e}")
                span.record_exception(e)
                return False
    
    async def _load_default_voice_profiles(self):
        """Load default voice profiles"""
        default_profiles = [
            VoiceProfile(
                name="default_male",
                gender="male",
                age_range="adult",
                accent="neutral",
                pitch=1.0,
                speed=1.0,
                emotion="neutral"
            ),
            VoiceProfile(
                name="default_female",
                gender="female",
                age_range="adult",
                accent="neutral",
                pitch=1.2,
                speed=1.0,
                emotion="neutral"
            ),
            VoiceProfile(
                name="friendly",
                gender="neutral",
                age_range="young_adult",
                accent="neutral",
                pitch=1.1,
                speed=1.05,
                emotion="happy",
                characteristics={"warmth": 0.8, "energy": 0.7}
            )
        ]
        
        for profile in default_profiles:
            self.voice_profiles[profile.profile_id] = profile
    
    async def speech_to_text(self, audio_data: AudioData, language: str = "en") -> TranscriptionResult:
        """Convert speech to text"""
        with self.tracer.start_as_current_span("speech_to_text") as span:
            import time
            start_time = time.time()
            
            span.set_attribute("audio_id", audio_data.audio_id)
            span.set_attribute("language", language)
            
            result = TranscriptionResult(
                language=language
            )
            
            try:
                # Simulate speech-to-text processing
                # In production, use Whisper, Google Speech-to-Text, or similar
                
                # Convert audio to numpy array
                audio_array = self._bytes_to_audio_array(audio_data)
                
                # Process audio (simulated)
                text = await self._simulate_stt(audio_array, language)
                
                result.text = text
                result.confidence = 0.85  # Simulated confidence
                result.processing_time = time.time() - start_time
                
                # Update metrics
                self.stt_requests.labels(status="success").inc()
                self.audio_processing_time.labels(operation="stt").observe(result.processing_time)
                
                span.set_attribute("text_length", len(text))
                span.set_attribute("confidence", result.confidence)
                
                self.logger.info(f"STT processing completed for {audio_data.audio_id}")
                return result
                
            except Exception as e:
                self.logger.error(f"Speech-to-text error: {e}")
                result.processing_time = time.time() - start_time
                self.stt_requests.labels(status="error").inc()
                span.record_exception(e)
                return result
    
    async def text_to_speech(self, text: str, voice_profile_id: str = None, 
                           quality: VoiceQuality = VoiceQuality.MEDIUM) -> SynthesisResult:
        """Convert text to speech"""
        with self.tracer.start_as_current_span("text_to_speech") as span:
            import time
            start_time = time.time()
            
            span.set_attribute("text_length", len(text))
            span.set_attribute("quality", quality.value)
            
            result = SynthesisResult(
                text=text,
                quality=quality
            )
            
            try:
                # Get voice profile
                if voice_profile_id and voice_profile_id in self.voice_profiles:
                    voice_profile = self.voice_profiles[voice_profile_id]
                    result.voice_id = voice_profile_id
                else:
                    # Use default profile
                    voice_profile = list(self.voice_profiles.values())[0] if self.voice_profiles else None
                    result.voice_id = voice_profile.profile_id if voice_profile else "default"
                
                # Generate speech (simulated)
                audio_data = await self._simulate_tts(text, voice_profile, quality)
                
                result.audio_data = audio_data
                result.processing_time = time.time() - start_time
                
                # Cache audio
                self.audio_cache[audio_data.audio_id] = audio_data
                self.cache_size.set(len(self.audio_cache))
                
                # Update metrics
                self.tts_requests.labels(status="success").inc()
                self.audio_processing_time.labels(operation="tts").observe(result.processing_time)
                self.audio_duration.set(audio_data.duration)
                
                span.set_attribute("audio_duration", audio_data.duration)
                
                self.logger.info(f"TTS processing completed for text length {len(text)}")
                return result
                
            except Exception as e:
                self.logger.error(f"Text-to-speech error: {e}")
                result.processing_time = time.time() - start_time
                self.tts_requests.labels(status="error").inc()
                span.record_exception(e)
                return result
    
    async def generate_lip_sync(self, text: str, audio_data: AudioData = None) -> LipSyncData:
        """Generate lip sync animation data"""
        with self.tracer.start_as_current_span("generate_lip_sync") as span:
            import time
            start_time = time.time()
            
            span.set_attribute("text_length", len(text))
            
            lip_sync = LipSyncData()
            
            try:
                # Convert text to phonemes (simplified)
                phonemes = await self._text_to_phonemes(text)
                
                # Generate visemes and timestamps
                visemes = []
                timestamps = []
                duration_per_phoneme = 0.1  # 100ms per phoneme
                
                for i, phoneme in enumerate(phonemes):
                    viseme = self._phoneme_to_viseme(phoneme)
                    visemes.append({
                        "viseme": viseme,
                        "intensity": 1.0,
                        "transition": 0.05
                    })
                    timestamps.append(i * duration_per_phoneme)
                
                lip_sync.phonemes = phonemes
                lip_sync.visemes = visemes
                lip_sync.timestamps = timestamps
                lip_sync.duration = len(phonemes) * duration_per_phoneme
                
                # Update metrics
                self.audio_processing_time.labels(operation="lip_sync").observe(time.time() - start_time)
                
                span.set_attribute("phoneme_count", len(phonemes))
                
                self.logger.info(f"Lip sync generated for {len(phonemes)} phonemes")
                return lip_sync
                
            except Exception as e:
                self.logger.error(f"Lip sync generation error: {e}")
                span.record_exception(e)
                return lip_sync
    
    async def process_audio(self, audio_data: AudioData, operations: List[str]) -> AudioData:
        """Process audio with various operations"""
        with self.tracer.start_as_current_span("process_audio") as span:
            import time
            start_time = time.time()
            
            span.set_attribute("operations", operations)
            
            processed_audio = audio_data
            
            try:
                # Convert to numpy array
                audio_array = self._bytes_to_audio_array(audio_data)
                
                # Apply operations
                for operation in operations:
                    if operation == "noise_reduction":
                        audio_array = await self._reduce_noise(audio_array)
                    elif operation == "normalize":
                        audio_array = await self._normalize_audio(audio_array)
                    elif operation == "trim_silence":
                        audio_array = await self._trim_silence(audio_array)
                    elif operation == "resample":
                        audio_array = await self._resample_audio(audio_array, 16000)
                
                # Convert back to bytes
                processed_data = self._audio_array_to_bytes(audio_array, audio_data.format)
                
                processed_audio = AudioData(
                    data=processed_data,
                    format=audio_data.format,
                    sample_rate=16000,
                    channels=1,
                    duration=len(audio_array) / 16000
                )
                
                # Update metrics
                self.audio_processing_time.labels(operation="process").observe(time.time() - start_time)
                
                self.logger.info(f"Audio processing completed with {len(operations)} operations")
                return processed_audio
                
            except Exception as e:
                self.logger.error(f"Audio processing error: {e}")
                span.record_exception(e)
                return audio_data
    
    async def create_voice_profile(self, name: str, characteristics: Dict[str, Any]) -> str:
        """Create a new voice profile"""
        profile = VoiceProfile(
            name=name,
            gender=characteristics.get("gender", "neutral"),
            age_range=characteristics.get("age_range", "adult"),
            accent=characteristics.get("accent", "neutral"),
            pitch=characteristics.get("pitch", 1.0),
            speed=characteristics.get("speed", 1.0),
            emotion=characteristics.get("emotion", "neutral"),
            characteristics=characteristics.get("characteristics", {})
        )
        
        self.voice_profiles[profile.profile_id] = profile
        
        self.logger.info(f"Created voice profile {profile.profile_id}")
        return profile.profile_id
    
    def _bytes_to_audio_array(self, audio_data: AudioData) -> np.ndarray:
        """Convert audio bytes to numpy array"""
        # Simplified conversion - in production use proper audio libraries
        try:
            # Assume 16-bit PCM
            audio_array = np.frombuffer(audio_data.data, dtype=np.int16)
            
            # Normalize to -1 to 1
            audio_array = audio_array.astype(np.float32) / 32768.0
            
            return audio_array
        except:
            # Fallback for simulation
            return np.random.uniform(-0.5, 0.5, int(audio_data.duration * audio_data.sample_rate))
    
    def _audio_array_to_bytes(self, audio_array: np.ndarray, audio_format: AudioFormat) -> bytes:
        """Convert numpy array to audio bytes"""
        # Convert back to 16-bit PCM
        audio_array = (audio_array * 32767.0).astype(np.int16)
        return audio_array.tobytes()
    
    async def _simulate_stt(self, audio_array: np.ndarray, language: str) -> str:
        """Simulate speech-to-text (placeholder)"""
        # In production, use Whisper or similar
        # This is a simulation for demonstration
        
        # Generate placeholder text based on audio characteristics
        duration = len(audio_array) / 16000
        
        if duration < 1.0:
            return "Hello"
        elif duration < 3.0:
            return "Hello, how are you today?"
        elif duration < 5.0:
            return "Hello, how are you today? I hope you're doing well."
        else:
            return "Hello, how are you today? I hope you're doing well. This is a simulated transcription for demonstration purposes."
    
    async def _simulate_tts(self, text: str, voice_profile: VoiceProfile, 
                           quality: VoiceQuality) -> AudioData:
        """Simulate text-to-speech (placeholder)"""
        # In production, use Coqui TTS, VITS, or similar
        # This is a simulation for demonstration
        
        # Calculate duration based on text length and speaking rate
        words = len(text.split())
        duration = (words / 150.0) * voice_profile.speed  # 150 words per minute average
        
        # Generate audio data (simulated)
        sample_rate = 16000
        samples = int(duration * sample_rate)
        
        # Generate simple sine wave audio
        t = np.linspace(0, duration, samples)
        frequency = 440 * voice_profile.pitch  # A4 note modified by pitch
        audio_array = 0.5 * np.sin(2 * np.pi * frequency * t)
        
        # Add some variation for more natural sound
        audio_array += 0.1 * np.sin(2 * np.pi * 880 * t)  # Harmonic
        audio_array += 0.05 * np.random.normal(0, 0.1, samples)  # Noise
        
        # Convert to bytes
        audio_array = (audio_array * 32767.0).astype(np.int16)
        audio_bytes = audio_array.tobytes()
        
        return AudioData(
            data=audio_bytes,
            format=AudioFormat.WAV,
            sample_rate=sample_rate,
            channels=1,
            duration=duration
        )
    
    async def _text_to_phonemes(self, text: str) -> List[str]:
        """Convert text to phonemes (simplified)"""
        # In production, use a proper phoneme converter
        # This is a simplified version
        
        phonemes = []
        for word in text.lower().split():
            # Simple word-to-phoneme mapping
            if word == "hello":
                phonemes.extend(["HH", "AH", "L", "OW"])
            elif word == "how":
                phonemes.extend(["HH", "AW"])
            elif word == "are":
                phonemes.extend(["AA", "R"])
            elif word == "you":
                phonemes.extend(["Y", "UW"])
            else:
                # Generate generic phonemes for unknown words
                for char in word:
                    phonemes.append(char.upper())
        
        return phonemes
    
    def _phoneme_to_viseme(self, phoneme: str) -> str:
        """Convert phoneme to viseme"""
        # Simplified phoneme-to-viseme mapping
        viseme_map = {
            "AA": "open", "AE": "open", "AH": "open", "AO": "open",
            "EH": "wide", "EY": "wide", "IH": "wide", "IY": "wide",
            "UW": "round", "OW": "round", "UH": "round",
            "M": "closed", "B": "closed", "P": "closed",
            "F": "bite", "V": "bite",
            "L": "tongue", "R": "tongue",
            "S": "teeth", "Z": "teeth", "SH": "teeth", "ZH": "teeth",
            "TH": "tongue", "DH": "tongue",
            "K": "back", "G": "back", "NG": "back",
            "HH": "open", "N": "tongue", "T": "teeth", "D": "tongue"
        }
        
        return viseme_map.get(phoneme, "neutral")
    
    async def _reduce_noise(self, audio_array: np.ndarray) -> np.ndarray:
        """Reduce noise in audio (simplified)"""
        # In production, use proper noise reduction algorithms
        # Simple spectral subtraction simulation
        return audio_array * 0.95  # Reduce amplitude slightly
    
    async def _normalize_audio(self, audio_array: np.ndarray) -> np.ndarray:
        """Normalize audio amplitude"""
        max_amplitude = np.max(np.abs(audio_array))
        if max_amplitude > 0:
            return audio_array / max_amplitude
        return audio_array
    
    async def _trim_silence(self, audio_array: np.ndarray) -> np.ndarray:
        """Trim silence from audio (simplified)"""
        # In production, use proper silence detection
        threshold = 0.01
        mask = np.abs(audio_array) > threshold
        return audio_array[mask]
    
    async def _resample_audio(self, audio_array: np.ndarray, target_rate: int) -> np.ndarray:
        """Resample audio to target rate (simplified)"""
        # In production, use proper resampling
        # This is a placeholder
        return audio_array


# FastAPI application
app = FastAPI(title="Voice Service")
voice_service: Optional[VoiceService] = None


class STTInput(BaseModel):
    """Input for speech-to-text"""
    audio_data: str  # Base64 encoded audio
    format: str = "wav"
    sample_rate: int = 16000
    language: str = "en"


class TTSInput(BaseModel):
    """Input for text-to-speech"""
    text: str
    voice_profile_id: Optional[str] = None
    quality: str = "medium"


class LipSyncInput(BaseModel):
    """Input for lip sync generation"""
    text: str
    audio_data: Optional[str] = None


class AudioProcessingInput(BaseModel):
    """Input for audio processing"""
    audio_data: str  # Base64 encoded audio
    format: str = "wav"
    operations: List[str] = []


class VoiceProfileInput(BaseModel):
    """Input for voice profile creation"""
    name: str
    gender: str = "neutral"
    age_range: str = "adult"
    accent: str = "neutral"
    pitch: float = 1.0
    speed: float = 1.0
    emotion: str = "neutral"
    characteristics: Dict[str, float] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize voice service on startup"""
    global voice_service
    voice_service = VoiceService()
    await voice_service.initialize()
    
    # Start metrics server
    start_http_server(8007)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup voice service on shutdown"""
    if voice_service:
        # Cleanup if needed
        pass


@app.get("/status")
async def get_status():
    """Get voice service status"""
    return {
        "status": "running",
        "voice_profiles_count": len(voice_service.voice_profiles) if voice_service else 0,
        "audio_cache_size": len(voice_service.audio_cache) if voice_service else 0
    }


@app.post("/stt")
async def speech_to_text_endpoint(stt_input: STTInput):
    """Convert speech to text"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not initialized")
    
    import base64
    audio_bytes = base64.b64decode(stt_input.audio_data)
    
    audio_data = AudioData(
        data=audio_bytes,
        format=AudioFormat(stt_input.format),
        sample_rate=stt_input.sample_rate,
        channels=1,
        duration=len(audio_bytes) / (stt_input.sample_rate * 2)  # Approximate
    )
    
    result = await voice_service.speech_to_text(audio_data, stt_input.language)
    
    return result.to_dict()


@app.post("/tts")
async def text_to_speech_endpoint(tts_input: TTSInput):
    """Convert text to speech"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not initialized")
    
    result = await voice_service.text_to_speech(
        tts_input.text,
        tts_input.voice_profile_id,
        VoiceQuality(tts_input.quality)
    )
    
    # Return audio data as base64
    import base64
    response_dict = result.to_dict()
    response_dict["audio_data_base64"] = base64.b64encode(result.audio_data.data).decode('utf-8')
    
    return response_dict


@app.post("/lip_sync")
async def generate_lip_sync_endpoint(lip_sync_input: LipSyncInput):
    """Generate lip sync animation data"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not initialized")
    
    audio_data = None
    if lip_sync_input.audio_data:
        import base64
        audio_bytes = base64.b64decode(lip_sync_input.audio_data)
        audio_data = AudioData(
            data=audio_bytes,
            format=AudioFormat.WAV,
            sample_rate=16000,
            channels=1
        )
    
    lip_sync = await voice_service.generate_lip_sync(lip_sync_input.text, audio_data)
    
    return lip_sync.to_dict()


@app.post("/process_audio")
async def process_audio_endpoint(processing_input: AudioProcessingInput):
    """Process audio with various operations"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not initialized")
    
    import base64
    audio_bytes = base64.b64decode(processing_input.audio_data)
    
    audio_data = AudioData(
        data=audio_bytes,
        format=AudioFormat(processing_input.format),
        sample_rate=16000,
        channels=1
    )
    
    processed_audio = await voice_service.process_audio(audio_data, processing_input.operations)
    
    # Return processed audio as base64
    response = {
        "audio_data_base64": base64.b64encode(processed_audio.data).decode('utf-8'),
        "format": processed_audio.format.value,
        "sample_rate": processed_audio.sample_rate,
        "duration": processed_audio.duration
    }
    
    return response


@app.post("/voice_profiles")
async def create_voice_profile_endpoint(profile_input: VoiceProfileInput):
    """Create a new voice profile"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not initialized")
    
    characteristics = {
        "gender": profile_input.gender,
        "age_range": profile_input.age_range,
        "accent": profile_input.accent,
        "pitch": profile_input.pitch,
        "speed": profile_input.speed,
        "emotion": profile_input.emotion,
        "characteristics": profile_input.characteristics
    }
    
    profile_id = await voice_service.create_voice_profile(profile_input.name, characteristics)
    
    return {"profile_id": profile_id, "status": "created"}


@app.get("/voice_profiles")
async def list_voice_profiles():
    """List all voice profiles"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not initialized")
    
    profiles = [profile.to_dict() for profile in voice_service.voice_profiles.values()]
    
    return {"profiles": profiles, "count": len(profiles)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
