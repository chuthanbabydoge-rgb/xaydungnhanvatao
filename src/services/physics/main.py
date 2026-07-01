"""
Physics Service - Physics simulation
Handles physics calculations, collision detection, and physics state management
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
import math

from shared.database.postgres import get_postgres
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Physics Service",
    description="Physics simulation for AI Companion",
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
class PhysicsBody(BaseModel):
    """Physics body model"""
    body_id: str = Field(..., description="Body ID")
    object_id: str = Field(..., description="Associated object ID")
    body_type: str = Field(default="dynamic", description="Body type: static, dynamic, kinematic")
    mass: float = Field(default=1.0, gt=0.0, description="Body mass in kg")
    position: Dict[str, float] = Field(..., description="Position (x, y, z)")
    rotation: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0, "z": 0}, description="Rotation (x, y, z)")
    velocity: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0, "z": 0}, description="Velocity (x, y, z)")
    angular_velocity: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0, "z": 0}, description="Angular velocity")
    collision_shape: str = Field(default="box", description="Collision shape: box, sphere, capsule, mesh")
    collision_params: Dict[str, float] = Field(default_factory=dict, description="Collision shape parameters")
    friction: float = Field(default=0.5, ge=0.0, le=1.0, description="Friction coefficient")
    restitution: float = Field(default=0.0, ge=0.0, le=1.0, description="Restitution (bounciness)")
    is_active: bool = Field(default=True, description="Whether body is active")


class PhysicsState(BaseModel):
    """Physics state model"""
    body_id: str = Field(..., description="Body ID")
    position: Dict[str, float] = Field(..., description="Current position")
    rotation: Dict[str, float] = Field(..., description="Current rotation")
    velocity: Dict[str, float] = Field(..., description="Current velocity")
    angular_velocity: Dict[str, float] = Field(..., description="Current angular velocity")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="State timestamp")


class ForceApplication(BaseModel):
    """Force application model"""
    body_id: str = Field(..., description="Body ID")
    force: Dict[str, float] = Field(..., description="Force vector (x, y, z)")
    position: Optional[Dict[str, float]] = Field(default=None, description="Application point")
    duration: Optional[float] = Field(default=None, description="Duration in seconds (None for impulse)")


class CollisionEvent(BaseModel):
    """Collision event model"""
    event_id: str = Field(..., description="Event ID")
    body_a: str = Field(..., description="First body ID")
    body_b: str = Field(..., description="Second body ID")
    contact_point: Dict[str, float] = Field(..., description="Contact point (x, y, z)")
    normal: Dict[str, float] = Field(..., description="Collision normal")
    impulse: float = Field(..., description="Collision impulse magnitude")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class RaycastQuery(BaseModel):
    """Raycast query model"""
    origin: Dict[str, float] = Field(..., description="Ray origin (x, y, z)")
    direction: Dict[str, float] = Field(..., description="Ray direction (normalized)")
    max_distance: float = Field(default=100.0, gt=0.0, description="Maximum ray distance")
    collision_mask: Optional[int] = Field(default=None, description="Collision mask")


class RaycastResult(BaseModel):
    """Raycast result model"""
    hit: bool = Field(..., description="Whether ray hit anything")
    body_id: Optional[str] = Field(default=None, description="Hit body ID")
    hit_point: Optional[Dict[str, float]] = Field(default=None, description="Hit point")
    distance: float = Field(..., description="Distance to hit")
    normal: Optional[Dict[str, float]] = Field(default=None, description="Hit normal")


class PhysicsSimulation(BaseModel):
    """Physics simulation model"""
    simulation_id: str = Field(..., description="Simulation ID")
    environment_id: str = Field(..., description="Environment ID")
    gravity: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": -9.81, "z": 0}, description="Gravity vector")
    time_step: float = Field(default=0.016, gt=0.0, description="Time step in seconds")
    sub_steps: int = Field(default=1, ge=1, description="Sub-steps for stability")
    is_running: bool = Field(default=False, description="Whether simulation is running")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Physics Service")
    
    try:
        # Create tables in PostgreSQL
        postgres = await get_postgres()
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS physics_bodies (
                body_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                object_id UUID NOT NULL,
                body_type VARCHAR(20) DEFAULT 'dynamic',
                mass FLOAT DEFAULT 1.0 CHECK (mass > 0),
                position JSONB NOT NULL,
                rotation JSONB DEFAULT '{"x": 0, "y": 0, "z": 0}',
                velocity JSONB DEFAULT '{"x": 0, "y": 0, "z": 0}',
                angular_velocity JSONB DEFAULT '{"x": 0, "y": 0, "z": 0}',
                collision_shape VARCHAR(20) DEFAULT 'box',
                collision_params JSONB DEFAULT '{}',
                friction FLOAT DEFAULT 0.5 CHECK (friction >= 0 AND friction <= 1),
                restitution FLOAT DEFAULT 0.0 CHECK (restitution >= 0 AND restitution <= 1),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS physics_simulations (
                simulation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                environment_id UUID NOT NULL,
                gravity JSONB DEFAULT '{"x": 0, "y": -9.81, "z": 0}',
                time_step FLOAT DEFAULT 0.016 CHECK (time_step > 0),
                sub_steps INTEGER DEFAULT 1 CHECK (sub_steps >= 1),
                is_running BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS collision_events (
                event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                body_a UUID NOT NULL,
                body_b UUID NOT NULL,
                contact_point JSONB NOT NULL,
                normal JSONB NOT NULL,
                impulse FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_physics_bodies_object ON physics_bodies(object_id)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_physics_bodies_type ON physics_bodies(body_type)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_physics_bodies_active ON physics_bodies(is_active)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_physics_simulations_env ON physics_simulations(environment_id)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_collision_events_bodies ON collision_events(body_a, body_b)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_collision_events_timestamp ON collision_events(timestamp)")
        
        logger.info("Physics Service started successfully")
    except Exception as e:
        logger.warning(f"Physics Service startup initialization skipped: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Physics Service")


# Helper functions
def vector_add(v1: Dict[str, float], v2: Dict[str, float]) -> Dict[str, float]:
    """Add two vectors"""
    return {
        "x": v1["x"] + v2["x"],
        "y": v1["y"] + v2["y"],
        "z": v1["z"] + v2["z"]
    }


def vector_subtract(v1: Dict[str, float], v2: Dict[str, float]) -> Dict[str, float]:
    """Subtract two vectors"""
    return {
        "x": v1["x"] - v2["x"],
        "y": v1["y"] - v2["y"],
        "z": v1["z"] - v2["z"]
    }


def vector_multiply(v: Dict[str, float], scalar: float) -> Dict[str, float]:
    """Multiply vector by scalar"""
    return {
        "x": v["x"] * scalar,
        "y": v["y"] * scalar,
        "z": v["z"] * scalar
    }


def vector_dot(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    """Dot product of two vectors"""
    return v1["x"] * v2["x"] + v1["y"] * v2["y"] + v1["z"] * v2["z"]


def vector_length(v: Dict[str, float]) -> float:
    """Length of vector"""
    return math.sqrt(v["x"]**2 + v["y"]**2 + v["z"]**2)


def vector_normalize(v: Dict[str, float]) -> Dict[str, float]:
    """Normalize vector"""
    length = vector_length(v)
    if length == 0:
        return {"x": 0, "y": 0, "z": 0}
    return vector_multiply(v, 1.0 / length)


# API endpoints
@app.post("/api/v1/physics/bodies", status_code=status.HTTP_201_CREATED)
async def create_physics_body(body: PhysicsBody):
    """
    Create a new physics body
    """
    try:
        postgres = await get_postgres()
        
        body_id = await postgres.fetchval("""
            INSERT INTO physics_bodies (
                object_id, body_type, mass, position, rotation, velocity,
                angular_velocity, collision_shape, collision_params, friction, restitution
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING body_id
        """, body.object_id, body.body_type, body.mass, body.position,
            body.rotation, body.velocity, body.angular_velocity,
            body.collision_shape, body.collision_params,
            body.friction, body.restitution)
        
        logger.info(f"Created physics body {body_id}")
        
        return {
            "body_id": str(body_id),
            "object_id": body.object_id,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create physics body: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create physics body: {str(e)}"
        )


@app.get("/api/v1/physics/bodies/{body_id}")
async def get_physics_body(body_id: str):
    """
    Get physics body by ID
    """
    try:
        postgres = await get_postgres()
        
        body = await postgres.fetchrow(
            "SELECT * FROM physics_bodies WHERE body_id = $1",
            body_id
        )
        
        if not body:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physics body not found"
            )
        
        return {
            "body_id": str(body["body_id"]),
            "object_id": str(body["object_id"]),
            "body_type": body["body_type"],
            "mass": body["mass"],
            "position": body["position"],
            "rotation": body["rotation"],
            "velocity": body["velocity"],
            "angular_velocity": body["angular_velocity"],
            "collision_shape": body["collision_shape"],
            "collision_params": body["collision_params"],
            "friction": body["friction"],
            "restitution": body["restitution"],
            "is_active": body["is_active"],
            "created_at": body["created_at"],
            "updated_at": body["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get physics body: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get physics body: {str(e)}"
        )


@app.put("/api/v1/physics/bodies/{body_id}/state")
async def update_physics_state(state: PhysicsState):
    """
    Update physics body state
    """
    try:
        postgres = await get_postgres()
        
        await postgres.execute("""
            UPDATE physics_bodies
            SET position = $2,
                rotation = $3,
                velocity = $4,
                angular_velocity = $5,
                updated_at = CURRENT_TIMESTAMP
            WHERE body_id = $1
        """, state.body_id, state.position, state.rotation,
            state.velocity, state.angular_velocity)
        
        # Cache state in Redis for real-time access
        redis = await get_redis()
        await redis.setex(
            f"physics_state:{state.body_id}",
            3600,  # 1 hour TTL
            state.json()
        )
        
        logger.info(f"Updated physics state for body {state.body_id}")
        
        return {
            "body_id": state.body_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update physics state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update physics state: {str(e)}"
        )


@app.post("/api/v1/physics/apply-force")
async def apply_force(force: ForceApplication):
    """
    Apply force to a physics body
    """
    try:
        postgres = await get_postgres()
        
        # Get current body state
        body = await postgres.fetchrow(
            "SELECT velocity, mass FROM physics_bodies WHERE body_id = $1",
            force.body_id
        )
        
        if not body:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physics body not found"
            )
        
        # Calculate acceleration (F = ma, so a = F/m)
        acceleration = vector_multiply(force.force, 1.0 / body["mass"])
        
        # Update velocity (v = v + a*t)
        # For impulse, use instantaneous change
        if force.duration is None:
            # Impulse: instantaneous velocity change
            delta_velocity = vector_multiply(acceleration, 1.0)  # Assume 1 second for impulse
        else:
            # Force over time: integrate acceleration
            delta_velocity = vector_multiply(acceleration, force.duration)
        
        new_velocity = vector_add(body["velocity"], delta_velocity)
        
        # Update body
        await postgres.execute(
            "UPDATE physics_bodies SET velocity = $2, updated_at = CURRENT_TIMESTAMP WHERE body_id = $1",
            force.body_id, new_velocity
        )
        
        logger.info(f"Applied force to body {force.body_id}")
        
        return {
            "body_id": force.body_id,
            "new_velocity": new_velocity,
            "status": "applied"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply force: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply force: {str(e)}"
        )


@app.post("/api/v1/physics/raycast")
async def raycast(query: RaycastQuery) -> RaycastResult:
    """
    Perform raycast query
    """
    try:
        postgres = await get_postgres()
        
        # Get all active physics bodies
        bodies = await postgres.fetch(
            "SELECT body_id, position, collision_shape, collision_params FROM physics_bodies WHERE is_active = true"
        )
        
        # Normalize direction
        direction = vector_normalize(query.direction)
        
        closest_hit = None
        closest_distance = query.max_distance
        
        for body in bodies:
            # Simple sphere collision for demo
            # In production, use proper collision detection based on shape
            body_pos = body["position"]
            
            # Vector from ray origin to body
            to_body = vector_subtract(body_pos, query.origin)
            
            # Project onto ray direction
            projection = vector_dot(to_body, direction)
            
            if projection < 0 or projection > closest_distance:
                continue
            
            # Closest point on ray to body center
            closest_point = vector_add(query.origin, vector_multiply(direction, projection))
            
            # Distance from closest point to body center
            distance_to_center = vector_length(vector_subtract(body_pos, closest_point))
            
            # Get collision radius (simplified)
            radius = body["collision_params"].get("radius", 1.0)
            
            if distance_to_center <= radius:
                # Ray hits body
                distance = projection - math.sqrt(radius**2 - distance_to_center**2)
                
                if distance < closest_distance and distance > 0:
                    closest_distance = distance
                    closest_hit = {
                        "body_id": str(body["body_id"]),
                        "hit_point": closest_point,
                        "distance": distance,
                        "normal": vector_normalize(vector_subtract(body_pos, closest_point))
                    }
        
        if closest_hit:
            return RaycastResult(
                hit=True,
                body_id=closest_hit["body_id"],
                hit_point=closest_hit["hit_point"],
                distance=closest_hit["distance"],
                normal=closest_hit["normal"]
            )
        else:
            return RaycastResult(
                hit=False,
                distance=query.max_distance
            )
        
    except Exception as e:
        logger.error(f"Failed to perform raycast: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform raycast: {str(e)}"
        )


@app.post("/api/v1/physics/simulations", status_code=status.HTTP_201_CREATED)
async def create_simulation(simulation: PhysicsSimulation):
    """
    Create a physics simulation
    """
    try:
        postgres = await get_postgres()
        
        simulation_id = await postgres.fetchval("""
            INSERT INTO physics_simulations (environment_id, gravity, time_step, sub_steps, is_running)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING simulation_id
        """, simulation.environment_id, simulation.gravity,
            simulation.time_step, simulation.sub_steps, simulation.is_running)
        
        logger.info(f"Created physics simulation {simulation_id}")
        
        return {
            "simulation_id": str(simulation_id),
            "environment_id": simulation.environment_id,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create simulation: {str(e)}"
        )


@app.post("/api/v1/physics/simulations/{simulation_id}/step")
async def step_simulation(simulation_id: str, steps: int = 1):
    """
    Step physics simulation forward
    """
    try:
        postgres = await get_postgres()
        
        # Get simulation config
        sim = await postgres.fetchrow(
            "SELECT * FROM physics_simulations WHERE simulation_id = $1",
            simulation_id
        )
        
        if not sim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Simulation not found"
            )
        
        # Get all dynamic bodies in simulation
        bodies = await postgres.fetch(
            "SELECT * FROM physics_bodies WHERE body_type = 'dynamic' AND is_active = true"
        )
        
        # Simple Euler integration for demo
        # In production, use proper physics engine like Bullet or PhysX
        for _ in range(steps):
            for body in bodies:
                # Apply gravity
                gravity_acceleration = sim["gravity"]
                
                # Update velocity
                new_velocity = vector_add(
                    body["velocity"],
                    vector_multiply(gravity_acceleration, sim["time_step"])
                )
                
                # Update position
                new_position = vector_add(
                    body["position"],
                    vector_multiply(new_velocity, sim["time_step"])
                )
                
                # Update body
                await postgres.execute("""
                    UPDATE physics_bodies
                    SET velocity = $2, position = $3, updated_at = CURRENT_TIMESTAMP
                    WHERE body_id = $1
                """, body["body_id"], new_velocity, new_position)
        
        logger.info(f"Stepped simulation {simulation_id} by {steps} steps")
        
        return {
            "simulation_id": simulation_id,
            "steps_performed": steps,
            "status": "stepped"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to step simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to step simulation: {str(e)}"
        )


@app.delete("/api/v1/physics/bodies/{body_id}")
async def delete_physics_body(body_id: str):
    """
    Delete a physics body
    """
    try:
        postgres = await get_postgres()
        
        result = await postgres.execute(
            "DELETE FROM physics_bodies WHERE body_id = $1",
            body_id
        )
        
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physics body not found"
            )
        
        # Remove from Redis cache
        redis = await get_redis()
        await redis.delete(f"physics_state:{body_id}")
        
        logger.info(f"Deleted physics body {body_id}")
        
        return {
            "body_id": body_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete physics body: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete physics body: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "physics-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8015)
