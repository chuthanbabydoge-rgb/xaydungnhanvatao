"""
Auth Service - Authentication and Authorization
Handles user authentication, JWT token generation, and authorization
"""
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import hashlib
import secrets
import jwt
import bcrypt

from shared.database.postgres import get_postgres
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Auth Service",
    description="Authentication and authorization for AI Companion",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# JWT Configuration
JWT_SECRET = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


# Pydantic models
class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    username: Optional[str] = Field(default=None, description="Username")
    full_name: Optional[str] = Field(default=None, description="Full name")


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str = Field(..., description="Refresh token")


class PasswordChange(BaseModel):
    """Password change request"""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class PasswordReset(BaseModel):
    """Password reset request"""
    email: EmailStr = Field(..., description="User email")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class VerifyToken(BaseModel):
    """Token verification response"""
    valid: bool = Field(..., description="Whether token is valid")
    user_id: Optional[str] = Field(default=None, description="User ID if valid")
    expires_at: Optional[datetime] = Field(default=None, description="Token expiration time")


# Helper functions
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Check if token is blacklisted
    redis = await get_redis()
    is_blacklisted = await redis.exists(f"blacklist:{token}")
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "user")
    }


async def require_role(required_role: str):
    """Dependency to require specific role"""
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "user")
        
        if user_role != required_role and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        
        return current_user
    
    return role_checker


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Auth Service")
    
    # Create users table if it doesn't exist
    postgres = await get_postgres()
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            username VARCHAR(100) UNIQUE,
            full_name VARCHAR(255),
            role VARCHAR(50) DEFAULT 'user',
            is_active BOOLEAN DEFAULT true,
            is_verified BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token VARCHAR(500) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked_at TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token VARCHAR(500) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    logger.info("Auth Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Auth Service")


# API endpoints
@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
async def register(request: UserRegister):
    """
    Register a new user
    """
    try:
        postgres = await get_postgres()
        
        # Check if email already exists
        existing_user = await postgres.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            request.email
        )
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        if request.username:
            existing_username = await postgres.fetchrow(
                "SELECT id FROM users WHERE username = $1",
                request.username
            )
            
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Insert user
        user_id = await postgres.fetchval("""
            INSERT INTO users (email, password_hash, username, full_name)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, request.email, password_hash, request.username, request.full_name)
        
        logger.info(f"User registered: {request.email}")
        
        return {
            "user_id": str(user_id),
            "email": request.email,
            "message": "Registration successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(request: UserLogin):
    """
    Login user and return JWT tokens
    """
    try:
        postgres = await get_postgres()
        
        # Get user by email
        user = await postgres.fetchrow(
            "SELECT id, email, password_hash, role, is_active FROM users WHERE email = $1",
            request.email
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Create tokens
        access_token = create_access_token({
            "sub": str(user["id"]),
            "email": user["email"],
            "role": user["role"]
        })
        
        refresh_token = create_refresh_token({
            "sub": str(user["id"])
        })
        
        # Store refresh token in database
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        await postgres.execute("""
            INSERT INTO refresh_tokens (user_id, token, expires_at)
            VALUES ($1, $2, $3)
        """, user["id"], refresh_token, expires_at)
        
        logger.info(f"User logged in: {request.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: TokenRefresh):
    """
    Refresh access token using refresh token
    """
    try:
        postgres = await get_postgres()
        
        # Decode refresh token
        payload = decode_token(request.refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        
        # Check if refresh token exists and is valid
        token_record = await postgres.fetchrow(
            """SELECT id, user_id, expires_at, revoked_at 
               FROM refresh_tokens 
               WHERE token = $1 AND user_id = $2""",
            request.refresh_token, user_id
        )
        
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        if token_record["revoked_at"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )
        
        if token_record["expires_at"] < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        
        # Get user info
        user = await postgres.fetchrow(
            "SELECT email, role FROM users WHERE id = $1",
            user_id
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new tokens
        access_token = create_access_token({
            "sub": user_id,
            "email": user["email"],
            "role": user["role"]
        })
        
        new_refresh_token = create_refresh_token({
            "sub": user_id
        })
        
        # Revoke old refresh token
        await postgres.execute(
            "UPDATE refresh_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = $1",
            token_record["id"]
        )
        
        # Store new refresh token
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        await postgres.execute("""
            INSERT INTO refresh_tokens (user_id, token, expires_at)
            VALUES ($1, $2, $3)
        """, user_id, new_refresh_token, expires_at)
        
        logger.info(f"Token refreshed for user: {user_id}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@app.post("/api/v1/auth/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Logout user by revoking refresh tokens
    """
    try:
        postgres = await get_postgres()
        redis = await get_redis()
        
        user_id = current_user["user_id"]
        
        # Revoke all refresh tokens for user
        await postgres.execute(
            "UPDATE refresh_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE user_id = $1",
            user_id
        )
        
        # Add current access token to blacklist
        # Note: In a real implementation, you'd need to pass the token
        # This is a simplified version
        
        logger.info(f"User logged out: {user_id}")
        
        return {
            "message": "Logout successful"
        }
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@app.get("/api/v1/auth/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current user information
    """
    try:
        postgres = await get_postgres()
        
        user = await postgres.fetchrow(
            """SELECT id, email, username, full_name, role, is_active, is_verified, created_at
               FROM users WHERE id = $1""",
            current_user["user_id"]
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "user_id": str(user["id"]),
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "is_active": user["is_active"],
            "is_verified": user["is_verified"],
            "created_at": user["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )


@app.post("/api/v1/auth/change-password")
async def change_password(
    request: PasswordChange,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Change user password
    """
    try:
        postgres = await get_postgres()
        
        user_id = current_user["user_id"]
        
        # Get current password hash
        user = await postgres.fetchrow(
            "SELECT password_hash FROM users WHERE id = $1",
            user_id
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify old password
        if not verify_password(request.old_password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = hash_password(request.new_password)
        
        # Update password
        await postgres.execute(
            "UPDATE users SET password_hash = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
            new_password_hash, user_id
        )
        
        # Revoke all refresh tokens
        await postgres.execute(
            "UPDATE refresh_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE user_id = $1",
            user_id
        )
        
        logger.info(f"Password changed for user: {user_id}")
        
        return {
            "message": "Password changed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password change failed: {str(e)}"
        )


@app.post("/api/v1/auth/verify-token", response_model=VerifyToken)
async def verify_token_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify if a token is valid
    """
    try:
        token = credentials.credentials
        
        try:
            payload = decode_token(token)
            
            return VerifyToken(
                valid=True,
                user_id=payload.get("sub"),
                expires_at=datetime.fromtimestamp(payload.get("exp"))
            )
        except HTTPException:
            return VerifyToken(valid=False)
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return VerifyToken(valid=False)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
