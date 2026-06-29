"""
Auth Service
Authentication business logic
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timedelta

from app.models.user import User, UserStatus, UserRole
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.core.exceptions import (
    UserNotFoundException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    EmailAlreadyExistsException
)
from app.config import settings


class AuthService:
    """Authentication service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """Register a new user."""
        # Check if username exists
        result = await self.db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise UserAlreadyExistsException("Username already exists")
        
        # Check if email exists
        result = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise EmailAlreadyExistsException("Email already exists")
        
        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            bio=user_data.bio,
            hashed_password=get_password_hash(user_data.password),
            status=UserStatus.PENDING,
            role=UserRole.USER
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return UserResponse.model_validate(user)
    
    async def authenticate_user(self, username: str, password: str) -> Token:
        """Authenticate user and return tokens."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsException("Invalid username or password")
        
        if not user.is_active:
            raise InvalidCredentialsException("User account is inactive")
        
        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.commit()
        
        # Create tokens
        token_data = {"sub": str(user.id), "username": user.username}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )
    
    async def refresh_tokens(self, refresh_token: str) -> Token:
        """Refresh access token using refresh token."""
        payload = verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise InvalidCredentialsException("Invalid refresh token")
        
        # Create new tokens
        token_data = {"sub": str(user.id), "username": user.username}
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token
        )
    
    async def logout_user(self, refresh_token: str):
        """Logout user and invalidate refresh token."""
        # TODO: Implement token blacklisting in Redis
        pass
    
    async def verify_user(self, user_id: str) -> Optional[User]:
        """Verify user exists and is active."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user and user.is_active:
            return user
        return None
