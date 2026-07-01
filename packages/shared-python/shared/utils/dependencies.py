"""
Dependency injection utilities
"""
from typing import Generator, AsyncGenerator
from sqlalchemy.orm import Session
from shared.database.postgres import get_db
from shared.database.mongodb import get_mongodb
from shared.database.redis import get_redis
from shared.database.qdrant import get_qdrant
from shared.database.neo4j import get_neo4j


def get_postgres_db() -> Generator[Session, None, None]:
    """
    Get PostgreSQL database session
    """
    yield from get_db()


async def get_mongodb_db():
    """
    Get MongoDB database instance
    """
    return get_mongodb()


async def get_redis_client():
    """
    Get Redis client instance
    """
    return get_redis()


async def get_qdrant_client():
    """
    Get Qdrant client instance
    """
    return get_qdrant()


async def get_neo4j_driver():
    """
    Get Neo4j driver instance
    """
    return get_neo4j()
