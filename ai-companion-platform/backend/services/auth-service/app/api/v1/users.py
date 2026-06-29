"""
Users API Routes
Auth Service
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.dependencies import get_db
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import UserService
from app.core.exceptions import UserNotFoundException

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile."""
    # TODO: Implement authentication dependency
    # For now, return a placeholder
    user_service = UserService(db)
    return await user_service.get_user_by_id("placeholder-id")


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    # TODO: Implement authentication dependency
    user_service = UserService(db)
    return await user_service.update_user("placeholder-id", user_update)


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
