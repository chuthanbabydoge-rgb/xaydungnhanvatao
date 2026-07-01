"""
Conversation Service - Manages conversations and message history
"""
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json
import uuid

from shared.database.mongodb import get_mongodb
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Conversation Service",
    description="Manages conversations and message history for AI Companion",
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
class Message(BaseModel):
    """Message model"""
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(default=None, description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ConversationCreate(BaseModel):
    """Create conversation request"""
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(default=None, description="Conversation title")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ConversationUpdate(BaseModel):
    """Update conversation request"""
    title: Optional[str] = Field(default=None, description="Conversation title")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class MessageAdd(BaseModel):
    """Add message request"""
    conversation_id: str = Field(..., description="Conversation ID")
    message: Message = Field(..., description="Message to add")


class ConversationQuery(BaseModel):
    """Query conversations request"""
    user_id: str = Field(..., description="User ID")
    limit: int = Field(default=20, description="Number of conversations to return")
    offset: int = Field(default=0, description="Offset for pagination")


class ConversationMessagesQuery(BaseModel):
    """Query conversation messages request"""
    conversation_id: str = Field(..., description="Conversation ID")
    limit: int = Field(default=50, description="Number of messages to return")
    offset: int = Field(default=0, description="Offset for pagination")


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, conversation_id: str):
        """Connect a WebSocket to a conversation"""
        await websocket.accept()
        
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        
        self.active_connections[conversation_id].append(websocket)
        logger.info(f"WebSocket connected to conversation {conversation_id}")
    
    def disconnect(self, websocket: WebSocket, conversation_id: str):
        """Disconnect a WebSocket from a conversation"""
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)
            
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
        
        logger.info(f"WebSocket disconnected from conversation {conversation_id}")
    
    async def broadcast(self, conversation_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections in a conversation"""
        if conversation_id in self.active_connections:
            for connection in self.active_connections[conversation_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to WebSocket: {e}")


manager = ConnectionManager()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Conversation Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Conversation Service")


# API endpoints
@app.post("/api/v1/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(request: ConversationCreate):
    """
    Create a new conversation
    """
    try:
        db = await get_mongodb()
        conversations = db["conversations"]
        
        conversation_id = str(uuid.uuid4())
        
        conversation = {
            "conversation_id": conversation_id,
            "user_id": request.user_id,
            "title": request.title or "New Conversation",
            "messages": [],
            "metadata": request.metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await conversations.insert_one(conversation)
        
        logger.info(f"Created conversation {conversation_id} for user {request.user_id}")
        
        return {
            "conversation_id": conversation_id,
            "user_id": request.user_id,
            "title": conversation["title"],
            "created_at": conversation["created_at"]
        }
        
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )


@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get a conversation by ID
    """
    try:
        db = await get_mongodb()
        conversations = db["conversations"]
        
        conversation = await conversations.find_one({"conversation_id": conversation_id})
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        conversation.pop("_id", None)
        
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )


@app.put("/api/v1/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, request: ConversationUpdate):
    """
    Update a conversation
    """
    try:
        db = await get_mongodb()
        conversations = db["conversations"]
        
        update_data = {
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if request.title is not None:
            update_data["title"] = request.title
        
        if request.metadata is not None:
            update_data["metadata"] = request.metadata
        
        result = await conversations.update_one(
            {"conversation_id": conversation_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        logger.info(f"Updated conversation {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "status": "updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}"
        )


@app.delete("/api/v1/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation
    """
    try:
        db = await get_mongodb()
        conversations = db["conversations"]
        
        result = await conversations.delete_one({"conversation_id": conversation_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        logger.info(f"Deleted conversation {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )


@app.post("/api/v1/conversations/query")
async def query_conversations(request: ConversationQuery):
    """
    Query conversations for a user
    """
    try:
        db = await get_mongodb()
        conversations = db["conversations"]
        
        cursor = conversations.find({"user_id": request.user_id}) \
            .sort("updated_at", -1) \
            .skip(request.offset) \
            .limit(request.limit)
        
        results = []
        async for conversation in cursor:
            conversation.pop("_id", None)
            results.append(conversation)
        
        logger.info(f"Found {len(results)} conversations for user {request.user_id}")
        
        return {
            "user_id": request.user_id,
            "conversations": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to query conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query conversations: {str(e)}"
        )


@app.post("/api/v1/messages/add")
async def add_message(request: MessageAdd):
    """
    Add a message to a conversation
    """
    try:
        db = await get_mongodb()
        conversations = db["conversations"]
        
        # Add timestamp if not provided
        if not request.message.timestamp:
            request.message.timestamp = datetime.utcnow().isoformat()
        
        message_data = request.message.dict()
        
        result = await conversations.update_one(
            {"conversation_id": request.conversation_id},
            {
                "$push": {"messages": message_data},
                "$set": {"updated_at": datetime.utcnow().isoformat()}
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {request.conversation_id} not found"
            )
        
        # Broadcast to WebSocket connections
        await manager.broadcast(request.conversation_id, {
            "type": "message_added",
            "conversation_id": request.conversation_id,
            "message": message_data
        })
        
        logger.info(f"Added message to conversation {request.conversation_id}")
        
        return {
            "conversation_id": request.conversation_id,
            "message": message_data,
            "status": "added"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {str(e)}"
        )


@app.post("/api/v1/messages/query")
async def query_messages(request: ConversationMessagesQuery):
    """
    Query messages in a conversation
    """
    try:
        db = await get_mongodb()
        conversations = db["conversations"]
        
        conversation = await conversations.find_one({"conversation_id": request.conversation_id})
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {request.conversation_id} not found"
            )
        
        messages = conversation.get("messages", [])
        
        # Apply pagination
        start = request.offset
        end = start + request.limit
        paginated_messages = messages[start:end]
        
        logger.info(f"Retrieved {len(paginated_messages)} messages from conversation {request.conversation_id}")
        
        return {
            "conversation_id": request.conversation_id,
            "messages": paginated_messages,
            "total": len(messages),
            "offset": request.offset,
            "limit": request.limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query messages: {str(e)}"
        )


@app.websocket("/ws/conversations/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for real-time conversation updates
    """
    await manager.connect(websocket, conversation_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle incoming WebSocket messages
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, conversation_id)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "conversation-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
