"""
Custom Exceptions
Auth Service
"""

from typing import Optional, Any


class AuthException(Exception):
    """Base authentication exception."""
    
    def __init__(self, message: str, detail: Optional[Any] = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class UserNotFoundException(AuthException):
    """User not found exception."""
    pass


class InvalidCredentialsException(AuthException):
    """Invalid credentials exception."""
    pass


class TokenExpiredException(AuthException):
    """Token expired exception."""
    pass


class InvalidTokenException(AuthException):
    """Invalid token exception."""
    pass


class UserAlreadyExistsException(AuthException):
    """User already exists exception."""
    pass


class EmailAlreadyExistsException(AuthException):
    """Email already exists exception."""
    pass


class PermissionDeniedException(AuthException):
    """Permission denied exception."""
    pass
