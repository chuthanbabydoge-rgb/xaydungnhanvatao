"""Session management for database"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.models import Session as SessionModel
from app.db.database import db

logger = logging.getLogger(__name__)


class SessionManager:
    """Session manager for user sessions"""
    
    async def create_session(
        self,
        user_id: str,
        session_token: str,
        device_info: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_in_hours: int = 24
    ) -> SessionModel:
        """Create a new session"""
        async with db.get_session() as session:
            session_obj = SessionModel(
                user_id=user_id,
                session_token=session_token,
                device_info=device_info,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
            )
            
            session.add(session_obj)
            await session.commit()
            await session.refresh(session_obj)
            
            logger.info(f"Created session {session_obj.id} for user {user_id}")
            return session_obj
    
    async def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Get session by ID"""
        async with db.get_session() as session:
            result = await session.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            return result.scalar_one_or_none()
    
    async def get_session_by_token(self, session_token: str) -> Optional[SessionModel]:
        """Get session by token"""
        async with db.get_session() as session:
            result = await session.execute(
                select(SessionModel).where(
                    SessionModel.session_token == session_token,
                    SessionModel.is_active == True,
                    SessionModel.expires_at > datetime.utcnow()
                )
            )
            return result.scalar_one_or_none()
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity"""
        async with db.get_session() as session:
            result = await session.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session_obj = result.scalar_one_or_none()
            
            if session_obj:
                session_obj.last_activity_at = datetime.utcnow()
                await session.commit()
                return True
            
            return False
    
    async def update_session_context(self, session_id: str, context_data: Dict[str, Any]) -> bool:
        """Update session context data"""
        async with db.get_session() as session:
            result = await session.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session_obj = result.scalar_one_or_none()
            
            if session_obj:
                if session_obj.context_data is None:
                    session_obj.context_data = {}
                
                session_obj.context_data.update(context_data)
                await session.commit()
                return True
            
            return False
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session"""
        async with db.get_session() as session:
            result = await session.execute(
                select(SessionModel).where(SessionModel.id == session_id)
            )
            session_obj = result.scalar_one_or_none()
            
            if session_obj:
                session_obj.is_active = False
                await session.commit()
                return True
            
            return False
    
    async def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        async with db.get_session() as session:
            result = await session.execute(
                select(SessionModel).where(
                    SessionModel.user_id == user_id,
                    SessionModel.is_active == True
                )
            )
            sessions = result.scalars().all()
            
            for session_obj in sessions:
                session_obj.is_active = False
            
            await session.commit()
            return len(sessions)
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        async with db.get_session() as session:
            result = await session.execute(
                select(SessionModel).where(
                    SessionModel.expires_at < datetime.utcnow(),
                    SessionModel.is_active == True
                )
            )
            sessions = result.scalars().all()
            
            for session_obj in sessions:
                session_obj.is_active = False
            
            await session.commit()
            return len(sessions)


# Global session manager instance
session_manager = SessionManager()
