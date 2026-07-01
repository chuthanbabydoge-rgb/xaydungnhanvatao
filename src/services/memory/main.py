"""
Memory Service - Manages vector storage and knowledge graph
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from shared.database.qdrant import create_collection, insert_points, search_points, delete_points
from shared.database.neo4j import create_node, create_relationship, find_node, find_related_nodes
from shared.utils.dependencies import get_qdrant_client, get_neo4j_driver
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Memory Service",
    description="Manages vector storage and knowledge graph for AI Companion",
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
class MemoryStore(BaseModel):
    """Memory store request"""
    user_id: str = Field(..., description="User ID")
    content: str = Field(..., description="Memory content")
    embedding: List[float] = Field(..., description="Vector embedding")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    memory_type: str = Field(default="episodic", description="Type of memory: episodic, semantic, procedural")


class MemorySearch(BaseModel):
    """Memory search request"""
    user_id: str = Field(..., description="User ID")
    query_embedding: List[float] = Field(..., description="Query vector embedding")
    limit: int = Field(default=10, description="Number of results to return")
    score_threshold: float = Field(default=0.7, description="Minimum similarity score")
    memory_type: Optional[str] = Field(default=None, description="Filter by memory type")


class MemoryRetrieve(BaseModel):
    """Memory retrieve request"""
    user_id: str = Field(..., description="User ID")
    memory_id: str = Field(..., description="Memory ID")


class MemoryConsolidate(BaseModel):
    """Memory consolidation request"""
    user_id: str = Field(..., description="User ID")
    memory_ids: List[str] = Field(..., description="Memory IDs to consolidate")
    summary: str = Field(..., description="Consolidated summary")


class EntityNode(BaseModel):
    """Entity node for knowledge graph"""
    entity_id: str = Field(..., description="Entity ID")
    entity_type: str = Field(..., description="Entity type: person, place, object, concept")
    name: str = Field(..., description="Entity name")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Additional properties")


class RelationshipEdge(BaseModel):
    """Relationship edge for knowledge graph"""
    from_entity_id: str = Field(..., description="Source entity ID")
    to_entity_id: str = Field(..., description="Target entity ID")
    relationship_type: str = Field(..., description="Relationship type")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Additional properties")


class GraphQuery(BaseModel):
    """Graph query request"""
    entity_id: str = Field(..., description="Entity ID")
    relationship_type: Optional[str] = Field(default=None, description="Filter by relationship type")
    direction: str = Field(default="outgoing", description="Relationship direction: outgoing, incoming, both")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Memory Service")
    
    try:
        # Create collections if they don't exist
        await create_collection("episodic_memory", vector_size=1536)
        await create_collection("semantic_memory", vector_size=1536)
        await create_collection("procedural_memory", vector_size=1536)
        
        logger.info("Memory Service started successfully")
    except Exception as e:
        logger.warning(f"Memory Service startup initialization skipped: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Memory Service")


# API endpoints
@app.post("/api/v1/memory/store", status_code=status.HTTP_201_CREATED)
async def store_memory(request: MemoryStore):
    """
    Store a memory in vector database and knowledge graph
    """
    try:
        from qdrant_client.models import PointStruct
        import uuid
        
        # Generate memory ID
        memory_id = str(uuid.uuid4())
        
        # Store in Qdrant
        collection_name = f"{request.memory_type}_memory"
        point = PointStruct(
            id=memory_id,
            vector=request.embedding,
            payload={
                "user_id": request.user_id,
                "content": request.content,
                "metadata": request.metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
                "memory_type": request.memory_type
            }
        )
        
        await insert_points(collection_name, [point])
        
        # Extract entities and create in knowledge graph
        entities = await extract_entities(request.content)
        for entity in entities:
            # Create entity node if it doesn't exist
            existing = await find_node("Entity", {"entity_id": entity["entity_id"]})
            if not existing:
                await create_node("Entity", {
                    "entity_id": entity["entity_id"],
                    "entity_type": entity["entity_type"],
                    "name": entity["name"],
                    "properties": entity.get("properties", {})
                })
            
            # Create relationship between memory and entity
            await create_relationship(
                "Memory", memory_id,
                "Entity", entity["entity_id"],
                "MENTIONS",
                {"timestamp": datetime.utcnow().isoformat()}
            )
        
        logger.info(f"Stored memory {memory_id} for user {request.user_id}")
        
        return {
            "memory_id": memory_id,
            "status": "stored",
            "entities_extracted": len(entities)
        }
        
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store memory: {str(e)}"
        )


@app.post("/api/v1/memory/search")
async def search_memory(request: MemorySearch):
    """
    Search for similar memories using vector similarity
    """
    try:
        collection_name = "episodic_memory"
        if request.memory_type:
            collection_name = f"{request.memory_type}_memory"
        
        results = await search_points(
            collection_name=collection_name,
            query_vector=request.query_embedding,
            limit=request.limit,
            score_threshold=request.score_threshold
        )
        
        # Filter by user_id
        filtered_results = [
            result for result in results
            if result["payload"].get("user_id") == request.user_id
        ]
        
        logger.info(f"Found {len(filtered_results)} memories for user {request.user_id}")
        
        return {
            "user_id": request.user_id,
            "results": filtered_results,
            "count": len(filtered_results)
        }
        
    except Exception as e:
        logger.error(f"Failed to search memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memory: {str(e)}"
        )


@app.post("/api/v1/memory/retrieve")
async def retrieve_memory(request: MemoryRetrieve):
    """
    Retrieve a specific memory by ID
    """
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        client = await get_qdrant_client()
        
        # Search in all collections
        memory_types = ["episodic", "semantic", "procedural"]
        for memory_type in memory_types:
            collection_name = f"{memory_type}_memory"
            
            try:
                results = client.retrieve(
                    collection_name=collection_name,
                    ids=[request.memory_id]
                )
                
                if results:
                    memory = results[0]
                    return {
                        "memory_id": memory.id,
                        "content": memory.payload.get("content"),
                        "metadata": memory.payload.get("metadata"),
                        "timestamp": memory.payload.get("timestamp"),
                        "memory_type": memory_type
                    }
            except Exception:
                continue
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {request.memory_id} not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}"
        )


@app.delete("/api/v1/memory/{memory_id}")
async def delete_memory(memory_id: str, user_id: str):
    """
    Delete a memory by ID
    """
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        client = await get_qdrant_client()
        
        # Search in all collections
        memory_types = ["episodic", "semantic", "procedural"]
        deleted = False
        
        for memory_type in memory_types:
            collection_name = f"{memory_type}_memory"
            
            try:
                # Check if memory belongs to user
                results = client.retrieve(
                    collection_name=collection_name,
                    ids=[memory_id]
                )
                
                if results and results[0].payload.get("user_id") == user_id:
                    await delete_points(collection_name, [memory_id])
                    deleted = True
                    break
            except Exception:
                continue
        
        if deleted:
            logger.info(f"Deleted memory {memory_id} for user {user_id}")
            return {"memory_id": memory_id, "status": "deleted"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found or access denied"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}"
        )


@app.post("/api/v1/memory/consolidate")
async def consolidate_memory(request: MemoryConsolidate):
    """
    Consolidate multiple memories into a single summary
    """
    try:
        from qdrant_client.models import PointStruct
        import uuid
        
        # Generate consolidated memory ID
        consolidated_id = str(uuid.uuid4())
        
        # Create consolidated memory
        consolidated_memory = {
            "memory_id": consolidated_id,
            "user_id": request.user_id,
            "summary": request.summary,
            "source_memory_ids": request.memory_ids,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store in semantic memory
        # Note: In production, you would generate an embedding for the summary
        # using an embedding model like OpenAI's text-embedding-ada-002
        
        logger.info(f"Consolidated {len(request.memory_ids)} memories into {consolidated_id}")
        
        return {
            "consolidated_memory_id": consolidated_id,
            "status": "consolidated",
            "source_count": len(request.memory_ids)
        }
        
    except Exception as e:
        logger.error(f"Failed to consolidate memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to consolidate memory: {str(e)}"
        )


@app.post("/api/v1/graph/entity", status_code=status.HTTP_201_CREATED)
async def create_entity(request: EntityNode):
    """
    Create an entity node in the knowledge graph
    """
    try:
        # Check if entity already exists
        existing = await find_node("Entity", {"entity_id": request.entity_id})
        
        if existing:
            return {
                "entity_id": request.entity_id,
                "status": "exists"
            }
        
        # Create entity node
        await create_node("Entity", {
            "entity_id": request.entity_id,
            "entity_type": request.entity_type,
            "name": request.name,
            "properties": request.properties or {}
        })
        
        logger.info(f"Created entity {request.entity_id}")
        
        return {
            "entity_id": request.entity_id,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entity: {str(e)}"
        )


@app.post("/api/v1/graph/relationship", status_code=status.HTTP_201_CREATED)
async def create_graph_relationship(request: RelationshipEdge):
    """
    Create a relationship between entities in the knowledge graph
    """
    try:
        await create_relationship(
            "Entity", request.from_entity_id,
            "Entity", request.to_entity_id,
            request.relationship_type,
            request.properties or {}
        )
        
        logger.info(f"Created relationship {request.from_entity_id} -> {request.to_entity_id}")
        
        return {
            "status": "created",
            "from_entity": request.from_entity_id,
            "to_entity": request.to_entity_id,
            "relationship_type": request.relationship_type
        }
        
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create relationship: {str(e)}"
        )


@app.post("/api/v1/graph/query")
async def query_graph(request: GraphQuery):
    """
    Query the knowledge graph for related entities
    """
    try:
        results = await find_related_nodes(
            node_label="Entity",
            node_id=request.entity_id,
            relationship_type=request.relationship_type,
            direction=request.direction
        )
        
        logger.info(f"Found {len(results)} related entities for {request.entity_id}")
        
        return {
            "entity_id": request.entity_id,
            "related_entities": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to query graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query graph: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "memory-service",
        "timestamp": datetime.utcnow().isoformat()
    }


# Helper functions
async def extract_entities(content: str) -> List[Dict[str, Any]]:
    """
    Extract entities from content using NLP
    In production, this would use a proper NLP library like spaCy or transformers
    """
    # Placeholder implementation
    # In production, use entity extraction from OpenAI or spaCy
    entities = []
    
    # Simple keyword extraction (placeholder)
    words = content.split()
    for word in words:
        if word[0].isupper() and len(word) > 3:
            entities.append({
                "entity_id": word.lower(),
                "entity_type": "unknown",
                "name": word,
                "properties": {}
            })
    
    return entities


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
