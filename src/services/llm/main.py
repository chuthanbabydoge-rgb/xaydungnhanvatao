"""Main FastAPI application for LLM Service"""
import time
import logging
import sys
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

# Ensure this directory is on sys.path for bare "from config import" imports
_llm_dir = os.path.dirname(os.path.abspath(__file__))
if _llm_dir not in sys.path:
    sys.path.insert(0, _llm_dir)

from config import get_settings
from app.api import v1_router
from app.db import init_db, close_db, init_redis, close_redis
from app.services import (
    OpenAIProvider,
    AnthropicProvider,
    model_router,
    response_cache
)
from app.core.exceptions import LLMServiceError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    # Startup
    logger.info("Starting LLM Service...")
    
    # Initialize database (non-fatal on failure)
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
    
    # Initialize Redis (non-fatal on failure)
    try:
        await init_redis()
        logger.info("Redis initialized")
    except Exception as e:
        logger.warning(f"Redis initialization skipped: {e}")
    
    # Initialize LLM providers (non-fatal on failure)
    try:
        if settings.OPENAI_API_KEY:
            openai_provider = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                org_id=settings.OPENAI_ORG_ID
            )
            await openai_provider.initialize()
            model_router.register_provider(openai_provider)
            logger.info("OpenAI provider initialized")
    except Exception as e:
        logger.warning(f"OpenAI provider initialization skipped: {e}")
    
    try:
        if settings.ANTHROPIC_API_KEY:
            anthropic_provider = AnthropicProvider(
                api_key=settings.ANTHROPIC_API_KEY,
                base_url=settings.ANTHROPIC_BASE_URL
            )
            await anthropic_provider.initialize()
            model_router.register_provider(anthropic_provider)
            logger.info("Anthropic provider initialized")
    except Exception as e:
        logger.warning(f"Anthropic provider initialization skipped: {e}")
    
    # Configure cache
    try:
        response_cache.set_cache_ttl(settings.CACHE_TTL)
        response_cache.set_cache_enabled_models(set(settings.CACHE_ENABLED_MODELS))
    except Exception as e:
        logger.warning(f"Cache configuration skipped: {e}")
    
    logger.info("LLM Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LLM Service...")
    
    try:
        await close_db()
        await close_redis()
        logger.info("LLM Service shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LLM Service for AI Companion Platform - Multi-LLM support with intelligent routing",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time=process_time,
    )
    
    return response


# Exception handlers
@app.exception_handler(LLMServiceError)
async def llm_service_error_handler(request: Request, exc: LLMServiceError):
    """Handle LLM service errors"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "LLM Service Error",
            "message": str(exc),
            "request_id": request.headers.get("X-Request-ID")
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID")
        }
    )


# Include routers
app.include_router(v1_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS if not settings.DEBUG else 1,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

