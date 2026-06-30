"""
Multi-Agent Service - Multi-agent coordination
Handles multiple AI agents, their coordination, communication, and task distribution
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
import asyncio

from shared.database.postgres import get_postgres
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Multi-Agent Service",
    description="Multi-agent coordination for AI Companion",
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
class Agent(BaseModel):
    """Agent model"""
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    agent_type: str = Field(..., description="Agent type: planner, coder, researcher, emotion, memory, avatar")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    status: str = Field(default="idle", description="Agent status: idle, busy, offline")
    current_task: Optional[str] = Field(default=None, description="Current task ID")
    workload: float = Field(default=0.0, ge=0.0, le=1.0, description="Current workload (0-1)")
    performance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Performance score")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    is_active: bool = Field(default=True, description="Whether agent is active")


class AgentTask(BaseModel):
    """Agent task model"""
    task_id: str = Field(..., description="Task ID")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    task_type: str = Field(..., description="Task type: planning, coding, research, emotion, memory, avatar")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1-10)")
    required_capabilities: List[str] = Field(default_factory=list, description="Required capabilities")
    estimated_duration: int = Field(default=60, description="Estimated duration in seconds")
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="Task input data")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="Task output data")
    status: str = Field(default="pending", description="Task status: pending, assigned, in_progress, completed, failed")
    assigned_agent: Optional[str] = Field(default=None, description="Assigned agent ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")


class AgentMessage(BaseModel):
    """Agent communication message model"""
    message_id: str = Field(..., description="Message ID")
    from_agent: str = Field(..., description="Sender agent ID")
    to_agent: str = Field(..., description="Receiver agent ID")
    message_type: str = Field(..., description="Message type: request, response, notification, coordination")
    content: Dict[str, Any] = Field(..., description="Message content")
    priority: int = Field(default=5, ge=1, le=10, description="Message priority")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    requires_response: bool = Field(default=False, description="Whether response is required")


class AgentCoordination(BaseModel):
    """Agent coordination model"""
    coordination_id: str = Field(..., description="Coordination ID")
    coordination_type: str = Field(..., description="Coordination type: collaboration, delegation, consensus")
    participants: List[str] = Field(..., description="Participating agent IDs")
    goal: str = Field(..., description="Coordination goal")
    status: str = Field(default="active", description="Coordination status: active, completed, failed")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Coordination context")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


class AgentCreate(BaseModel):
    """Agent creation model"""
    name: str = Field(..., description="Agent name")
    agent_type: str = Field(..., description="Agent type")
    capabilities: Optional[List[str]] = Field(default=None, description="Agent capabilities")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Multi-Agent Service")
    
    # Create tables in PostgreSQL
    postgres = await get_postgres()
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            agent_type VARCHAR(50) NOT NULL,
            capabilities TEXT[] DEFAULT '{}',
            status VARCHAR(20) DEFAULT 'idle',
            current_task UUID,
            workload FLOAT DEFAULT 0.0 CHECK (workload >= 0 AND workload <= 1),
            performance_score FLOAT DEFAULT 1.0 CHECK (performance_score >= 0 AND performance_score <= 1),
            metadata JSONB DEFAULT '{}',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS agent_tasks (
            task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            task_type VARCHAR(50) NOT NULL,
            priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
            required_capabilities TEXT[] DEFAULT '{}',
            estimated_duration INTEGER DEFAULT 60,
            input_data JSONB DEFAULT '{}',
            output_data JSONB DEFAULT '{}',
            status VARCHAR(20) DEFAULT 'pending',
            assigned_agent UUID,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS agent_messages (
            message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            from_agent UUID NOT NULL,
            to_agent UUID NOT NULL,
            message_type VARCHAR(50) NOT NULL,
            content JSONB NOT NULL,
            priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
            requires_response BOOLEAN DEFAULT false,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS agent_coordinations (
            coordination_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            coordination_type VARCHAR(50) NOT NULL,
            participants UUID[] NOT NULL,
            goal TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'active',
            context JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(agent_type)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent ON agent_tasks(assigned_agent)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_agent_messages_from ON agent_messages(from_agent)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_agent_messages_to ON agent_messages(to_agent)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_agent_coordinations_status ON agent_coordinations(status)")
    
    logger.info("Multi-Agent Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Multi-Agent Service")


# API endpoints
@app.post("/api/v1/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(agent: AgentCreate):
    """
    Create a new agent
    """
    try:
        postgres = await get_postgres()
        
        agent_id = await postgres.fetchval("""
            INSERT INTO agents (name, agent_type, capabilities, metadata)
            VALUES ($1, $2, $3, $4)
            RETURNING agent_id
        """, agent.name, agent.agent_type, agent.capabilities or [],
            agent.metadata or {})
        
        logger.info(f"Created agent {agent_id}")
        
        return {
            "agent_id": str(agent_id),
            "name": agent.name,
            "agent_type": agent.agent_type,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """
    Get agent by ID
    """
    try:
        postgres = await get_postgres()
        
        agent = await postgres.fetchrow(
            "SELECT * FROM agents WHERE agent_id = $1",
            agent_id
        )
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        return {
            "agent_id": str(agent["agent_id"]),
            "name": agent["name"],
            "agent_type": agent["agent_type"],
            "capabilities": agent["capabilities"],
            "status": agent["status"],
            "current_task": str(agent["current_task"]) if agent["current_task"] else None,
            "workload": agent["workload"],
            "performance_score": agent["performance_score"],
            "metadata": agent["metadata"],
            "is_active": agent["is_active"],
            "created_at": agent["created_at"],
            "updated_at": agent["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {str(e)}"
        )


@app.get("/api/v1/agents")
async def list_agents(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List agents with filtering
    """
    try:
        postgres = await get_postgres()
        
        query = "SELECT * FROM agents WHERE 1=1"
        params = []
        param_count = 1
        
        if agent_type:
            query += f" AND agent_type = ${param_count}"
            params.append(agent_type)
            param_count += 1
        
        if status:
            query += f" AND status = ${param_count}"
            params.append(status)
            param_count += 1
        
        if is_active is not None:
            query += f" AND is_active = ${param_count}"
            params.append(is_active)
            param_count += 1
        
        query += " ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])
        
        agents = await postgres.fetch(query, *params)
        
        results = []
        for agent in agents:
            results.append({
                "agent_id": str(agent["agent_id"]),
                "name": agent["name"],
                "agent_type": agent["agent_type"],
                "capabilities": agent["capabilities"],
                "status": agent["status"],
                "workload": agent["workload"],
                "is_active": agent["is_active"]
            })
        
        return {
            "agents": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}"
        )


@app.post("/api/v1/agents/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(task: AgentTask):
    """
    Create a new agent task
    """
    try:
        postgres = await get_postgres()
        
        task_id = await postgres.fetchval("""
            INSERT INTO agent_tasks (
                title, description, task_type, priority, required_capabilities,
                estimated_duration, input_data, status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING task_id
        """, task.title, task.description, task.task_type,
            task.priority, task.required_capabilities,
            task.estimated_duration, task.input_data or {},
            task.status)
        
        logger.info(f"Created agent task {task_id}")
        
        return {
            "task_id": str(task_id),
            "title": task.title,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@app.post("/api/v1/agents/tasks/{task_id}/assign")
async def assign_task(task_id: str, agent_id: str):
    """
    Assign a task to an agent
    """
    try:
        postgres = await get_postgres()
        
        # Check if task exists
        task = await postgres.fetchrow(
            "SELECT * FROM agent_tasks WHERE task_id = $1",
            task_id
        )
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check if agent exists and is available
        agent = await postgres.fetchrow(
            "SELECT * FROM agents WHERE agent_id = $1 AND is_active = true",
            agent_id
        )
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or inactive"
            )
        
        # Check if agent has required capabilities
        agent_capabilities = set(agent["capabilities"])
        required_capabilities = set(task["required_capabilities"])
        
        if not required_capabilities.issubset(agent_capabilities):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent lacks required capabilities"
            )
        
        # Assign task
        await postgres.execute("""
            UPDATE agent_tasks
            SET assigned_agent = $2, status = 'assigned', started_at = CURRENT_TIMESTAMP
            WHERE task_id = $1
        """, task_id, agent_id)
        
        # Update agent status
        await postgres.execute("""
            UPDATE agents
            SET status = 'busy', current_task = $2, updated_at = CURRENT_TIMESTAMP
            WHERE agent_id = $1
        """, agent_id, task_id)
        
        logger.info(f"Assigned task {task_id} to agent {agent_id}")
        
        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "assigned"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign task: {str(e)}"
        )


@app.post("/api/v1/agents/tasks/{task_id}/complete")
async def complete_task(task_id: str, output_data: Dict[str, Any]):
    """
    Mark a task as completed
    """
    try:
        postgres = await get_postgres()
        
        # Get task
        task = await postgres.fetchrow(
            "SELECT assigned_agent FROM agent_tasks WHERE task_id = $1",
            task_id
        )
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Update task
        await postgres.execute("""
            UPDATE agent_tasks
            SET status = 'completed', output_data = $2, completed_at = CURRENT_TIMESTAMP
            WHERE task_id = $1
        """, task_id, output_data)
        
        # Update agent status if task was assigned
        if task["assigned_agent"]:
            await postgres.execute("""
                UPDATE agents
                SET status = 'idle', current_task = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE agent_id = $1
            """, task["assigned_agent"])
        
        logger.info(f"Completed task {task_id}")
        
        return {
            "task_id": task_id,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete task: {str(e)}"
        )


@app.post("/api/v1/agents/messages", status_code=status.HTTP_201_CREATED)
async def send_message(message: AgentMessage):
    """
    Send a message from one agent to another
    """
    try:
        postgres = await get_postgres()
        
        message_id = await postgres.fetchval("""
            INSERT INTO agent_messages (from_agent, to_agent, message_type, content, priority, requires_response)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING message_id
        """, message.from_agent, message.to_agent, message.message_type,
            message.content, message.priority, message.requires_response)
        
        # Send to Redis for real-time delivery
        redis = await get_redis()
        await redis.publish(f"agent_messages:{message.to_agent}", message.json())
        
        logger.info(f"Sent message {message_id} from {message.from_agent} to {message.to_agent}")
        
        return {
            "message_id": str(message_id),
            "status": "sent"
        }
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@app.get("/api/v1/agents/{agent_id}/messages")
async def get_agent_messages(agent_id: str, limit: int = 50, offset: int = 0):
    """
    Get messages for an agent
    """
    try:
        postgres = await get_postgres()
        
        messages = await postgres.fetch("""
            SELECT * FROM agent_messages
            WHERE to_agent = $1 OR from_agent = $1
            ORDER BY timestamp DESC
            LIMIT $2 OFFSET $3
        """, agent_id, limit, offset)
        
        results = []
        for msg in messages:
            results.append({
                "message_id": str(msg["message_id"]),
                "from_agent": str(msg["from_agent"]),
                "to_agent": str(msg["to_agent"]),
                "message_type": msg["message_type"],
                "content": msg["content"],
                "priority": msg["priority"],
                "requires_response": msg["requires_response"],
                "timestamp": msg["timestamp"]
            })
        
        return {
            "agent_id": agent_id,
            "messages": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent messages: {str(e)}"
        )


@app.post("/api/v1/agents/coordinations", status_code=status.HTTP_201_CREATED)
async def create_coordination(coordination: AgentCoordination):
    """
    Create an agent coordination
    """
    try:
        postgres = await get_postgres()
        
        coordination_id = await postgres.fetchval("""
            INSERT INTO agent_coordinations (coordination_type, participants, goal, context)
            VALUES ($1, $2, $3, $4)
            RETURNING coordination_id
        """, coordination.coordination_type, coordination.participants,
            coordination.goal, coordination.context or {})
        
        logger.info(f"Created coordination {coordination_id}")
        
        return {
            "coordination_id": str(coordination_id),
            "coordination_type": coordination.coordination_type,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create coordination: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create coordination: {str(e)}"
        )


@app.post("/api/v1/agents/auto-assign")
async def auto_assign_task(task_type: str, required_capabilities: List[str], priority: int = 5):
    """
    Automatically assign a task to the best available agent
    """
    try:
        postgres = await get_postgres()
        
        # Find available agents with required capabilities
        agents = await postgres.fetch("""
            SELECT * FROM agents
            WHERE is_active = true
            AND status = 'idle'
            AND $1 = ANY(capabilities)
            ORDER BY performance_score DESC, workload ASC
            LIMIT 5
        """, required_capabilities[0] if required_capabilities else "")
        
        if not agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No available agents with required capabilities"
            )
        
        # Select best agent (consider workload and performance)
        best_agent = None
        best_score = -1
        
        for agent in agents:
            # Check if agent has all required capabilities
            agent_capabilities = set(agent["capabilities"])
            if not set(required_capabilities).issubset(agent_capabilities):
                continue
            
            # Calculate score (higher is better)
            score = agent["performance_score"] * (1 - agent["workload"])
            
            if score > best_score:
                best_score = score
                best_agent = agent
        
        if not best_agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No suitable agent found"
            )
        
        return {
            "agent_id": str(best_agent["agent_id"]),
            "agent_name": best_agent["name"],
            "agent_type": best_agent["agent_type"],
            "score": best_score,
            "message": "Agent selected for task assignment"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to auto-assign task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to auto-assign task: {str(e)}"
        )


@app.delete("/api/v1/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """
    Delete an agent
    """
    try:
        postgres = await get_postgres()
        
        result = await postgres.execute(
            "DELETE FROM agents WHERE agent_id = $1",
            agent_id
        )
        
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        logger.info(f"Deleted agent {agent_id}")
        
        return {
            "agent_id": agent_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "multi-agent-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8022)
