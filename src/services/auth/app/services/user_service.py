"""
User Service
User business logic
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.models.user import User
from app.schemas.user import UserUpdate, UserResponse
from app.core.exceptions import UserNotFoundException, EmailAlreadyExistsException


class UserService:
    """User service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: str) -> UserResponse:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")

        return UserResponse.model_validate(user)

    async def get_user_by_username(self, username: str) -> UserResponse:
        """Get user by username."""
        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"User with username {username} not found")

        return UserResponse.model_validate(user)

    async def get_user_by_email(self, email: str) -> UserResponse:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"User with email {email} not found")

        return UserResponse.model_validate(user)

    async def update_user(self, user_id: str, user_update: UserUpdate) -> UserResponse:
        """Update user."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")

        # Update user fields
        update_data = user_update.model_dump(exclude_unset=True)

        # Check if email is being updated and if it's already taken
        if "email" in update_data and update_data["email"] != user.email:
            email_check = await self.db.execute(
                select(User).where(User.email == update_data["email"])
            )
            if email_check.scalar_one_or_none():
                raise EmailAlreadyExistsException("Email already taken")

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)

        return UserResponse.model_validate(user)

    async def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")

        await self.db.delete(user)
        await self.db.commit()

        return True
