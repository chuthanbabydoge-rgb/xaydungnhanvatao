"""Voice Service Configuration"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Voice Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8003
    WORKERS: int = 4
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/voice_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600
    REDIS_MAX_CONNECTIONS: int = 50
    
    # OpenAI (Whisper)
    OPENAI_API_KEY: Optional[str] = None
    
    # Deepgram
    DEEPGRAM_API_KEY: Optional[str] = None
    
    # ElevenLabs (TTS + Voice Cloning)
    ELEVENLABS_API_KEY: Optional[str] = None
    
    # TTS Settings
    DEFAULT_TTS_MODEL: str = "eleven_multilingual_v2"
    DEFAULT_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"
    SUPPORTED_LANGUAGES: List[str] = ["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh"]
    
    # STT Settings
    DEFAULT_STT_MODEL: str = "whisper-1"
    SUPPORTED_AUDIO_FORMATS: List[str] = ["wav", "mp3", "ogg", "flac", "m4a"]
    MAX_AUDIO_SIZE_MB: int = 25
    
    # Voice Cloning
    ENABLE_VOICE_CLONING: bool = True
    MIN_CLONE_SAMPLES: int = 30
    MAX_CLONE_SAMPLES: int = 100
    
    # Audio Processing
    SAMPLE_RATE: int = 16000
    AUDIO_QUALITY: str = "high"  # low, medium, high
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 30
    RATE_LIMIT_AUDIO_MB_PER_MINUTE: int = 100
    
    # Monitoring
    ENABLE_TRACING: bool = True
    JAEGER_HOST: str = "localhost"
    JAEGER_PORT: int = 6831
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9003
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
