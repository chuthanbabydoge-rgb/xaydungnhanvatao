"""
Animation Service - Animation data management
Handles animation clips, states, transitions, and animation graph management
"""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
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
    title="Animation Service",
    description="Animation data management for AI Companion",
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
class AnimationClip(BaseModel):
    """Animation clip model"""
    clip_id: str = Field(..., description="Animation clip ID")
    name: str = Field(..., description="Animation name")
    description: Optional[str] = Field(default=None, description="Animation description")
    category: str = Field(default="movement", description="Animation category: movement, idle, gesture, emotion, task")
    duration: float = Field(..., gt=0, description="Animation duration in seconds")
    loop: bool = Field(default=False, description="Whether animation loops")
    root_motion: bool = Field(default=False, description="Whether animation has root motion")
    blend_in_time: float = Field(default=0.1, ge=0.0, description="Blend in time")
    blend_out_time: float = Field(default=0.1, ge=0.0, description="Blend out time")
    tags: List[str] = Field(default_factory=list, description="Animation tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    asset_url: Optional[str] = Field(default=None, description="Animation asset URL")


class AnimationState(BaseModel):
    """Animation state model"""
    state_id: str = Field(..., description="State ID")
    name: str = Field(..., description="State name")
    default_clip: str = Field(..., description="Default animation clip ID")
    clips: List[str] = Field(default_factory=list, description="Available animation clips")
    transitions: Dict[str, str] = Field(default_factory=dict, description="Transitions to other states")
    exit_time: float = Field(default=0.0, ge=0.0, description="Exit time for transitions")
    can_interrupt: bool = Field(default=True, description="Whether state can be interrupted")
    priority: int = Field(default=0, description="State priority (higher = more important)")


class AnimationGraph(BaseModel):
    """Animation graph model"""
    graph_id: str = Field(..., description="Graph ID")
    character_id: str = Field(..., description="Character ID")
    name: str = Field(..., description="Graph name")
    states: List[str] = Field(default_factory=list, description="State IDs in graph")
    default_state: str = Field(..., description="Default state ID")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Graph parameters")
    is_active: bool = Field(default=True, description="Whether graph is active")


class AnimationRequest(BaseModel):
    """Animation playback request"""
    character_id: str = Field(..., description="Character ID")
    user_id: str = Field(..., description="User ID")
    clip_id: str = Field(..., description="Animation clip ID")
    loop: bool = Field(default=False, description="Whether to loop")
    speed: float = Field(default=1.0, gt=0.0, description="Playback speed")
    transition_duration: float = Field(default=0.2, ge=0.0, description="Transition duration")


class BlendShape(BaseModel):
    """Blend shape model"""
    shape_id: str = Field(..., description="Shape ID")
    name: str = Field(..., description="Shape name")
    category: str = Field(default="facial", description="Shape category: facial, body")
    index: int = Field(..., description="Shape index")
    default_value: float = Field(default=0.0, ge=0.0, le=1.0, description="Default value")
    range: tuple = Field(default=(0.0, 1.0), description="Value range")


class AnimationCreate(BaseModel):
    """Animation creation model"""
    name: str = Field(..., description="Animation name")
    description: Optional[str] = Field(default=None, description="Animation description")
    category: str = Field(default="movement", description="Animation category")
    duration: float = Field(..., gt=0, description="Animation duration")
    loop: bool = Field(default=False, description="Whether animation loops")
    root_motion: bool = Field(default=False, description="Whether animation has root motion")
    blend_in_time: float = Field(default=0.1, ge=0.0, description="Blend in time")
    blend_out_time: float = Field(default=0.1, ge=0.0, description="Blend out time")
    tags: Optional[List[str]] = Field(default=None, description="Animation tags")
    asset_url: Optional[str] = Field(default=None, description="Animation asset URL")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Animation Service")
    
    # Create tables in PostgreSQL
    postgres = await get_postgres()
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS animation_clips (
            clip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            category VARCHAR(50) DEFAULT 'movement',
            duration FLOAT NOT NULL CHECK (duration > 0),
            loop BOOLEAN DEFAULT false,
            root_motion BOOLEAN DEFAULT false,
            blend_in_time FLOAT DEFAULT 0.1 CHECK (blend_in_time >= 0),
            blend_out_time FLOAT DEFAULT 0.1 CHECK (blend_out_time >= 0),
            tags TEXT[] DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            asset_url VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS animation_states (
            state_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            default_clip UUID NOT NULL REFERENCES animation_clips(clip_id),
            clips UUID[] DEFAULT '{}',
            transitions JSONB DEFAULT '{}',
            exit_time FLOAT DEFAULT 0.0 CHECK (exit_time >= 0),
            can_interrupt BOOLEAN DEFAULT true,
            priority INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS animation_graphs (
            graph_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            character_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            states UUID[] DEFAULT '{}',
            default_state UUID NOT NULL REFERENCES animation_states(state_id),
            parameters JSONB DEFAULT '{}',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS blend_shapes (
            shape_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            category VARCHAR(50) DEFAULT 'facial',
            index INTEGER NOT NULL,
            default_value FLOAT DEFAULT 0.0 CHECK (default_value >= 0 AND default_value <= 1),
            min_value FLOAT DEFAULT 0.0 CHECK (min_value >= 0 AND min_value <= 1),
            max_value FLOAT DEFAULT 1.0 CHECK (max_value >= 0 AND max_value <= 1),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_animation_clips_category ON animation_clips(category)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_animation_clips_tags ON animation_clips USING GIN(tags)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_animation_graphs_character ON animation_graphs(character_id)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_animation_graphs_active ON animation_graphs(is_active)")
    
    logger.info("Animation Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Animation Service")


# API endpoints
@app.post("/api/v1/animations/clips", status_code=status.HTTP_201_CREATED)
async def create_animation_clip(animation: AnimationCreate):
    """
    Create a new animation clip
    """
    try:
        postgres = await get_postgres()
        
        clip_id = await postgres.fetchval("""
            INSERT INTO animation_clips (
                name, description, category, duration, loop, root_motion,
                blend_in_time, blend_out_time, tags, asset_url
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING clip_id
        """, animation.name, animation.description, animation.category,
            animation.duration, animation.loop, animation.root_motion,
            animation.blend_in_time, animation.blend_out_time,
            animation.tags or [], animation.asset_url)
        
        logger.info(f"Created animation clip {clip_id}")
        
        return {
            "clip_id": str(clip_id),
            "name": animation.name,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create animation clip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create animation clip: {str(e)}"
        )


@app.get("/api/v1/animations/clips/{clip_id}")
async def get_animation_clip(clip_id: str):
    """
    Get animation clip by ID
    """
    try:
        postgres = await get_postgres()
        
        clip = await postgres.fetchrow(
            "SELECT * FROM animation_clips WHERE clip_id = $1",
            clip_id
        )
        
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation clip not found"
            )
        
        return {
            "clip_id": str(clip["clip_id"]),
            "name": clip["name"],
            "description": clip["description"],
            "category": clip["category"],
            "duration": clip["duration"],
            "loop": clip["loop"],
            "root_motion": clip["root_motion"],
            "blend_in_time": clip["blend_in_time"],
            "blend_out_time": clip["blend_out_time"],
            "tags": clip["tags"],
            "metadata": clip["metadata"],
            "asset_url": clip["asset_url"],
            "created_at": clip["created_at"],
            "updated_at": clip["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get animation clip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get animation clip: {str(e)}"
        )


@app.get("/api/v1/animations/clips")
async def list_animation_clips(
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List animation clips with filtering
    """
    try:
        postgres = await get_postgres()
        
        query = "SELECT * FROM animation_clips WHERE 1=1"
        params = []
        param_count = 1
        
        if category:
            query += f" AND category = ${param_count}"
            params.append(category)
            param_count += 1
        
        if tags:
            for tag in tags:
                query += f" AND ${param_count} = ANY(tags)"
                params.append(tag)
                param_count += 1
        
        query += " ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])
        
        clips = await postgres.fetch(query, *params)
        
        results = []
        for clip in clips:
            results.append({
                "clip_id": str(clip["clip_id"]),
                "name": clip["name"],
                "category": clip["category"],
                "duration": clip["duration"],
                "tags": clip["tags"],
                "asset_url": clip["asset_url"]
            })
        
        return {
            "clips": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to list animation clips: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list animation clips: {str(e)}"
        )


@app.post("/api/v1/animations/states", status_code=status.HTTP_201_CREATED)
async def create_animation_state(state: AnimationState):
    """
    Create a new animation state
    """
    try:
        postgres = await get_postgres()
        
        state_id = await postgres.fetchval("""
            INSERT INTO animation_states (
                name, default_clip, clips, transitions, exit_time, can_interrupt, priority
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING state_id
        """, state.name, state.default_clip, state.clips,
            state.transitions, state.exit_time, state.can_interrupt, state.priority)
        
        logger.info(f"Created animation state {state_id}")
        
        return {
            "state_id": str(state_id),
            "name": state.name,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create animation state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create animation state: {str(e)}"
        )


@app.post("/api/v1/animations/graphs", status_code=status.HTTP_201_CREATED)
async def create_animation_graph(graph: AnimationGraph):
    """
    Create a new animation graph for a character
    """
    try:
        postgres = await get_postgres()
        
        graph_id = await postgres.fetchval("""
            INSERT INTO animation_graphs (
                character_id, name, states, default_state, parameters, is_active
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING graph_id
        """, graph.character_id, graph.name, graph.states,
            graph.default_state, graph.parameters, graph.is_active)
        
        logger.info(f"Created animation graph {graph_id}")
        
        return {
            "graph_id": str(graph_id),
            "character_id": graph.character_id,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create animation graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create animation graph: {str(e)}"
        )


@app.get("/api/v1/animations/graphs/character/{character_id}")
async def get_character_animation_graph(character_id: str):
    """
    Get animation graph for a character
    """
    try:
        postgres = await get_postgres()
        
        graph = await postgres.fetchrow(
            "SELECT * FROM animation_graphs WHERE character_id = $1 AND is_active = true",
            character_id
        )
        
        if not graph:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active animation graph not found for character"
            )
        
        return {
            "graph_id": str(graph["graph_id"]),
            "character_id": str(graph["character_id"]),
            "name": graph["name"],
            "states": graph["states"],
            "default_state": str(graph["default_state"]),
            "parameters": graph["parameters"],
            "is_active": graph["is_active"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get animation graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get animation graph: {str(e)}"
        )


@app.post("/api/v1/animations/play")
async def play_animation(request: AnimationRequest):
    """
    Request animation playback for a character
    """
    try:
        # Get animation clip
        postgres = await get_postgres()
        
        clip = await postgres.fetchrow(
            "SELECT * FROM animation_clips WHERE clip_id = $1",
            request.clip_id
        )
        
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation clip not found"
            )
        
        # Log animation request
        mongodb = await get_mongodb()
        collection = mongodb["animation_requests"]
        
        await collection.insert_one({
            "character_id": request.character_id,
            "user_id": request.user_id,
            "clip_id": request.clip_id,
            "loop": request.loop,
            "speed": request.speed,
            "transition_duration": request.transition_duration,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Animation play request: {request.clip_id} for character {request.character_id}")
        
        return {
            "status": "queued",
            "clip_id": request.clip_id,
            "character_id": request.character_id,
            "estimated_duration": clip["duration"] / request.speed if request.speed > 0 else clip["duration"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to play animation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to play animation: {str(e)}"
        )


@app.post("/api/v1/animations/blend-shapes", status_code=status.HTTP_201_CREATED)
async def create_blend_shape(shape: BlendShape):
    """
    Create a new blend shape
    """
    try:
        postgres = await get_postgres()
        
        shape_id = await postgres.fetchval("""
            INSERT INTO blend_shapes (name, category, index, default_value, min_value, max_value)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING shape_id
        """, shape.name, shape.category, shape.index,
            shape.default_value, shape.range[0], shape.range[1])
        
        logger.info(f"Created blend shape {shape_id}")
        
        return {
            "shape_id": str(shape_id),
            "name": shape.name,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create blend shape: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create blend shape: {str(e)}"
        )


@app.get("/api/v1/animations/blend-shapes")
async def list_blend_shapes(category: Optional[str] = None):
    """
    List blend shapes
    """
    try:
        postgres = await get_postgres()
        
        query = "SELECT * FROM blend_shapes"
        params = []
        
        if category:
            query += " WHERE category = $1"
            params.append(category)
        
        shapes = await postgres.fetch(query, *params)
        
        results = []
        for shape in shapes:
            results.append({
                "shape_id": str(shape["shape_id"]),
                "name": shape["name"],
                "category": shape["category"],
                "index": shape["index"],
                "default_value": shape["default_value"],
                "range": (shape["min_value"], shape["max_value"])
            })
        
        return {
            "blend_shapes": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to list blend shapes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list blend shapes: {str(e)}"
        )


@app.delete("/api/v1/animations/clips/{clip_id}")
async def delete_animation_clip(clip_id: str):
    """
    Delete an animation clip
    """
    try:
        postgres = await get_postgres()
        
        result = await postgres.execute(
            "DELETE FROM animation_clips WHERE clip_id = $1",
            clip_id
        )
        
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation clip not found"
            )
        
        logger.info(f"Deleted animation clip {clip_id}")
        
        return {
            "clip_id": clip_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete animation clip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete animation clip: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "animation-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)
