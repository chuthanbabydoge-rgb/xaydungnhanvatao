"""
Security Module
Auth Service
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.config import settings
from app.core.exceptions import InvalidTokenException, TokenExpiredException
from app.db.redis import is_token_blacklisted


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create an access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode a token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        if payload.get("type") != token_type:
            raise InvalidTokenException("Invalid token type")

        return payload
    except JWTError as e:
        if "expired" in str(e):
            raise TokenExpiredException("Token has expired")
        raise InvalidTokenException("Invalid token")


async def verify_token_async(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode a token with blacklist check."""
    try:
        # Check if token is blacklisted
        if await is_token_blacklisted(token):
            raise InvalidTokenException("Token has been revoked")

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        if payload.get("type") != token_type:
            raise InvalidTokenException("Invalid token type")

        return payload
    except JWTError as e:
        if "expired" in str(e):
            raise TokenExpiredException("Token has expired")
        raise InvalidTokenException("Invalid token")


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a token without verification (for debugging)."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_exp": False})
        return payload
    except JWTError:
        return None
