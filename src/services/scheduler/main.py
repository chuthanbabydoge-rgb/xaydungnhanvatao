"""
Scheduler Service - Time-based tasks, context awareness, and adaptive scheduling
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import uuid
import asyncio

from shared.database.mongodb import get_mongodb
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Scheduler Service",
    description="Time-based tasks, context awareness, and adaptive scheduling for AI Companion",
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
class TaskType(str, Enum):
    """Task types"""
    REMINDER = "reminder"
    GOAL_TRIGGER = "goal_trigger"
    PROACTIVE_ACTION = "proactive_action"
    MAINTENANCE = "maintenance"
    LEARNING = "learning"


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecurrenceType(str, Enum):
    """Recurrence types"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ScheduledTask(BaseModel):
    """Scheduled task model"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID")
    type: TaskType = Field(..., description="Task type")
    name: str = Field(..., description="Task name")
    description: str = Field(..., description="Task description")
    scheduled_time: str = Field(..., description="Scheduled execution time (ISO format)")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    recurrence: RecurrenceType = Field(default=RecurrenceType.NONE, description="Recurrence type")
    recurrence_interval: Optional[int] = Field(default=None, description="Recurrence interval in days")
    context_requirements: Optional[List[str]] = Field(default=None, description="Required context conditions")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TaskExecution(BaseModel):
    """Task execution model"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = Field(..., description="Task ID")
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = Field(default=None, description="Completion time")
    status: TaskStatus = Field(default=TaskStatus.RUNNING, description="Execution status")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ContextCondition(BaseModel):
    """Context condition model"""
    condition_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID")
    condition_type: str = Field(..., description="Condition type: time, energy, mood, location")
    threshold: float = Field(..., description="Condition threshold")
    operator: str = Field(default=">=", description="Comparison operator: >=, <=, ==, !=")
    description: str = Field(..., description="Condition description")


class ScheduleRequest(BaseModel):
    """Schedule task request"""
    user_id: str = Field(..., description="User ID")
    type: TaskType = Field(..., description="Task type")
    name: str = Field(..., description="Task name")
    description: str = Field(..., description="Task description")
    scheduled_time: str = Field(..., description="Scheduled execution time (ISO format)")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Task parameters")
    recurrence: RecurrenceType = Field(default=RecurrenceType.NONE, description="Recurrence type")
    recurrence_interval: Optional[int] = Field(default=None, description="Recurrence interval in days")
    context_requirements: Optional[List[str]] = Field(default=None, description="Required context conditions")


# Scheduler system
class SchedulerSystem:
    """Manages task scheduling and execution"""
    
    def __init__(self):
        self.is_running = False
        self.scheduled_tasks = {}
    
    async def start(self):
        """Start the scheduler"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Scheduler started")
        
        # Start background task processor
        asyncio.create_task(self._process_tasks())
    
    async def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        logger.info("Scheduler stopped")
    
    async def schedule_task(self, task: ScheduledTask) -> str:
        """Schedule a task"""
        db = await get_mongodb()
        tasks = db["scheduled_tasks"]
        
        # Store task in database
        await tasks.insert_one(task.dict())
        
        # Add to in-memory schedule
        scheduled_time = datetime.fromisoformat(task.scheduled_time)
        self.scheduled_tasks[task.task_id] = {
            "task": task,
            "scheduled_time": scheduled_time
        }
        
        logger.info(f"Scheduled task {task.task_id} for {task.scheduled_time}")
        
        return task.task_id
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        db = await get_mongodb()
        tasks = db["scheduled_tasks"]
        
        # Update in database
        result = await tasks.update_one(
            {"task_id": task_id},
            {"$set": {"status": TaskStatus.CANCELLED, "updated_at": datetime.utcnow().isoformat()}}
        )
        
        # Remove from in-memory schedule
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
        
        logger.info(f"Cancelled task {task_id}")
        
        return result.modified_count > 0
    
    async def _process_tasks(self):
        """Process scheduled tasks"""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                # Check for tasks that are due
                due_tasks = []
                for task_id, task_info in self.scheduled_tasks.items():
                    if task_info["scheduled_time"] <= current_time:
                        due_tasks.append(task_id)
                
                # Execute due tasks
                for task_id in due_tasks:
                    await self._execute_task(task_id)
                
                # Sleep for 1 second before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing tasks: {e}")
                await asyncio.sleep(5)
    
    async def _execute_task(self, task_id: str):
        """Execute a task"""
        db = await get_mongodb()
        tasks = db["scheduled_tasks"]
        executions = db["task_executions"]
        
        try:
            # Get task
            task_doc = await tasks.find_one({"task_id": task_id})
            if not task_doc:
                logger.warning(f"Task {task_id} not found")
                return
            
            task_doc.pop("_id", None)
            task = ScheduledTask(**task_doc)
            
            # Update task status
            await tasks.update_one(
                {"task_id": task_id},
                {"$set": {"status": TaskStatus.RUNNING, "updated_at": datetime.utcnow().isoformat()}}
            )
            
            # Create execution record
            execution = TaskExecution(task_id=task_id)
            await executions.insert_one(execution.dict())
            
            # Execute task based on type
            result = await self._execute_task_by_type(task)
            
            # Update execution
            await executions.update_one(
                {"execution_id": execution.execution_id},
                {
                    "$set": {
                        "status": TaskStatus.COMPLETED,
                        "completed_at": datetime.utcnow().isoformat(),
                        "result": result
                    }
                }
            )
            
            # Update task status
            await tasks.update_one(
                {"task_id": task_id},
                {"$set": {"status": TaskStatus.COMPLETED, "updated_at": datetime.utcnow().isoformat()}}
            )
            
            # Handle recurrence
            if task.recurrence != RecurrenceType.NONE and task.recurrence_interval:
                await self._schedule_next_occurrence(task)
            
            # Remove from in-memory schedule
            if task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task_id]
            
            logger.info(f"Executed task {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {e}")
            
            # Update execution with error
            await executions.update_one(
                {"execution_id": execution.execution_id},
                {
                    "$set": {
                        "status": TaskStatus.FAILED,
                        "completed_at": datetime.utcnow().isoformat(),
                        "error": str(e)
                    }
                }
            )
            
            # Update task status
            await tasks.update_one(
                {"task_id": task_id},
                {"$set": {"status": TaskStatus.FAILED, "updated_at": datetime.utcnow().isoformat()}}
            )
    
    async def _execute_task_by_type(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute task based on its type"""
        if task.type == TaskType.REMINDER:
            return await self._execute_reminder(task)
        elif task.type == TaskType.GOAL_TRIGGER:
            return await self._execute_goal_trigger(task)
        elif task.type == TaskType.PROACTIVE_ACTION:
            return await self._execute_proactive_action(task)
        elif task.type == TaskType.MAINTENANCE:
            return await self._execute_maintenance(task)
        elif task.type == TaskType.LEARNING:
            return await self._execute_learning(task)
        else:
            return {"status": "unknown_task_type"}
    
    async def _execute_reminder(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a reminder task"""
        # In production, this would send a notification to the user
        reminder_message = task.parameters.get("message", "Reminder")
        
        return {
            "type": "reminder",
            "message": reminder_message,
            "delivered": True
        }
    
    async def _execute_goal_trigger(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a goal trigger task"""
        # In production, this would trigger a goal in the motivation service
        goal_type = task.parameters.get("goal_type", "assistance")
        
        return {
            "type": "goal_trigger",
            "goal_type": goal_type,
            "triggered": True
        }
    
    async def _execute_proactive_action(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a proactive action task"""
        # In production, this would execute a proactive action
        action_type = task.parameters.get("action_type", "check_in")
        
        return {
            "type": "proactive_action",
            "action_type": action_type,
            "executed": True
        }
    
    async def _execute_maintenance(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a maintenance task"""
        # In production, this would perform system maintenance
        maintenance_type = task.parameters.get("maintenance_type", "cleanup")
        
        return {
            "type": "maintenance",
            "maintenance_type": maintenance_type,
            "completed": True
        }
    
    async def _execute_learning(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a learning task"""
        # In production, this would trigger learning processes
        learning_type = task.parameters.get("learning_type", "preference_update")
        
        return {
            "type": "learning",
            "learning_type": learning_type,
            "completed": True
        }
    
    async def _schedule_next_occurrence(self, task: ScheduledTask):
        """Schedule the next occurrence of a recurring task"""
        current_time = datetime.fromisoformat(task.scheduled_time)
        interval_days = task.recurrence_interval or 1
        
        next_time = current_time + timedelta(days=interval_days)
        
        # Create new task for next occurrence
        new_task = ScheduledTask(
            user_id=task.user_id,
            type=task.type,
            name=task.name,
            description=task.description,
            scheduled_time=next_time.isoformat(),
            priority=task.priority,
            parameters=task.parameters,
            recurrence=task.recurrence,
            recurrence_interval=task.recurrence_interval,
            context_requirements=task.context_requirements
        )
        
        await self.schedule_task(new_task)
    
    async def get_scheduled_tasks(self, user_id: str) -> List[ScheduledTask]:
        """Get scheduled tasks for a user"""
        db = await get_mongodb()
        tasks = db["scheduled_tasks"]
        
        cursor = tasks.find({
            "user_id": user_id,
            "status": {"$in": [TaskStatus.PENDING, TaskStatus.SCHEDULED]}
        }).sort("scheduled_time", 1)
        
        result = []
        async for task in cursor:
            task.pop("_id", None)
            result.append(ScheduledTask(**task))
        
        return result
    
    async def get_task_executions(self, task_id: str) -> List[TaskExecution]:
        """Get execution history for a task"""
        db = await get_mongodb()
        executions = db["task_executions"]
        
        cursor = executions.find({"task_id": task_id}).sort("started_at", -1)
        
        result = []
        async for execution in cursor:
            execution.pop("_id", None)
            result.append(TaskExecution(**execution))
        
        return result


# Context awareness system
class ContextAwarenessSystem:
    """Manages context conditions for task execution"""
    
    async def add_context_condition(self, condition: ContextCondition):
        """Add a context condition"""
        db = await get_mongodb()
        conditions = db["context_conditions"]
        
        await conditions.insert_one(condition.dict())
        
        logger.info(f"Added context condition {condition.condition_id}")
    
    async def check_context_conditions(self, user_id: str, required_conditions: List[str]) -> bool:
        """Check if context conditions are met"""
        db = await get_mongodb()
        conditions = db["context_conditions"]
        
        for condition_id in required_conditions:
            condition = await conditions.find_one({"condition_id": condition_id})
            if not condition:
                logger.warning(f"Context condition {condition_id} not found")
                return False
            
            # Check condition (simplified)
            # In production, this would check actual context values
            is_met = self._evaluate_condition(condition)
            
            if not is_met:
                return False
        
        return True
    
    def _evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        """Evaluate a context condition"""
        # Simplified evaluation
        # In production, this would check actual context values from various sources
        return True  # Placeholder


# Global instances
scheduler = SchedulerSystem()
context_awareness = ContextAwarenessSystem()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Scheduler Service")
    
    try:
        # Start scheduler
        await scheduler.start()
    except Exception as e:
        logger.warning(f"Scheduler start skipped: {e}")
    
    try:
        # Load existing scheduled tasks
        db = await get_mongodb()
        tasks = db["scheduled_tasks"]
        
        cursor = tasks.find({
            "status": {"$in": [TaskStatus.PENDING, TaskStatus.SCHEDULED]},
            "scheduled_time": {"$gte": datetime.utcnow().isoformat()}
        })
        
        async for task_doc in cursor:
            task_doc.pop("_id", None)
            task = ScheduledTask(**task_doc)
            
            scheduled_time = datetime.fromisoformat(task.scheduled_time)
            scheduler.scheduled_tasks[task.task_id] = {
                "task": task,
                "scheduled_time": scheduled_time
            }
        
        logger.info(f"Loaded {len(scheduler.scheduled_tasks)} scheduled tasks")
    except Exception as e:
        logger.warning(f"Scheduled tasks loading skipped: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Scheduler Service")
    
    # Stop scheduler
    await scheduler.stop()


# API endpoints
@app.post("/api/v1/scheduler/schedule", status_code=status.HTTP_201_CREATED)
async def schedule_task(request: ScheduleRequest):
    """
    Schedule a new task
    """
    try:
        task = ScheduledTask(
            user_id=request.user_id,
            type=request.type,
            name=request.name,
            description=request.description,
            scheduled_time=request.scheduled_time,
            priority=request.priority,
            parameters=request.parameters or {},
            recurrence=request.recurrence,
            recurrence_interval=request.recurrence_interval,
            context_requirements=request.context_requirements
        )
        
        task_id = await scheduler.schedule_task(task)
        
        return {
            "task_id": task_id,
            "status": "scheduled",
            "scheduled_time": task.scheduled_time
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule task: {str(e)}"
        )


@app.delete("/api/v1/scheduler/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a scheduled task
    """
    try:
        success = await scheduler.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        return {
            "task_id": task_id,
            "status": "cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )


@app.get("/api/v1/scheduler/tasks/{user_id}")
async def get_scheduled_tasks(user_id: str):
    """
    Get scheduled tasks for a user
    """
    try:
        tasks = await scheduler.get_scheduled_tasks(user_id)
        
        return {
            "user_id": user_id,
            "tasks": [task.dict() for task in tasks],
            "count": len(tasks)
        }
        
    except Exception as e:
        logger.error(f"Failed to get scheduled tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduled tasks: {str(e)}"
        )


@app.get("/api/v1/scheduler/tasks/{task_id}/executions")
async def get_task_executions(task_id: str):
    """
    Get execution history for a task
    """
    try:
        executions = await scheduler.get_task_executions(task_id)
        
        return {
            "task_id": task_id,
            "executions": [execution.dict() for execution in executions],
            "count": len(executions)
        }
        
    except Exception as e:
        logger.error(f"Failed to get task executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task executions: {str(e)}"
        )


@app.post("/api/v1/scheduler/context", status_code=status.HTTP_201_CREATED)
async def add_context_condition(request: ContextCondition):
    """
    Add a context condition
    """
    try:
        await context_awareness.add_context_condition(request)
        
        return {
            "condition_id": request.condition_id,
            "status": "added"
        }
        
    except Exception as e:
        logger.error(f"Failed to add context condition: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add context condition: {str(e)}"
        )


@app.post("/api/v1/scheduler/context/check")
async def check_context_conditions(user_id: str, required_conditions: List[str]):
    """
    Check if context conditions are met
    """
    try:
        is_met = await context_awareness.check_context_conditions(user_id, required_conditions)
        
        return {
            "user_id": user_id,
            "conditions_met": is_met,
            "required_conditions": required_conditions
        }
        
    except Exception as e:
        logger.error(f"Failed to check context conditions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check context conditions: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "scheduler-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
