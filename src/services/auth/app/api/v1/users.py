"""
Users API Routes
Auth Service
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.dependencies import get_db, get_current_user
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import UserService
from app.core.exceptions import UserNotFoundException
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile."""
    user_service = UserService(db)
    return await user_service.get_user_by_id(str(current_user.id))


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    user_service = UserService(db)
    return await user_service.update_user(str(current_user.id), user_update)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID."""
    user_service = UserService(db)
    
    try:
        user = await user_service.get_user_by_id(user_id)
        return user
    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
