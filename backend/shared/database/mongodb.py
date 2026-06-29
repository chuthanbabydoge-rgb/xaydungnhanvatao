"""
MongoDB database connection and management
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# MongoDB client
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_database = None


async def init_mongodb():
    """
    Initialize MongoDB connection
    """
    global mongodb_client, mongodb_database
    
    try:
        mongodb_client = AsyncIOMotorClient(settings.mongodb_url)
        mongodb_database = mongodb_client[settings.mongodb_db]
        
        # Test connection
        await mongodb_database.command("ping")
        logger.info("MongoDB connection initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB connection: {e}")
        raise


async def close_mongodb():
    """
    Close MongoDB connection
    """
    global mongodb_client
    
    if mongodb_client:
        mongodb_client.close()
        logger.info("MongoDB connection closed")


def get_mongodb():
    """
    Get MongoDB database instance
    """
    if mongodb_database is None:
        raise RuntimeError("MongoDB not initialized. Call init_mongodb() first.")
    return mongodb_database
