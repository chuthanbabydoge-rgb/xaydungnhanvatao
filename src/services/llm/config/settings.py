"""LLM Service Configuration"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "LLM Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    WORKERS: int = 4
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/llm_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600
    REDIS_MAX_CONNECTIONS: int = 50
    
    # LLM Providers
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ORG_ID: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_PROJECT_ID: Optional[str] = None
    
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    
    # Local LLM
    LOCAL_LLM_PATH: Optional[str] = None
    LOCAL_LLM_DEVICE: str = "cuda"  # cuda, cpu, mps
    LOCAL_LLM_QUANTIZE: bool = True
    LOCAL_LLM_GPTQ: bool = False
    
    # Model Configuration
    DEFAULT_MODEL: str = "gpt-4"
    DEFAULT_MODEL_MAX_TOKENS: int = 4096
    DEFAULT_MODEL_TEMPERATURE: float = 0.7
    DEFAULT_MODEL_TOP_P: float = 0.9
    DEFAULT_MODEL_FREQUENCY_PENALTY: float = 0.0
    DEFAULT_MODEL_PRESENCE_PENALTY: float = 0.0
    
    # Model Selection
    ENABLE_MODEL_ROUTING: bool = True
    ROUTING_STRATEGY: str = "cost_optimized"  # cost_optimized, quality_optimized, speed_optimized
    COST_PER_1K_TOKENS: float = 0.002  # Average cost
    
    # Context Management
    MAX_CONTEXT_LENGTH: int = 128000
    CONTEXT_COMPRESSION_THRESHOLD: float = 0.8
    ENABLE_CONTEXT_COMPRESSION: bool = True
    ENABLE_LONG_CONTEXT: bool = True
    
    # Streaming
    ENABLE_STREAMING: bool = True
    STREAM_CHUNK_SIZE: int = 512
    
    # Caching
    ENABLE_RESPONSE_CACHE: bool = True
    CACHE_ENABLED_MODELS: List[str] = ["gpt-3.5-turbo", "claude-3-haiku"]
    CACHE_TTL: int = 3600
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_TOKENS_PER_MINUTE: int = 90000
    
    # Monitoring
    ENABLE_TRACING: bool = True
    JAEGER_HOST: str = "localhost"
    JAEGER_PORT: int = 6831
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9002
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Feature Flags
    ENABLE_FUNCTION_CALLING: bool = True
    ENABLE_CODE_INTERPRETER: bool = False
    ENABLE_WEB_SEARCH: bool = False
    ENABLE_PLUGINS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
