"""
Authentication API Routes
Auth Service
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from app.dependencies import get_db
from app.schemas.user import (
    LoginRequest,
    RegisterRequest,
    Token,
    UserResponse,
    UserCreate
)
from app.services.auth_service import AuthService
from app.core.security import verify_token
from app.core.exceptions import (
    InvalidCredentialsException,
    UserAlreadyExistsException
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.register_user(user_data)
        return user
    except UserAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login user and return tokens."""
    auth_service = AuthService(db)
    
    try:
        tokens = await auth_service.authenticate_user(
            username=form_data.username,
            password=form_data.password
        )
        return tokens
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)
    
    try:
        tokens = await auth_service.refresh_tokens(refresh_token)
        return tokens
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout")
async def logout(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Logout user and invalidate refresh token."""
    auth_service = AuthService(db)
    await auth_service.logout_user(refresh_token)
    return {"message": "Successfully logged out"}


@router.post("/verify-token")
async def verify_token_endpoint(token: str):
    """Verify token validity."""
    try:
        payload = verify_token(token)
        return {"valid": True, "payload": payload}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
