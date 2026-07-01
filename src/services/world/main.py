"""
World Service - World graph and environment management
Handles spatial environments, object graphs, navigation, and environmental data
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid

from shared.database.postgres import get_postgres
from shared.database.neo4j import get_neo4j
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="World Service",
    description="World graph and environment management for AI Companion",
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
class Environment(BaseModel):
    """Environment model"""
    environment_id: str = Field(..., description="Environment ID")
    name: str = Field(..., description="Environment name")
    description: Optional[str] = Field(default=None, description="Environment description")
    environment_type: str = Field(default="indoor", description="Environment type: indoor, outdoor, mixed")
    bounds: Dict[str, float] = Field(..., description="Spatial bounds (min_x, max_x, min_y, max_y, min_z, max_z)")
    navigation_mesh: Optional[str] = Field(default=None, description="Navigation mesh data")
    lighting_setup: Optional[Dict[str, Any]] = Field(default=None, description="Lighting configuration")
    objects: List[str] = Field(default_factory=list, description="Object IDs in environment")
    spawn_points: List[Dict[str, float]] = Field(default_factory=list, description="Character spawn points")
    is_active: bool = Field(default=True, description="Whether environment is active")


class WorldObject(BaseModel):
    """World object model"""
    object_id: str = Field(..., description="Object ID")
    name: str = Field(..., description="Object name")
    object_type: str = Field(..., description="Object type: furniture, decoration, interactive, static")
    category: str = Field(default="general", description="Object category")
    position: Dict[str, float] = Field(..., description="Position (x, y, z)")
    rotation: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0, "z": 0}, description="Rotation (x, y, z)")
    scale: Dict[str, float] = Field(default_factory=lambda: {"x": 1, "y": 1, "z": 1}, description="Scale (x, y, z)")
    is_interactive: bool = Field(default=False, description="Whether object is interactive")
    is_static: bool = Field(default=True, description="Whether object is static")
    physics_enabled: bool = Field(default=True, description="Whether physics is enabled")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ObjectRelationship(BaseModel):
    """Object relationship model"""
    relationship_id: str = Field(..., description="Relationship ID")
    from_object_id: str = Field(..., description="Source object ID")
    to_object_id: str = Field(..., description="Target object ID")
    relationship_type: str = Field(..., description="Relationship type: contains, supports, adjacent_to, connected_to")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Relationship properties")


class NavigationNode(BaseModel):
    """Navigation node model"""
    node_id: str = Field(..., description="Node ID")
    position: Dict[str, float] = Field(..., description="Position (x, y, z)")
    neighbors: List[str] = Field(default_factory=list, description="Neighbor node IDs")
    cost: float = Field(default=1.0, ge=0.0, description="Traversal cost")
    is_blocked: bool = Field(default=False, description="Whether node is blocked")


class PathQuery(BaseModel):
    """Path query model"""
    start_position: Dict[str, float] = Field(..., description="Start position (x, y, z)")
    end_position: Dict[str, float] = Field(..., description="End position (x, y, z)")
    environment_id: str = Field(..., description="Environment ID")
    algorithm: str = Field(default="astar", description="Pathfinding algorithm: astar, dijkstra")


class EnvironmentCreate(BaseModel):
    """Environment creation model"""
    name: str = Field(..., description="Environment name")
    description: Optional[str] = Field(default=None, description="Environment description")
    environment_type: str = Field(default="indoor", description="Environment type")
    bounds: Dict[str, float] = Field(..., description="Spatial bounds")
    spawn_points: Optional[List[Dict[str, float]]] = Field(default=None, description="Spawn points")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting World Service")
    
    # Create tables in PostgreSQL
    postgres = await get_postgres()
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS environments (
            environment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            environment_type VARCHAR(50) DEFAULT 'indoor',
            bounds JSONB NOT NULL,
            navigation_mesh TEXT,
            lighting_setup JSONB DEFAULT '{}',
            objects UUID[] DEFAULT '{}',
            spawn_points JSONB DEFAULT '[]',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS world_objects (
            object_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            object_type VARCHAR(50) NOT NULL,
            category VARCHAR(100) DEFAULT 'general',
            position JSONB NOT NULL,
            rotation JSONB DEFAULT '{"x": 0, "y": 0, "z": 0}',
            scale JSONB DEFAULT '{"x": 1, "y": 1, "z": 1}',
            is_interactive BOOLEAN DEFAULT false,
            is_static BOOLEAN DEFAULT true,
            physics_enabled BOOLEAN DEFAULT true,
            metadata JSONB DEFAULT '{}',
            environment_id UUID,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS navigation_nodes (
            node_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            environment_id UUID NOT NULL,
            position JSONB NOT NULL,
            neighbors UUID[] DEFAULT '{}',
            cost FLOAT DEFAULT 1.0 CHECK (cost >= 0),
            is_blocked BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_environments_type ON environments(environment_type)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_environments_active ON environments(is_active)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_world_objects_type ON world_objects(object_type)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_world_objects_env ON world_objects(environment_id)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_navigation_nodes_env ON navigation_nodes(environment_id)")
    
    logger.info("World Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down World Service")


# API endpoints
@app.post("/api/v1/world/environments", status_code=status.HTTP_201_CREATED)
async def create_environment(environment: EnvironmentCreate):
    """
    Create a new environment
    """
    try:
        postgres = await get_postgres()
        
        environment_id = await postgres.fetchval("""
            INSERT INTO environments (name, description, environment_type, bounds, spawn_points)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING environment_id
        """, environment.name, environment.description,
            environment.environment_type, environment.bounds,
            environment.spawn_points or [])
        
        # Create environment in Neo4j
        try:
            neo4j = await get_neo4j()
            await neo4j.execute_query(
                """
                CREATE (e:Environment {
                    id: $environment_id,
                    name: $name,
                    type: $environment_type,
                    created_at: datetime()
                })
                """,
                environment_id=str(environment_id),
                name=environment.name,
                environment_type=environment.environment_type
            )
        except Exception as e:
            logger.warning(f"Failed to create environment in Neo4j: {e}")
        
        logger.info(f"Created environment {environment_id}")
        
        return {
            "environment_id": str(environment_id),
            "name": environment.name,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create environment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create environment: {str(e)}"
        )


@app.get("/api/v1/world/environments/{environment_id}")
async def get_environment(environment_id: str):
    """
    Get environment by ID
    """
    try:
        postgres = await get_postgres()
        
        environment = await postgres.fetchrow(
            "SELECT * FROM environments WHERE environment_id = $1",
            environment_id
        )
        
        if not environment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment not found"
            )
        
        return {
            "environment_id": str(environment["environment_id"]),
            "name": environment["name"],
            "description": environment["description"],
            "environment_type": environment["environment_type"],
            "bounds": environment["bounds"],
            "navigation_mesh": environment["navigation_mesh"],
            "lighting_setup": environment["lighting_setup"],
            "objects": [str(obj_id) for obj_id in environment["objects"]] if environment["objects"] else [],
            "spawn_points": environment["spawn_points"],
            "is_active": environment["is_active"],
            "created_at": environment["created_at"],
            "updated_at": environment["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get environment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get environment: {str(e)}"
        )


@app.get("/api/v1/world/environments")
async def list_environments(
    environment_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List environments with filtering
    """
    try:
        postgres = await get_postgres()
        
        query = "SELECT * FROM environments WHERE 1=1"
        params = []
        param_count = 1
        
        if environment_type:
            query += f" AND environment_type = ${param_count}"
            params.append(environment_type)
            param_count += 1
        
        if is_active is not None:
            query += f" AND is_active = ${param_count}"
            params.append(is_active)
            param_count += 1
        
        query += " ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])
        
        environments = await postgres.fetch(query, *params)
        
        results = []
        for env in environments:
            results.append({
                "environment_id": str(env["environment_id"]),
                "name": env["name"],
                "environment_type": env["environment_type"],
                "is_active": env["is_active"],
                "created_at": env["created_at"]
            })
        
        return {
            "environments": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to list environments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list environments: {str(e)}"
        )


@app.post("/api/v1/world/objects", status_code=status.HTTP_201_CREATED)
async def create_world_object(obj: WorldObject, environment_id: Optional[str] = None):
    """
    Create a new world object
    """
    try:
        postgres = await get_postgres()
        
        object_id = await postgres.fetchval("""
            INSERT INTO world_objects (
                name, object_type, category, position, rotation, scale,
                is_interactive, is_static, physics_enabled, metadata, environment_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING object_id
        """, obj.name, obj.object_type, obj.category, obj.position,
            obj.rotation, obj.scale, obj.is_interactive, obj.is_static,
            obj.physics_enabled, obj.metadata or {}, environment_id)
        
        # Create object in Neo4j
        try:
            neo4j = await get_neo4j()
            await neo4j.execute_query(
                """
                CREATE (o:WorldObject {
                    id: $object_id,
                    name: $name,
                    type: $object_type,
                    category: $category,
                    position: $position,
                    created_at: datetime()
                })
                """,
                object_id=str(object_id),
                name=obj.name,
                object_type=obj.object_type,
                category=obj.category,
                position=str(obj.position)
            )
        except Exception as e:
            logger.warning(f"Failed to create object in Neo4j: {e}")
        
        # Add to environment if specified
        if environment_id:
            await postgres.execute(
                "UPDATE environments SET objects = array_append(objects, $1) WHERE environment_id = $2",
                object_id, environment_id
            )
        
        logger.info(f"Created world object {object_id}")
        
        return {
            "object_id": str(object_id),
            "name": obj.name,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create world object: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create world object: {str(e)}"
        )


@app.get("/api/v1/world/objects/{object_id}")
async def get_world_object(object_id: str):
    """
    Get world object by ID
    """
    try:
        postgres = await get_postgres()
        
        obj = await postgres.fetchrow(
            "SELECT * FROM world_objects WHERE object_id = $1",
            object_id
        )
        
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="World object not found"
            )
        
        return {
            "object_id": str(obj["object_id"]),
            "name": obj["name"],
            "object_type": obj["object_type"],
            "category": obj["category"],
            "position": obj["position"],
            "rotation": obj["rotation"],
            "scale": obj["scale"],
            "is_interactive": obj["is_interactive"],
            "is_static": obj["is_static"],
            "physics_enabled": obj["physics_enabled"],
            "metadata": obj["metadata"],
            "environment_id": str(obj["environment_id"]) if obj["environment_id"] else None,
            "created_at": obj["created_at"],
            "updated_at": obj["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get world object: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get world object: {str(e)}"
        )


@app.get("/api/v1/world/environments/{environment_id}/objects")
async def get_environment_objects(environment_id: str):
    """
    Get all objects in an environment
    """
    try:
        postgres = await get_postgres()
        
        objects = await postgres.fetch(
            "SELECT * FROM world_objects WHERE environment_id = $1",
            environment_id
        )
        
        results = []
        for obj in objects:
            results.append({
                "object_id": str(obj["object_id"]),
                "name": obj["name"],
                "object_type": obj["object_type"],
                "category": obj["category"],
                "position": obj["position"],
                "is_interactive": obj["is_interactive"]
            })
        
        return {
            "environment_id": environment_id,
            "objects": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to get environment objects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get environment objects: {str(e)}"
        )


@app.post("/api/v1/world/objects/relationship", status_code=status.HTTP_201_CREATED)
async def create_object_relationship(relationship: ObjectRelationship):
    """
    Create a relationship between two objects
    """
    try:
        # Create relationship in Neo4j
        neo4j = await get_neo4j()
        
        await neo4j.execute_query(
            """
            MATCH (o1:WorldObject {id: $from_object_id})
            MATCH (o2:WorldObject {id: $to_object_id})
            CREATE (o1)-[r:RELATED_TO {
                relationship_id: $relationship_id,
                type: $relationship_type,
                properties: $properties,
                created_at: datetime()
            }]->(o2)
            RETURN r
            """,
            from_object_id=relationship.from_object_id,
            to_object_id=relationship.to_object_id,
            relationship_id=relationship.relationship_id,
            relationship_type=relationship.relationship_type,
            properties=relationship.properties or {}
        )
        
        logger.info(f"Created object relationship {relationship.relationship_id}")
        
        return {
            "relationship_id": relationship.relationship_id,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create object relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create object relationship: {str(e)}"
        )


@app.post("/api/v1/world/navigation/nodes", status_code=status.HTTP_201_CREATED)
async def create_navigation_node(node: NavigationNode, environment_id: str):
    """
    Create a navigation node
    """
    try:
        postgres = await get_postgres()
        
        node_id = await postgres.fetchval("""
            INSERT INTO navigation_nodes (environment_id, position, neighbors, cost, is_blocked)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING node_id
        """, environment_id, node.position, node.neighbors,
            node.cost, node.is_blocked)
        
        logger.info(f"Created navigation node {node_id}")
        
        return {
            "node_id": str(node_id),
            "environment_id": environment_id,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create navigation node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create navigation node: {str(e)}"
        )


@app.post("/api/v1/world/navigation/path")
async def find_path(query: PathQuery):
    """
    Find path between two positions using A* algorithm
    """
    try:
        # Simple A* implementation (in production, use a proper pathfinding library)
        postgres = await get_postgres()
        
        # Get navigation nodes for environment
        nodes = await postgres.fetch(
            "SELECT * FROM navigation_nodes WHERE environment_id = $1 AND is_blocked = false",
            query.environment_id
        )
        
        if not nodes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No navigation nodes found for environment"
            )
        
        # Build node graph
        node_graph = {}
        for node in nodes:
            node_graph[str(node["node_id"])] = {
                "position": node["position"],
                "neighbors": [str(n) for n in node["neighbors"]],
                "cost": node["cost"]
            }
        
        # Find nearest nodes to start and end positions
        def distance(pos1, pos2):
            return ((pos1["x"] - pos2["x"])**2 + (pos1["y"] - pos2["y"])**2 + (pos1["z"] - pos2["z"])**2)**0.5
        
        start_node = min(node_graph.keys(), key=lambda n: distance(query.start_position, node_graph[n]["position"]))
        end_node = min(node_graph.keys(), key=lambda n: distance(query.end_position, node_graph[n]["position"]))
        
        # A* pathfinding
        from heapq import heappush, heappop
        
        open_set = [(0, start_node)]
        came_from = {}
        g_score = {start_node: 0}
        f_score = {start_node: distance(query.start_position, node_graph[start_node]["position"])}
        
        while open_set:
            current = heappop(open_set)[1]
            
            if current == end_node:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(node_graph[current]["position"])
                    current = came_from[current]
                path.append(node_graph[start_node]["position"])
                path.reverse()
                
                return {
                    "path": path,
                    "length": len(path),
                    "algorithm": query.algorithm
                }
            
            for neighbor in node_graph[current]["neighbors"]:
                if neighbor not in node_graph:
                    continue
                
                tentative_g = g_score[current] + node_graph[current]["cost"]
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + distance(node_graph[neighbor]["position"], query.end_position)
                    heappush(open_set, (f_score[neighbor], neighbor))
        
        # No path found
        return {
            "path": [],
            "length": 0,
            "algorithm": query.algorithm,
            "message": "No path found"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find path: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find path: {str(e)}"
        )


@app.delete("/api/v1/world/objects/{object_id}")
async def delete_world_object(object_id: str):
    """
    Delete a world object
    """
    try:
        postgres = await get_postgres()
        
        result = await postgres.execute(
            "DELETE FROM world_objects WHERE object_id = $1",
            object_id
        )
        
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="World object not found"
            )
        
        # Delete from Neo4j
        try:
            neo4j = await get_neo4j()
            await neo4j.execute_query(
                """
                MATCH (o:WorldObject {id: $object_id})
                DETACH DELETE o
                """,
                object_id=object_id
            )
        except Exception as e:
            logger.warning(f"Failed to delete object from Neo4j: {e}")
        
        logger.info(f"Deleted world object {object_id}")
        
        return {
            "object_id": object_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete world object: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete world object: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "world-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8014)
