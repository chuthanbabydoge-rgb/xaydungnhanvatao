"""
User Service - User profiles and preferences management
Handles user profiles, preferences, settings, and character configurations
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid

from shared.database.postgres import get_postgres
from shared.database.mongodb import get_mongodb
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="User Service",
    description="User profiles and preferences management for AI Companion",
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


# Pydantic models
class UserProfile(BaseModel):
    """User profile model"""
    user_id: str = Field(..., description="User ID")
    username: Optional[str] = Field(default=None, description="Username")
    full_name: Optional[str] = Field(default=None, description="Full name")
    bio: Optional[str] = Field(default=None, description="User bio")
    avatar_url: Optional[str] = Field(default=None, description="Avatar image URL")
    date_of_birth: Optional[str] = Field(default=None, description="Date of birth")
    location: Optional[str] = Field(default=None, description="Location")
    language: Optional[str] = Field(default="en", description="Preferred language")
    timezone: Optional[str] = Field(default="UTC", description="Timezone")


class UserPreferences(BaseModel):
    """User preferences model"""
    user_id: str = Field(..., description="User ID")
    theme: Optional[str] = Field(default="light", description="UI theme: light, dark, auto")
    notifications_enabled: Optional[bool] = Field(default=True, description="Enable notifications")
    email_notifications: Optional[bool] = Field(default=True, description="Email notifications")
    voice_enabled: Optional[bool] = Field(default=True, description="Voice interaction enabled")
    ar_enabled: Optional[bool] = Field(default=True, description="AR features enabled")
    privacy_level: Optional[str] = Field(default="standard", description="Privacy level: basic, standard, strict")
    data_sharing: Optional[bool] = Field(default=False, description="Allow data sharing for improvements")


class CharacterPreferences(BaseModel):
    """Character preferences model"""
    user_id: str = Field(..., description="User ID")
    character_id: Optional[str] = Field(default=None, description="Selected character ID")
    character_name: Optional[str] = Field(default=None, description="Character name")
    personality_traits: Optional[Dict[str, float]] = Field(default=None, description="Personality trait preferences")
    voice_settings: Optional[Dict[str, Any]] = Field(default=None, description="Voice settings")
    appearance_settings: Optional[Dict[str, Any]] = Field(default=None, description="Appearance settings")
    behavior_settings: Optional[Dict[str, Any]] = Field(default=None, description="Behavior settings")


class UserSettings(BaseModel):
    """User settings model"""
    user_id: str = Field(..., description="User ID")
    settings: Dict[str, Any] = Field(..., description="User settings")


class UserStats(BaseModel):
    """User statistics model"""
    user_id: str = Field(..., description="User ID")
    total_conversations: int = Field(default=0, description="Total conversations")
    total_messages: int = Field(default=0, description="Total messages sent")
    total_interaction_time: int = Field(default=0, description="Total interaction time in seconds")
    last_active: Optional[datetime] = Field(default=None, description="Last active timestamp")
    streak_days: int = Field(default=0, description="Current streak days")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting User Service")
    
    try:
        # Create tables in PostgreSQL
        postgres = await get_postgres()
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id UUID PRIMARY KEY,
                username VARCHAR(100) UNIQUE,
                full_name VARCHAR(255),
                bio TEXT,
                avatar_url VARCHAR(500),
                date_of_birth DATE,
                location VARCHAR(255),
                language VARCHAR(10) DEFAULT 'en',
                timezone VARCHAR(50) DEFAULT 'UTC',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id UUID PRIMARY KEY,
                theme VARCHAR(20) DEFAULT 'light',
                notifications_enabled BOOLEAN DEFAULT true,
                email_notifications BOOLEAN DEFAULT true,
                voice_enabled BOOLEAN DEFAULT true,
                ar_enabled BOOLEAN DEFAULT true,
                privacy_level VARCHAR(20) DEFAULT 'standard',
                data_sharing BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id UUID PRIMARY KEY,
                total_conversations INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                total_interaction_time INTEGER DEFAULT 0,
                last_active TIMESTAMP,
                streak_days INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        logger.info("User Service started successfully")
    except Exception as e:
        logger.warning(f"User Service startup initialization skipped: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down User Service")


# API endpoints
@app.get("/api/v1/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    """
    Get user profile by ID
    """
    try:
        postgres = await get_postgres()
        
        profile = await postgres.fetchrow(
            "SELECT * FROM user_profiles WHERE user_id = $1",
            user_id
        )
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        return {
            "user_id": str(profile["user_id"]),
            "username": profile["username"],
            "full_name": profile["full_name"],
            "bio": profile["bio"],
            "avatar_url": profile["avatar_url"],
            "date_of_birth": profile["date_of_birth"],
            "location": profile["location"],
            "language": profile["language"],
            "timezone": profile["timezone"],
            "created_at": profile["created_at"],
            "updated_at": profile["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )


@app.put("/api/v1/users/{user_id}/profile")
async def update_user_profile(user_id: str, profile: UserProfile):
    """
    Update user profile
    """
    try:
        postgres = await get_postgres()
        
        # Check if profile exists
        existing = await postgres.fetchrow(
            "SELECT user_id FROM user_profiles WHERE user_id = $1",
            user_id
        )
        
        if existing:
            # Update existing profile
            await postgres.execute("""
                UPDATE user_profiles
                SET username = $2,
                    full_name = $3,
                    bio = $4,
                    avatar_url = $5,
                    date_of_birth = $6,
                    location = $7,
                    language = $8,
                    timezone = $9,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            """, user_id, profile.username, profile.full_name, profile.bio,
                profile.avatar_url, profile.date_of_birth, profile.location,
                profile.language, profile.timezone)
        else:
            # Create new profile
            await postgres.execute("""
                INSERT INTO user_profiles (user_id, username, full_name, bio, avatar_url, date_of_birth, location, language, timezone)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, user_id, profile.username, profile.full_name, profile.bio,
                profile.avatar_url, profile.date_of_birth, profile.location,
                profile.language, profile.timezone)
        
        logger.info(f"Updated profile for user: {user_id}")
        
        return {
            "user_id": user_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user profile: {str(e)}"
        )


@app.get("/api/v1/users/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    """
    Get user preferences
    """
    try:
        postgres = await get_postgres()
        
        preferences = await postgres.fetchrow(
            "SELECT * FROM user_preferences WHERE user_id = $1",
            user_id
        )
        
        if not preferences:
            # Return default preferences
            return {
                "user_id": user_id,
                "theme": "light",
                "notifications_enabled": True,
                "email_notifications": True,
                "voice_enabled": True,
                "ar_enabled": True,
                "privacy_level": "standard",
                "data_sharing": False
            }
        
        return {
            "user_id": str(preferences["user_id"]),
            "theme": preferences["theme"],
            "notifications_enabled": preferences["notifications_enabled"],
            "email_notifications": preferences["email_notifications"],
            "voice_enabled": preferences["voice_enabled"],
            "ar_enabled": preferences["ar_enabled"],
            "privacy_level": preferences["privacy_level"],
            "data_sharing": preferences["data_sharing"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user preferences: {str(e)}"
        )


@app.put("/api/v1/users/{user_id}/preferences")
async def update_user_preferences(user_id: str, preferences: UserPreferences):
    """
    Update user preferences
    """
    try:
        postgres = await get_postgres()
        
        # Check if preferences exist
        existing = await postgres.fetchrow(
            "SELECT user_id FROM user_preferences WHERE user_id = $1",
            user_id
        )
        
        if existing:
            # Update existing preferences
            await postgres.execute("""
                UPDATE user_preferences
                SET theme = $2,
                    notifications_enabled = $3,
                    email_notifications = $4,
                    voice_enabled = $5,
                    ar_enabled = $6,
                    privacy_level = $7,
                    data_sharing = $8,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
            """, user_id, preferences.theme, preferences.notifications_enabled,
                preferences.email_notifications, preferences.voice_enabled,
                preferences.ar_enabled, preferences.privacy_level,
                preferences.data_sharing)
        else:
            # Create new preferences
            await postgres.execute("""
                INSERT INTO user_preferences (user_id, theme, notifications_enabled, email_notifications, voice_enabled, ar_enabled, privacy_level, data_sharing)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, user_id, preferences.theme, preferences.notifications_enabled,
                preferences.email_notifications, preferences.voice_enabled,
                preferences.ar_enabled, preferences.privacy_level,
                preferences.data_sharing)
        
        logger.info(f"Updated preferences for user: {user_id}")
        
        return {
            "user_id": user_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user preferences: {str(e)}"
        )


@app.get("/api/v1/users/{user_id}/character")
async def get_character_preferences(user_id: str):
    """
    Get character preferences
    """
    try:
        mongodb = await get_mongodb()
        collection = mongodb["character_preferences"]
        
        character_prefs = await collection.find_one({"user_id": user_id})
        
        if not character_prefs:
            return {
                "user_id": user_id,
                "character_id": None,
                "character_name": None,
                "personality_traits": {},
                "voice_settings": {},
                "appearance_settings": {},
                "behavior_settings": {}
            }
        
        character_prefs.pop("_id", None)
        
        return character_prefs
        
    except Exception as e:
        logger.error(f"Failed to get character preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get character preferences: {str(e)}"
        )


@app.put("/api/v1/users/{user_id}/character")
async def update_character_preferences(user_id: str, preferences: CharacterPreferences):
    """
    Update character preferences
    """
    try:
        mongodb = await get_mongodb()
        collection = mongodb["character_preferences"]
        
        # Check if preferences exist
        existing = await collection.find_one({"user_id": user_id})
        
        preferences_dict = preferences.dict()
        preferences_dict["updated_at"] = datetime.utcnow().isoformat()
        
        if existing:
            await collection.update_one(
                {"user_id": user_id},
                {"$set": preferences_dict}
            )
        else:
            preferences_dict["created_at"] = datetime.utcnow().isoformat()
            await collection.insert_one(preferences_dict)
        
        logger.info(f"Updated character preferences for user: {user_id}")
        
        return {
            "user_id": user_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update character preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update character preferences: {str(e)}"
        )


@app.get("/api/v1/users/{user_id}/stats")
async def get_user_stats(user_id: str):
    """
    Get user statistics
    """
    try:
        postgres = await get_postgres()
        
        stats = await postgres.fetchrow(
            "SELECT * FROM user_stats WHERE user_id = $1",
            user_id
        )
        
        if not stats:
            # Return default stats
            return {
                "user_id": user_id,
                "total_conversations": 0,
                "total_messages": 0,
                "total_interaction_time": 0,
                "last_active": None,
                "streak_days": 0
            }
        
        return {
            "user_id": str(stats["user_id"]),
            "total_conversations": stats["total_conversations"],
            "total_messages": stats["total_messages"],
            "total_interaction_time": stats["total_interaction_time"],
            "last_active": stats["last_active"],
            "streak_days": stats["streak_days"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user stats: {str(e)}"
        )


@app.post("/api/v1/users/{user_id}/stats/increment")
async def increment_user_stats(user_id: str, increment_data: Dict[str, Any]):
    """
    Increment user statistics
    """
    try:
        postgres = await get_postgres()
        
        # Check if stats exist
        existing = await postgres.fetchrow(
            "SELECT user_id FROM user_stats WHERE user_id = $1",
            user_id
        )
        
        if existing:
            # Update existing stats
            update_fields = []
            update_values = []
            param_count = 2
            
            if "conversations" in increment_data:
                update_fields.append(f"total_conversations = total_conversations + ${param_count}")
                update_values.append(increment_data["conversations"])
                param_count += 1
            
            if "messages" in increment_data:
                update_fields.append(f"total_messages = total_messages + ${param_count}")
                update_values.append(increment_data["messages"])
                param_count += 1
            
            if "interaction_time" in increment_data:
                update_fields.append(f"total_interaction_time = total_interaction_time + ${param_count}")
                update_values.append(increment_data["interaction_time"])
                param_count += 1
            
            update_fields.append("last_active = CURRENT_TIMESTAMP")
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            if update_fields:
                query = f"""
                    UPDATE user_stats
                    SET {', '.join(update_fields)}
                    WHERE user_id = $1
                """
                await postgres.execute(query, user_id, *update_values)
        else:
            # Create new stats
            await postgres.execute("""
                INSERT INTO user_stats (user_id, total_conversations, total_messages, total_interaction_time, last_active)
                VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            """, user_id, 
                increment_data.get("conversations", 0),
                increment_data.get("messages", 0),
                increment_data.get("interaction_time", 0))
        
        logger.info(f"Incremented stats for user: {user_id}")
        
        return {
            "user_id": user_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to increment user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to increment user stats: {str(e)}"
        )


@app.delete("/api/v1/users/{user_id}")
async def delete_user(user_id: str):
    """
    Delete user account and all associated data
    """
    try:
        postgres = await get_postgres()
        mongodb = await get_mongodb()
        
        # Delete from PostgreSQL tables
        await postgres.execute("DELETE FROM user_profiles WHERE user_id = $1", user_id)
        await postgres.execute("DELETE FROM user_preferences WHERE user_id = $1", user_id)
        await postgres.execute("DELETE FROM user_stats WHERE user_id = $1", user_id)
        
        # Delete from MongoDB collections
        await mongodb["character_preferences"].delete_many({"user_id": user_id})
        await mongodb["user_settings"].delete_many({"user_id": user_id})
        
        logger.info(f"Deleted user: {user_id}")
        
        return {
            "user_id": user_id,
            "status": "deleted"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "user-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
