"""Security utilities for LLM Service"""
import os
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.exceptions import AuthenticationError


class SecurityManager:
    """Security manager for authentication and encryption"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        """Hash password"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=30)
        
        to_encode = data.copy()
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_access_token(self, token: str) -> Dict[str, Any]:
        """Decode JWT access token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
    
    def generate_api_key(self) -> str:
        """Generate secure API key"""
        return secrets.token_urlsafe(32)
    
    def verify_api_key(self, api_key: str, valid_keys: list[str]) -> bool:
        """Verify API key"""
        return api_key in valid_keys
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        # For production, use proper encryption like Fernet
        # This is a placeholder
        return secrets.token_urlsafe(len(data)) + data
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        # For production, use proper decryption
        # This is a placeholder
        return encrypted_data[43:]  # Remove prefix


def get_security_manager() -> SecurityManager:
    """Get security manager instance"""
    from config import get_settings
    settings = get_settings()
    return SecurityManager(settings.SECRET_KEY, settings.ALGORITHM)
