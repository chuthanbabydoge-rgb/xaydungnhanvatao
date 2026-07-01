"""
Social Service - Social relationship management
Handles relationships between users and AI companions, social interactions, and relationship tracking
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
    title="Social Service",
    description="Social relationship management for AI Companion",
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
class Relationship(BaseModel):
    """Relationship model"""
    relationship_id: str = Field(..., description="Relationship ID")
    user_id: str = Field(..., description="User ID")
    character_id: str = Field(..., description="Character ID")
    relationship_type: str = Field(default="friend", description="Relationship type: friend, mentor, companion, family")
    affinity_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Affinity score (0-1)")
    trust_level: float = Field(default=0.5, ge=0.0, le=1.0, description="Trust level (0-1)")
    interaction_count: int = Field(default=0, description="Total interaction count")
    last_interaction: Optional[datetime] = Field(default=None, description="Last interaction timestamp")
    relationship_stage: str = Field(default="acquaintance", description="Relationship stage: acquaintance, friend, close_friend, best_friend")
    shared_memories: int = Field(default=0, description="Number of shared memories")
    notes: Optional[str] = Field(default=None, description="Relationship notes")


class Interaction(BaseModel):
    """Interaction model"""
    interaction_id: str = Field(..., description="Interaction ID")
    relationship_id: str = Field(..., description="Relationship ID")
    interaction_type: str = Field(..., description="Interaction type: conversation, activity, shared_experience")
    duration: int = Field(default=0, description="Interaction duration in seconds")
    sentiment: float = Field(default=0.0, ge=-1.0, le=1.0, description="Sentiment score (-1 to 1)")
    topics: List[str] = Field(default_factory=list, description="Topics discussed")
    emotional_impact: float = Field(default=0.0, ge=-1.0, le=1.0, description="Emotional impact (-1 to 1)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Interaction timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class RelationshipUpdate(BaseModel):
    """Relationship update model"""
    affinity_delta: Optional[float] = Field(default=None, ge=-0.5, le=0.5, description="Affinity change")
    trust_delta: Optional[float] = Field(default=None, ge=-0.5, le=0.5, description="Trust change")
    notes: Optional[str] = Field(default=None, description="Update notes")


class SocialGraphQuery(BaseModel):
    """Social graph query model"""
    user_id: str = Field(..., description="User ID")
    depth: int = Field(default=1, ge=1, le=3, description="Graph depth to explore")
    relationship_types: Optional[List[str]] = Field(default=None, description="Filter by relationship types")


class RelationshipRecommendation(BaseModel):
    """Relationship recommendation model"""
    character_id: str = Field(..., description="Character ID")
    compatibility_score: float = Field(..., ge=0.0, le=1.0, description="Compatibility score")
    reasons: List[str] = Field(default_factory=list, description="Reasons for recommendation")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Social Service")
    
    try:
        # Create tables in PostgreSQL
        postgres = await get_postgres()
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                character_id UUID NOT NULL,
                relationship_type VARCHAR(50) DEFAULT 'friend',
                affinity_score FLOAT DEFAULT 0.5 CHECK (affinity_score >= 0 AND affinity_score <= 1),
                trust_level FLOAT DEFAULT 0.5 CHECK (trust_level >= 0 AND trust_level <= 1),
                interaction_count INTEGER DEFAULT 0,
                last_interaction TIMESTAMP,
                relationship_stage VARCHAR(50) DEFAULT 'acquaintance',
                shared_memories INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, character_id)
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                relationship_id UUID NOT NULL REFERENCES relationships(relationship_id) ON DELETE CASCADE,
                interaction_type VARCHAR(50) NOT NULL,
                duration INTEGER DEFAULT 0,
                sentiment FLOAT DEFAULT 0.0 CHECK (sentiment >= -1 AND sentiment <= 1),
                topics TEXT[],
                emotional_impact FLOAT DEFAULT 0.0 CHECK (emotional_impact >= -1 AND emotional_impact <= 1),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            )
        """)
        
        # Create indexes
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_relationships_user_id ON relationships(user_id)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_relationships_character_id ON relationships(character_id)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_interactions_relationship_id ON interactions(relationship_id)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp)")
        
        logger.info("Social Service started successfully")
    except Exception as e:
        logger.warning(f"Social Service startup initialization skipped: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Social Service")


# API endpoints
@app.post("/api/v1/social/relationships", status_code=status.HTTP_201_CREATED)
async def create_relationship(relationship: Relationship):
    """
    Create a new relationship between user and character
    """
    try:
        postgres = await get_postgres()
        
        # Check if relationship already exists
        existing = await postgres.fetchrow(
            "SELECT relationship_id FROM relationships WHERE user_id = $1 AND character_id = $2",
            relationship.user_id, relationship.character_id
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Relationship already exists"
            )
        
        # Create relationship
        relationship_id = await postgres.fetchval("""
            INSERT INTO relationships (
                relationship_id, user_id, character_id, relationship_type,
                affinity_score, trust_level, interaction_count, last_interaction,
                relationship_stage, shared_memories, notes
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING relationship_id
        """, relationship.relationship_id, relationship.user_id, relationship.character_id,
            relationship.relationship_type, relationship.affinity_score, relationship.trust_level,
            relationship.interaction_count, relationship.last_interaction,
            relationship.relationship_stage, relationship.shared_memories, relationship.notes)
        
        # Create relationship in Neo4j knowledge graph
        try:
            neo4j = await get_neo4j()
            await neo4j.execute_query(
                """
                MERGE (u:User {id: $user_id})
                MERGE (c:Character {id: $character_id})
                MERGE (u)-[r:RELATED_TO]->(c)
                SET r.relationship_id = $relationship_id,
                    r.relationship_type = $relationship_type,
                    r.affinity_score = $affinity_score,
                    r.trust_level = $trust_level,
                    r.created_at = datetime()
                """,
                user_id=str(relationship.user_id),
                character_id=str(relationship.character_id),
                relationship_id=str(relationship_id),
                relationship_type=relationship.relationship_type,
                affinity_score=relationship.affinity_score,
                trust_level=relationship.trust_level
            )
        except Exception as e:
            logger.warning(f"Failed to create relationship in Neo4j: {e}")
        
        logger.info(f"Created relationship {relationship_id}")
        
        return {
            "relationship_id": str(relationship_id),
            "status": "created"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create relationship: {str(e)}"
        )


@app.get("/api/v1/social/relationships/{relationship_id}")
async def get_relationship(relationship_id: str):
    """
    Get relationship by ID
    """
    try:
        postgres = await get_postgres()
        
        relationship = await postgres.fetchrow(
            "SELECT * FROM relationships WHERE relationship_id = $1",
            relationship_id
        )
        
        if not relationship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relationship not found"
            )
        
        return {
            "relationship_id": str(relationship["relationship_id"]),
            "user_id": str(relationship["user_id"]),
            "character_id": str(relationship["character_id"]),
            "relationship_type": relationship["relationship_type"],
            "affinity_score": relationship["affinity_score"],
            "trust_level": relationship["trust_level"],
            "interaction_count": relationship["interaction_count"],
            "last_interaction": relationship["last_interaction"],
            "relationship_stage": relationship["relationship_stage"],
            "shared_memories": relationship["shared_memories"],
            "notes": relationship["notes"],
            "created_at": relationship["created_at"],
            "updated_at": relationship["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get relationship: {str(e)}"
        )


@app.get("/api/v1/social/users/{user_id}/relationships")
async def get_user_relationships(user_id: str):
    """
    Get all relationships for a user
    """
    try:
        postgres = await get_postgres()
        
        relationships = await postgres.fetch(
            "SELECT * FROM relationships WHERE user_id = $1 ORDER BY affinity_score DESC",
            user_id
        )
        
        results = []
        for rel in relationships:
            results.append({
                "relationship_id": str(rel["relationship_id"]),
                "character_id": str(rel["character_id"]),
                "relationship_type": rel["relationship_type"],
                "affinity_score": rel["affinity_score"],
                "trust_level": rel["trust_level"],
                "interaction_count": rel["interaction_count"],
                "last_interaction": rel["last_interaction"],
                "relationship_stage": rel["relationship_stage"],
                "shared_memories": rel["shared_memories"]
            })
        
        return {
            "user_id": user_id,
            "relationships": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to get user relationships: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user relationships: {str(e)}"
        )


@app.put("/api/v1/social/relationships/{relationship_id}")
async def update_relationship(relationship_id: str, update: RelationshipUpdate):
    """
    Update relationship metrics
    """
    try:
        postgres = await get_postgres()
        
        # Get current relationship
        current = await postgres.fetchrow(
            "SELECT affinity_score, trust_level, interaction_count FROM relationships WHERE relationship_id = $1",
            relationship_id
        )
        
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relationship not found"
            )
        
        # Calculate new values
        new_affinity = current["affinity_score"]
        new_trust = current["trust_level"]
        
        if update.affinity_delta is not None:
            new_affinity = max(0.0, min(1.0, current["affinity_score"] + update.affinity_delta))
        
        if update.trust_delta is not None:
            new_trust = max(0.0, min(1.0, current["trust_level"] + update.trust_delta))
        
        # Update relationship
        await postgres.execute("""
            UPDATE relationships
            SET affinity_score = $2,
                trust_level = $3,
                notes = $4,
                updated_at = CURRENT_TIMESTAMP
            WHERE relationship_id = $1
        """, relationship_id, new_affinity, new_trust, update.notes)
        
        # Update relationship stage based on affinity
        new_stage = "acquaintance"
        if new_affinity >= 0.8:
            new_stage = "best_friend"
        elif new_affinity >= 0.6:
            new_stage = "close_friend"
        elif new_affinity >= 0.4:
            new_stage = "friend"
        
        await postgres.execute(
            "UPDATE relationships SET relationship_stage = $2 WHERE relationship_id = $1",
            relationship_id, new_stage
        )
        
        # Update Neo4j
        try:
            neo4j = await get_neo4j()
            await neo4j.execute_query(
                """
                MATCH (u:User)-[r:RELATED_TO]->(c:Character)
                WHERE r.relationship_id = $relationship_id
                SET r.affinity_score = $affinity_score,
                    r.trust_level = $trust_level,
                    r.relationship_stage = $relationship_stage,
                    r.updated_at = datetime()
                """,
                relationship_id=relationship_id,
                affinity_score=new_affinity,
                trust_level=new_trust,
                relationship_stage=new_stage
            )
        except Exception as e:
            logger.warning(f"Failed to update relationship in Neo4j: {e}")
        
        logger.info(f"Updated relationship {relationship_id}")
        
        return {
            "relationship_id": relationship_id,
            "status": "updated",
            "new_affinity": new_affinity,
            "new_trust": new_trust,
            "new_stage": new_stage
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update relationship: {str(e)}"
        )


@app.post("/api/v1/social/interactions", status_code=status.HTTP_201_CREATED)
async def log_interaction(interaction: Interaction):
    """
    Log a social interaction
    """
    try:
        postgres = await get_postgres()
        
        # Create interaction
        interaction_id = await postgres.fetchval("""
            INSERT INTO interactions (
                interaction_id, relationship_id, interaction_type, duration,
                sentiment, topics, emotional_impact, timestamp, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING interaction_id
        """, interaction.interaction_id, interaction.relationship_id,
            interaction.interaction_type, interaction.duration,
            interaction.sentiment, interaction.topics,
            interaction.emotional_impact, interaction.timestamp,
            interaction.metadata)
        
        # Update relationship metrics
        await postgres.execute("""
            UPDATE relationships
            SET interaction_count = interaction_count + 1,
                last_interaction = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE relationship_id = $1
        """, interaction.relationship_id, interaction.timestamp)
        
        # Update affinity based on sentiment and emotional impact
        sentiment_bonus = (interaction.sentiment + 1) / 2  # Convert to 0-1
        emotional_bonus = (interaction.emotional_impact + 1) / 2
        affinity_increase = (sentiment_bonus + emotional_bonus) / 20  # Small increment
        
        await postgres.execute("""
            UPDATE relationships
            SET affinity_score = LEAST(1.0, affinity_score + $2),
                updated_at = CURRENT_TIMESTAMP
            WHERE relationship_id = $1
        """, interaction.relationship_id, affinity_increase)
        
        logger.info(f"Logged interaction {interaction_id}")
        
        return {
            "interaction_id": str(interaction_id),
            "status": "logged"
        }
        
    except Exception as e:
        logger.error(f"Failed to log interaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log interaction: {str(e)}"
        )


@app.get("/api/v1/social/relationships/{relationship_id}/interactions")
async def get_relationship_interactions(relationship_id: str, limit: int = 50, offset: int = 0):
    """
    Get interactions for a relationship
    """
    try:
        postgres = await get_postgres()
        
        interactions = await postgres.fetch(
            """SELECT * FROM interactions 
               WHERE relationship_id = $1 
               ORDER BY timestamp DESC 
               LIMIT $2 OFFSET $3""",
            relationship_id, limit, offset
        )
        
        results = []
        for interaction in interactions:
            results.append({
                "interaction_id": str(interaction["interaction_id"]),
                "interaction_type": interaction["interaction_type"],
                "duration": interaction["duration"],
                "sentiment": interaction["sentiment"],
                "topics": interaction["topics"],
                "emotional_impact": interaction["emotional_impact"],
                "timestamp": interaction["timestamp"],
                "metadata": interaction["metadata"]
            })
        
        return {
            "relationship_id": relationship_id,
            "interactions": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to get interactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interactions: {str(e)}"
        )


@app.post("/api/v1/social/recommendations")
async def get_relationship_recommendations(user_id: str, limit: int = 5):
    """
    Get character recommendations for a user based on compatibility
    """
    try:
        # In a real implementation, this would use:
        # - User personality analysis
        # - Character personality matching
        # - Shared interests
        # - Past interaction patterns
        
        # Mock recommendations for demo
        recommendations = [
            RelationshipRecommendation(
                character_id="char_001",
                compatibility_score=0.85,
                reasons=["Similar communication style", "Shared interests in technology", "Complementary personality traits"]
            ),
            RelationshipRecommendation(
                character_id="char_002",
                compatibility_score=0.78,
                reasons=["Emotional support alignment", "Learning-focused personality", "Patient communication style"]
            ),
            RelationshipRecommendation(
                character_id="char_003",
                compatibility_score=0.72,
                reasons=["Humor compatibility", "Casual conversation style", "Shared cultural references"]
            )
        ]
        
        return {
            "user_id": user_id,
            "recommendations": recommendations[:limit],
            "count": len(recommendations[:limit])
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}"
        )


@app.get("/api/v1/social/relationships/{relationship_id}/analytics")
async def get_relationship_analytics(relationship_id: str):
    """
    Get analytics for a relationship
    """
    try:
        postgres = await get_postgres()
        
        # Get relationship
        relationship = await postgres.fetchrow(
            "SELECT * FROM relationships WHERE relationship_id = $1",
            relationship_id
        )
        
        if not relationship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relationship not found"
            )
        
        # Get interaction statistics
        stats = await postgres.fetchrow("""
            SELECT 
                COUNT(*) as total_interactions,
                AVG(duration) as avg_duration,
                AVG(sentiment) as avg_sentiment,
                AVG(emotional_impact) as avg_emotional_impact,
                MIN(timestamp) as first_interaction,
                MAX(timestamp) as last_interaction
            FROM interactions
            WHERE relationship_id = $1
        """, relationship_id)
        
        # Get topic distribution
        topics = await postgres.fetch("""
            SELECT unnest(topics) as topic, COUNT(*) as count
            FROM interactions
            WHERE relationship_id = $1
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 10
        """, relationship_id)
        
        topic_distribution = [
            {"topic": row["topic"], "count": row["count"]}
            for row in topics
        ]
        
        return {
            "relationship_id": relationship_id,
            "relationship_stage": relationship["relationship_stage"],
            "affinity_score": relationship["affinity_score"],
            "trust_level": relationship["trust_level"],
            "interaction_count": relationship["interaction_count"],
            "shared_memories": relationship["shared_memories"],
            "analytics": {
                "total_interactions": stats["total_interactions"],
                "avg_duration": float(stats["avg_duration"]) if stats["avg_duration"] else 0,
                "avg_sentiment": float(stats["avg_sentiment"]) if stats["avg_sentiment"] else 0,
                "avg_emotional_impact": float(stats["avg_emotional_impact"]) if stats["avg_emotional_impact"] else 0,
                "first_interaction": stats["first_interaction"],
                "last_interaction": stats["last_interaction"],
                "topic_distribution": topic_distribution
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


@app.delete("/api/v1/social/relationships/{relationship_id}")
async def delete_relationship(relationship_id: str):
    """
    Delete a relationship
    """
    try:
        postgres = await get_postgres()
        
        result = await postgres.execute(
            "DELETE FROM relationships WHERE relationship_id = $1",
            relationship_id
        )
        
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relationship not found"
            )
        
        # Delete from Neo4j
        try:
            neo4j = await get_neo4j()
            await neo4j.execute_query(
                """
                MATCH (u:User)-[r:RELATED_TO]->(c:Character)
                WHERE r.relationship_id = $relationship_id
                DELETE r
                """,
                relationship_id=relationship_id
            )
        except Exception as e:
            logger.warning(f"Failed to delete relationship from Neo4j: {e}")
        
        logger.info(f"Deleted relationship {relationship_id}")
        
        return {
            "relationship_id": relationship_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete relationship: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "social-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8021)
