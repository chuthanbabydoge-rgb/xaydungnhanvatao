"""Database models for LLM Service"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid


Base = declarative_base()


class LLMRequest(Base):
    """LLM request model"""
    __tablename__ = "llm_requests"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=True, index=True)
    
    # Request details
    model_provider = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=True)
    
    # Request content
    prompt = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=True)
    messages = Column(JSON, nullable=True)
    
    # Parameters
    max_tokens = Column(Integer, default=4096)
    temperature = Column(Float, default=0.7)
    top_p = Column(Float, default=0.9)
    frequency_penalty = Column(Float, default=0.0)
    presence_penalty = Column(Float, default=0.0)
    
    # Response
    response = Column(Text, nullable=True)
    finish_reason = Column(String(50), nullable=True)
    usage = Column(JSON, nullable=True)
    
    # Metrics
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    processing_time_ms = Column(Float, default=0.0)
    first_token_time_ms = Column(Float, nullable=True)
    
    # Cost tracking
    cost = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    
    # Status
    status = Column(String(20), default="pending", index=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    request_type = Column(String(50), default="chat", index=True)
    cached = Column(Boolean, default=False, index=True)
    function_call = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="llm_requests")
    session = relationship("Session", back_populates="llm_requests")
    
    def __repr__(self):
        return f"<LLMRequest(id={self.id}, model={self.model_name}, status={self.status})>"


class LLMCache(Base):
    """LLM response cache model"""
    __tablename__ = "llm_cache"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Cache key
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Request details
    model_provider = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    
    # Request content (hashed)
    prompt_hash = Column(String(64), nullable=False, index=True)
    system_prompt_hash = Column(String(64), nullable=True)
    
    # Response
    response = Column(Text, nullable=False)
    usage = Column(JSON, nullable=True)
    
    # Metrics
    total_tokens = Column(Integer, default=0)
    processing_time_ms = Column(Float, default=0.0)
    
    # Cache metadata
    hit_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    # Size tracking
    response_size_bytes = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<LLMCache(cache_key={self.cache_key}, model={self.model_name}, hits={self.hit_count})>"


class ModelConfig(Base):
    """Model configuration model"""
    __tablename__ = "model_configs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Model identification
    provider = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=True)
    display_name = Column(String(200), nullable=False)
    
    # Model capabilities
    max_context_length = Column(Integer, default=4096)
    max_output_tokens = Column(Integer, default=4096)
    supports_function_calling = Column(Boolean, default=False)
    supports_vision = Column(Boolean, default=False)
    supports_streaming = Column(Boolean, default=True)
    
    # Pricing
    input_cost_per_1k = Column(Float, default=0.0)
    output_cost_per_1k = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    
    # Performance
    avg_latency_ms = Column(Float, default=0.0)
    p50_latency_ms = Column(Float, default=0.0)
    p95_latency_ms = Column(Float, default=0.0)
    p99_latency_ms = Column(Float, default=0.0)
    
    # Quality metrics
    quality_score = Column(Float, default=0.0)
    user_satisfaction = Column(Float, default=0.0)
    
    # Routing rules
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True, index=True)
    requires_key = Column(Boolean, default=True)
    
    # Rate limits
    requests_per_minute = Column(Integer, default=60)
    tokens_per_minute = Column(Integer, default=90000)
    
    # Feature flags
    features = Column(JSON, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ModelConfig(provider={self.provider}, model={self.model_name}, enabled={self.enabled})>"


class UsageStats(Base):
    """Usage statistics model"""
    __tablename__ = "usage_stats"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Time period
    period = Column(String(20), nullable=False, index=True)  # hourly, daily, weekly, monthly
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    
    # User level
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=True, index=True)
    
    # Model level
    model_provider = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    
    # Request counts
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    cached_requests = Column(Integer, default=0)
    
    # Token usage
    total_prompt_tokens = Column(Integer, default=0)
    total_completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Cost
    total_cost = Column(Float, default=0.0)
    
    # Performance
    avg_processing_time_ms = Column(Float, default=0.0)
    avg_first_token_time_ms = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="usage_stats")
    session = relationship("Session", back_populates="usage_stats")
    
    def __repr__(self):
        return f"<UsageStats(period={self.period}, requests={self.total_requests}, cost={self.total_cost})>"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Preferences
    preferred_model = Column(String(100), nullable=True)
    preferred_language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    
    # Quota
    monthly_quota = Column(Integer, default=1000000)
    monthly_usage = Column(Integer, default=0)
    quota_reset_at = Column(DateTime, nullable=True)
    
    # Subscription
    subscription_tier = Column(String(50), default="free")
    subscription_expires_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    llm_requests = relationship("LLMRequest", back_populates="user")
    usage_stats = relationship("UsageStats", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"


class Session(Base):
    """Session model"""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # Session details
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    device_info = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Context
    context_data = Column(JSON, nullable=True)
    memory_data = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    
    # Relationships
    user = relationship("User")
    llm_requests = relationship("LLMRequest", back_populates="session")
    usage_stats = relationship("UsageStats", back_populates="session")
    
    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"
