"""
Auth Service - Authentication and Authorization
AI Companion Platform
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.config import settings
from app.dependencies import get_db, get_redis
from app.api.v1 import auth, users
from app.core.security import create_access_token, verify_token
from app.core.exceptions import (
    AuthException,
    UserNotFoundException,
    InvalidCredentialsException
)

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# FastAPI app
app = FastAPI(
    title="AI Companion Auth Service",
    description="Authentication and authorization service for AI Companion Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Starting Auth Service...")
    # Startup logic here
    yield
    logger.info("Shutting down Auth Service...")


app.router.lifespan_context = lifespan


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": "1.0.0"
    }


# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])


# Exception handlers
@app.exception_handler(AuthException)
async def auth_exception_handler(request, exc: AuthException):
    """Handle authentication exceptions."""
    logger.error(f"Auth exception: {exc.message}")
    return {
        "error": "authentication_error",
        "message": exc.message,
        "detail": exc.detail
    }, status.HTTP_401_UNAUTHORIZED


@app.exception_handler(UserNotFoundException)
async def user_not_found_handler(request, exc: UserNotFoundException):
    """Handle user not found exceptions."""
    logger.error(f"User not found: {exc.message}")
    return {
        "error": "user_not_found",
        "message": exc.message
    }, status.HTTP_404_NOT_FOUND


@app.exception_handler(InvalidCredentialsException)
async def invalid_credentials_handler(request, exc: InvalidCredentialsException):
    """Handle invalid credentials exceptions."""
    logger.error(f"Invalid credentials: {exc.message}")
    return {
        "error": "invalid_credentials",
        "message": exc.message
    }, status.HTTP_401_UNAUTHORIZED


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return {
        "error": "internal_server_error",
        "message": "An unexpected error occurred"
    }, status.HTTP_500_INTERNAL_SERVER_ERROR


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )