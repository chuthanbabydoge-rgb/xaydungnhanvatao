"""Database connection and session management"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from app.models import Base
from config import get_settings

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager"""
    
    def __init__(self):
        self.engine = None
        self.async_session_maker = None
        self.settings = get_settings()
    
    async def connect(self):
        """Create database engine and session maker"""
        if self.engine is not None:
            return
        
        logger.info(f"Connecting to database: {self.settings.DATABASE_URL}")
        
        self.engine = create_async_engine(
            self.settings.DATABASE_URL,
            echo=self.settings.DEBUG,
            pool_size=self.settings.DATABASE_POOL_SIZE,
            max_overflow=self.settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
        )
        
        logger.info("Database connection established")
    
    async def disconnect(self):
        """Close database connections"""
        if self.engine is None:
            return
        
        logger.info("Closing database connection")
        
        await self.engine.dispose()
        self.engine = None
        self.async_session_maker = None
        
        logger.info("Database connection closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session context manager"""
        if self.async_session_maker is None:
            await self.connect()
        
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# Global database instance
db = Database()


async def init_db():
    """Initialize database"""
    await db.connect()


async def close_db():
    """Close database"""
    await db.disconnect()
