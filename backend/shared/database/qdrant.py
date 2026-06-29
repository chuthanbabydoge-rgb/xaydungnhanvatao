"""
Qdrant vector database connection and management
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import Optional, List, Dict, Any
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# Qdrant client
qdrant_client: Optional[QdrantClient] = None


async def init_qdrant():
    """
    Initialize Qdrant connection
    """
    global qdrant_client
    
    try:
        qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        
        # Test connection
        collections = qdrant_client.get_collections()
        logger.info(f"Qdrant connection initialized successfully. Found {len(collections.collections)} collections")
        
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant connection: {e}")
        raise


async def close_qdrant():
    """
    Close Qdrant connection
    """
    global qdrant_client
    
    if qdrant_client:
        qdrant_client.close()
        logger.info("Qdrant connection closed")


def get_qdrant():
    """
    Get Qdrant client instance
    """
    if qdrant_client is None:
        raise RuntimeError("Qdrant not initialized. Call init_qdrant() first.")
    return qdrant_client


async def create_collection(
    collection_name: str,
    vector_size: int = 1536,
    distance: Distance = Distance.COSINE
):
    """
    Create a collection in Qdrant
    """
    client = get_qdrant()
    
    try:
        # Check if collection exists
        collections = client.get_collections()
        existing_collections = [c.name for c in collections.collections]
        
        if collection_name in existing_collections:
            logger.info(f"Collection {collection_name} already exists")
            return
        
        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance
            )
        )
        logger.info(f"Collection {collection_name} created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create collection {collection_name}: {e}")
        raise


async def insert_points(
    collection_name: str,
    points: List[PointStruct]
):
    """
    Insert points into a collection
    """
    client = get_qdrant()
    
    try:
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        logger.info(f"Inserted {len(points)} points into {collection_name}")
        
    except Exception as e:
        logger.error(f"Failed to insert points into {collection_name}: {e}")
        raise


async def search_points(
    collection_name: str,
    query_vector: List[float],
    limit: int = 10,
    score_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Search for similar points in a collection
    """
    client = get_qdrant()
    
    try:
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold
        )
        
        return [
            {
                "id": point.id,
                "score": point.score,
                "payload": point.payload
            }
            for point in results
        ]
        
    except Exception as e:
        logger.error(f"Failed to search in {collection_name}: {e}")
        raise


async def delete_points(
    collection_name: str,
    point_ids: List[str]
):
    """
    Delete points from a collection
    """
    client = get_qdrant()
    
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=point_ids
        )
        logger.info(f"Deleted {len(point_ids)} points from {collection_name}")
        
    except Exception as e:
        logger.error(f"Failed to delete points from {collection_name}: {e}")
        raise
