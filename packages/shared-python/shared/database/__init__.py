from .postgres import get_db

def get_postgres():
    return get_db()

def get_postgres_session():
    return get_db()

from .redis import get_redis

def get_redis_client():
    return get_redis()

from .mongodb import get_mongodb

def get_mongodb_client():
    return get_mongodb()

from .qdrant import get_qdrant

def get_qdrant_client():
    return get_qdrant()

from .neo4j import get_neo4j

def get_neo4j_driver():
    return get_neo4j()

__all__ = [
    "get_db",
    "get_postgres",
    "get_postgres_session",
    "get_redis",
    "get_redis_client",
    "get_mongodb",
    "get_mongodb_client",
    "get_qdrant",
    "get_qdrant_client",
    "get_neo4j",
    "get_neo4j_driver",
]
