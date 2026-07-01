"""
Character Service - Character state management
Handles character configuration, state tracking, and lifecycle management
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid

from shared.database.postgres import get_postgres
from shared.database.mongodb import get_mongodb
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Character Service",
    description="Character state management for AI Companion",
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
class CharacterConfig(BaseModel):
    """Character configuration model"""
    character_id: str = Field(..., description="Character ID")
    name: str = Field(..., description="Character name")
    description: Optional[str] = Field(default=None, description="Character description")
    personality_traits: Dict[str, float] = Field(default_factory=dict, description="Personality traits (Big Five)")
    appearance_settings: Dict[str, Any] = Field(default_factory=dict, description="Appearance settings")
    voice_settings: Dict[str, Any] = Field(default_factory=dict, description="Voice settings")
    behavior_settings: Dict[str, Any] = Field(default_factory=dict, description="Behavior settings")
    capabilities: List[str] = Field(default_factory=list, description="Character capabilities")
    is_active: bool = Field(default=True, description="Whether character is active")


class CharacterState(BaseModel):
    """Character state model"""
    character_id: str = Field(..., description="Character ID")
    user_id: str = Field(..., description="User ID")
    current_emotion: str = Field(default="neutral", description="Current emotion")
    current_activity: str = Field(default="idle", description="Current activity")
    position: Optional[Dict[str, float]] = Field(default=None, description="Position in 3D space")
    rotation: Optional[Dict[str, float]] = Field(default=None, description="Rotation in 3D space")
    animation_state: str = Field(default="idle", description="Current animation state")
    health_status: float = Field(default=1.0, ge=0.0, le=1.0, description="Health status (0-1)")
    energy_level: float = Field(default=1.0, ge=0.0, le=1.0, description="Energy level (0-1)")
    mood: float = Field(default=0.5, ge=0.0, le=1.0, description="Current mood (0-1)")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class CharacterSnapshot(BaseModel):
    """Character snapshot for persistence"""
    character_id: str = Field(..., description="Character ID")
    user_id: str = Field(..., description="User ID")
    state: Dict[str, Any] = Field(..., description="Complete character state")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Snapshot timestamp")


class CharacterCreate(BaseModel):
    """Character creation model"""
    name: str = Field(..., description="Character name")
    description: Optional[str] = Field(default=None, description="Character description")
    personality_traits: Optional[Dict[str, float]] = Field(default=None, description="Personality traits")
    appearance_settings: Optional[Dict[str, Any]] = Field(default=None, description="Appearance settings")
    voice_settings: Optional[Dict[str, Any]] = Field(default=None, description="Voice settings")
    behavior_settings: Optional[Dict[str, Any]] = Field(default=None, description="Behavior settings")
    capabilities: Optional[List[str]] = Field(default=None, description="Character capabilities")


class CharacterUpdate(BaseModel):
    """Character update model"""
    name: Optional[str] = Field(default=None, description="Character name")
    description: Optional[str] = Field(default=None, description="Character description")
    personality_traits: Optional[Dict[str, float]] = Field(default=None, description="Personality traits")
    appearance_settings: Optional[Dict[str, Any]] = Field(default=None, description="Appearance settings")
    voice_settings: Optional[Dict[str, Any]] = Field(default=None, description="Voice settings")
    behavior_settings: Optional[Dict[str, Any]] = Field(default=None, description="Behavior settings")
    capabilities: Optional[List[str]] = Field(default=None, description="Character capabilities")
    is_active: Optional[bool] = Field(default=None, description="Active status")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Character Service")
    
    try:
        # Create tables in PostgreSQL
        postgres = await get_postgres()
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS character_configs (
                character_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                personality_traits JSONB DEFAULT '{}',
                appearance_settings JSONB DEFAULT '{}',
                voice_settings JSONB DEFAULT '{}',
                behavior_settings JSONB DEFAULT '{}',
                capabilities TEXT[] DEFAULT '{}',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS character_states (
                character_id UUID NOT NULL,
                user_id UUID NOT NULL,
                current_emotion VARCHAR(50) DEFAULT 'neutral',
                current_activity VARCHAR(50) DEFAULT 'idle',
                position JSONB,
                rotation JSONB,
                animation_state VARCHAR(50) DEFAULT 'idle',
                health_status FLOAT DEFAULT 1.0 CHECK (health_status >= 0 AND health_status <= 1),
                energy_level FLOAT DEFAULT 1.0 CHECK (energy_level >= 0 AND energy_level <= 1),
                mood FLOAT DEFAULT 0.5 CHECK (mood >= 0 AND mood <= 1),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, user_id)
            )
        """)
        
        # Create indexes
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_character_configs_name ON character_configs(name)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_character_configs_active ON character_configs(is_active)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_character_states_user_id ON character_states(user_id)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_character_states_updated ON character_states(last_updated)")
        
        logger.info("Character Service started successfully")
    except Exception as e:
        logger.warning(f"Character Service startup initialization skipped: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Character Service")


# API endpoints
@app.post("/api/v1/characters", status_code=status.HTTP_201_CREATED)
async def create_character(character: CharacterCreate):
    """
    Create a new character configuration
    """
    try:
        postgres = await get_postgres()
        
        character_id = await postgres.fetchval("""
            INSERT INTO character_configs (
                name, description, personality_traits, appearance_settings,
                voice_settings, behavior_settings, capabilities
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING character_id
        """, character.name, character.description,
            character.personality_traits or {},
            character.appearance_settings or {},
            character.voice_settings or {},
            character.behavior_settings or {},
            character.capabilities or [])
        
        logger.info(f"Created character {character_id}")
        
        return {
            "character_id": str(character_id),
            "name": character.name,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create character: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create character: {str(e)}"
        )


@app.get("/api/v1/characters/{character_id}")
async def get_character(character_id: str):
    """
    Get character configuration by ID
    """
    try:
        postgres = await get_postgres()
        
        character = await postgres.fetchrow(
            "SELECT * FROM character_configs WHERE character_id = $1",
            character_id
        )
        
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found"
            )
        
        return {
            "character_id": str(character["character_id"]),
            "name": character["name"],
            "description": character["description"],
            "personality_traits": character["personality_traits"],
            "appearance_settings": character["appearance_settings"],
            "voice_settings": character["voice_settings"],
            "behavior_settings": character["behavior_settings"],
            "capabilities": character["capabilities"],
            "is_active": character["is_active"],
            "created_at": character["created_at"],
            "updated_at": character["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get character: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get character: {str(e)}"
        )


@app.get("/api/v1/characters")
async def list_characters(active_only: bool = True, limit: int = 50, offset: int = 0):
    """
    List all characters
    """
    try:
        postgres = await get_postgres()
        
        query = "SELECT * FROM character_configs"
        params = []
        
        if active_only:
            query += " WHERE is_active = true"
        
        query += " ORDER BY created_at DESC LIMIT $1 OFFSET $2"
        params.extend([limit, offset])
        
        characters = await postgres.fetch(query, *params)
        
        results = []
        for char in characters:
            results.append({
                "character_id": str(char["character_id"]),
                "name": char["name"],
                "description": char["description"],
                "capabilities": char["capabilities"],
                "is_active": char["is_active"],
                "created_at": char["created_at"]
            })
        
        return {
            "characters": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to list characters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list characters: {str(e)}"
        )


@app.put("/api/v1/characters/{character_id}")
async def update_character(character_id: str, update: CharacterUpdate):
    """
    Update character configuration
    """
    try:
        postgres = await get_postgres()
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        param_count = 1
        
        if update.name is not None:
            update_fields.append(f"name = ${param_count}")
            update_values.append(update.name)
            param_count += 1
        
        if update.description is not None:
            update_fields.append(f"description = ${param_count}")
            update_values.append(update.description)
            param_count += 1
        
        if update.personality_traits is not None:
            update_fields.append(f"personality_traits = ${param_count}")
            update_values.append(update.personality_traits)
            param_count += 1
        
        if update.appearance_settings is not None:
            update_fields.append(f"appearance_settings = ${param_count}")
            update_values.append(update.appearance_settings)
            param_count += 1
        
        if update.voice_settings is not None:
            update_fields.append(f"voice_settings = ${param_count}")
            update_values.append(update.voice_settings)
            param_count += 1
        
        if update.behavior_settings is not None:
            update_fields.append(f"behavior_settings = ${param_count}")
            update_values.append(update.behavior_settings)
            param_count += 1
        
        if update.capabilities is not None:
            update_fields.append(f"capabilities = ${param_count}")
            update_values.append(update.capabilities)
            param_count += 1
        
        if update.is_active is not None:
            update_fields.append(f"is_active = ${param_count}")
            update_values.append(update.is_active)
            param_count += 1
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            query = f"""
                UPDATE character_configs
                SET {', '.join(update_fields)}
                WHERE character_id = ${param_count}
            """
            update_values.append(character_id)
            
            result = await postgres.execute(query, *update_values)
            
            if result == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Character not found"
                )
        
        logger.info(f"Updated character {character_id}")
        
        return {
            "character_id": character_id,
            "status": "updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update character: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update character: {str(e)}"
        )


@app.delete("/api/v1/characters/{character_id}")
async def delete_character(character_id: str):
    """
    Delete a character
    """
    try:
        postgres = await get_postgres()
        
        result = await postgres.execute(
            "DELETE FROM character_configs WHERE character_id = $1",
            character_id
        )
        
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found"
            )
        
        # Delete associated states
        await postgres.execute(
            "DELETE FROM character_states WHERE character_id = $1",
            character_id
        )
        
        logger.info(f"Deleted character {character_id}")
        
        return {
            "character_id": character_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete character: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete character: {str(e)}"
        )


@app.post("/api/v1/characters/{character_id}/state")
async def set_character_state(character_id: str, state: CharacterState):
    """
    Set or update character state for a user
    """
    try:
        postgres = await get_postgres()
        
        # Check if character exists
        character = await postgres.fetchrow(
            "SELECT character_id FROM character_configs WHERE character_id = $1",
            character_id
        )
        
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found"
            )
        
        # Upsert character state
        await postgres.execute("""
            INSERT INTO character_states (
                character_id, user_id, current_emotion, current_activity,
                position, rotation, animation_state, health_status,
                energy_level, mood, last_updated
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP)
            ON CONFLICT (character_id, user_id)
            DO UPDATE SET
                current_emotion = EXCLUDED.current_emotion,
                current_activity = EXCLUDED.current_activity,
                position = EXCLUDED.position,
                rotation = EXCLUDED.rotation,
                animation_state = EXCLUDED.animation_state,
                health_status = EXCLUDED.health_status,
                energy_level = EXCLUDED.energy_level,
                mood = EXCLUDED.mood,
                last_updated = CURRENT_TIMESTAMP
        """, character_id, state.user_id, state.current_emotion,
            state.current_activity, state.position, state.rotation,
            state.animation_state, state.health_status,
            state.energy_level, state.mood)
        
        logger.info(f"Set state for character {character_id}, user {state.user_id}")
        
        return {
            "character_id": character_id,
            "user_id": state.user_id,
            "status": "updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set character state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set character state: {str(e)}"
        )


@app.get("/api/v1/characters/{character_id}/state/{user_id}")
async def get_character_state(character_id: str, user_id: str):
    """
    Get character state for a user
    """
    try:
        postgres = await get_postgres()
        
        state = await postgres.fetchrow(
            "SELECT * FROM character_states WHERE character_id = $1 AND user_id = $2",
            character_id, user_id
        )
        
        if not state:
            # Return default state
            return {
                "character_id": character_id,
                "user_id": user_id,
                "current_emotion": "neutral",
                "current_activity": "idle",
                "animation_state": "idle",
                "health_status": 1.0,
                "energy_level": 1.0,
                "mood": 0.5,
                "last_updated": None
            }
        
        return {
            "character_id": str(state["character_id"]),
            "user_id": str(state["user_id"]),
            "current_emotion": state["current_emotion"],
            "current_activity": state["current_activity"],
            "position": state["position"],
            "rotation": state["rotation"],
            "animation_state": state["animation_state"],
            "health_status": state["health_status"],
            "energy_level": state["energy_level"],
            "mood": state["mood"],
            "last_updated": state["last_updated"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get character state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get character state: {str(e)}"
        )


@app.post("/api/v1/characters/{character_id}/snapshot")
async def create_character_snapshot(character_id: str, snapshot: CharacterSnapshot):
    """
    Create a character state snapshot for persistence
    """
    try:
        mongodb = await get_mongodb()
        collection = mongodb["character_snapshots"]
        
        snapshot_dict = snapshot.dict()
        snapshot_dict["created_at"] = datetime.utcnow().isoformat()
        
        await collection.insert_one(snapshot_dict)
        
        logger.info(f"Created snapshot for character {character_id}")
        
        return {
            "character_id": character_id,
            "user_id": snapshot.user_id,
            "status": "snapshot_created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create snapshot: {str(e)}"
        )


@app.get("/api/v1/characters/{character_id}/snapshots/{user_id}")
async def get_character_snapshots(character_id: str, user_id: str, limit: int = 10):
    """
    Get character state snapshots for a user
    """
    try:
        mongodb = await get_mongodb()
        collection = mongodb["character_snapshots"]
        
        snapshots = await collection.find(
            {"character_id": character_id, "user_id": user_id}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        results = []
        for snapshot in snapshots:
            snapshot.pop("_id", None)
            results.append(snapshot)
        
        return {
            "character_id": character_id,
            "user_id": user_id,
            "snapshots": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to get snapshots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get snapshots: {str(e)}"
        )


@app.delete("/api/v1/characters/{character_id}/state/{user_id}")
async def delete_character_state(character_id: str, user_id: str):
    """
    Delete character state for a user
    """
    try:
        postgres = await get_postgres()
        
        result = await postgres.execute(
            "DELETE FROM character_states WHERE character_id = $1 AND user_id = $2",
            character_id, user_id
        )
        
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character state not found"
            )
        
        logger.info(f"Deleted state for character {character_id}, user {user_id}")
        
        return {
            "character_id": character_id,
            "user_id": user_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete character state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete character state: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "character-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8016)
