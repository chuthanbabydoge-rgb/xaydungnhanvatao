"""
Scheduler Agent - Task scheduling and execution management
Schedules tasks, manages execution queues, and optimizes resource allocation
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import heapq
from collections import defaultdict

from shared.agent_base import BaseAgent, AgentMessage, MessageType


class TaskStatus(Enum):
    """Task status states"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class SchedulePriority(Enum):
    """Schedule priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    agent_type: str = ""
    task_data: Dict[str, Any] = field(default_factory=dict)
    priority: SchedulePriority = SchedulePriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    scheduled_time: Optional[datetime] = None
    deadline: Optional[datetime] = None
    estimated_duration: Optional[timedelta] = None
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue comparison"""
        if self.scheduled_time and other.scheduled_time:
            if self.scheduled_time != other.scheduled_time:
                return self.scheduled_time < other.scheduled_time
        return self.priority.value < other.priority.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "priority": self.priority.value,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "estimated_duration": str(self.estimated_duration) if self.estimated_duration else None,
            "dependencies": self.dependencies,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class Schedule:
    """Represents a schedule"""
    schedule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    tasks: List[ScheduledTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    status: TaskStatus = TaskStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "name": self.name,
            "description": self.description,
            "task_count": len(self.tasks),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value
        }


class SchedulerAgent(BaseAgent):
    """
    Scheduler Agent - Task scheduling and execution management
    Schedules tasks, manages execution queues, and optimizes resource allocation
    """
    
    def __init__(
        self,
        agent_id: str = "scheduler-agent-1",
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        enable_tracing: bool = True,
        enable_metrics: bool = True,
        max_concurrent_tasks: int = 10
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="scheduler",
            rabbitmq_url=rabbitmq_url,
            enable_tracing=enable_tracing,
            enable_metrics=enable_metrics
        )
        
        # Task storage
        self.tasks: Dict[str, ScheduledTask] = {}  # task_id -> task
        self.schedules: Dict[str, Schedule] = {}  # schedule_id -> schedule
        
        # Priority queues
        self.ready_queue: List[ScheduledTask] = []  # Tasks ready to execute
        self.scheduled_queue: List[ScheduledTask] = []  # Tasks scheduled for future
        
        # Execution management
        self.running_tasks: Dict[str, ScheduledTask] = {}  # Currently running tasks
        self.max_concurrent_tasks = max_concurrent_tasks
        self.active_tasks = 0
        
        # Dependency tracking
        self.dependency_graph: Dict[str, List[str]] = {}  # task_id -> dependent task_ids
        self.blocked_tasks: Dict[str, ScheduledTask] = {}  # Blocked tasks
        
        # Capabilities
        self.capabilities = [
            "task_scheduling",
            "priority_management",
            "dependency_resolution",
            "resource_allocation",
            "execution_monitoring",
            "deadline_management"
        ]
    
    def register_handlers(self):
        """Register message handlers"""
        self.message_handlers[MessageType.TASK_REQUEST] = self.handle_task_request
        self.message_handlers[MessageType.QUERY] = self.handle_query
        self.message_handlers[MessageType.EVENT] = self.handle_event
    
    async def start(self):
        """Start the scheduler agent"""
        await super().start()
        
        # Start background tasks
        await self.start_background_tasks()
        
        # Announce capabilities
        await self.announce_capabilities()
    
    async def start_background_tasks(self):
        """Start background scheduling tasks"""
        # Task scheduler loop
        scheduler_loop = asyncio.create_task(self.scheduler_loop())
        self.background_tasks.append(scheduler_loop)
        
        # Deadline monitor loop
        deadline_monitor = asyncio.create_task(self.deadline_monitor_loop())
        self.background_tasks.append(deadline_monitor)
        
        # Task execution monitor
        execution_monitor = asyncio.create_task(self.execution_monitor_loop())
        self.background_tasks.append(execution_monitor)
    
    async def announce_capabilities(self):
        """Announce agent capabilities"""
        capabilities_message = AgentMessage(
            sender_id=self.agent_id,
            message_type=MessageType.EVENT,
            content={
                "event_type": "agent_capabilities",
                "agent_id": self.agent_id,
                "capabilities": self.capabilities
            }
        )
        
        await self.publish_message(
            capabilities_message,
            routing_key="planner.*"
        )
    
    async def handle_task_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming scheduling task"""
        task_data = message.content
        task_type = task_data.get("task_type")
        
        if task_type == "schedule_task":
            result = await self.schedule_task(task_data)
        elif task_type == "create_schedule":
            result = await self.create_schedule(task_data)
        elif task_type == "cancel_task":
            result = await self.cancel_task(task_data)
        elif task_type == "update_task":
            result = await self.update_task(task_data)
        else:
            result = {"error": "Unknown task type"}
        
        return result
    
    async def handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle query messages"""
        query_type = message.content.get("query_type")
        
        if query_type == "task_status":
            task_id = message.content.get("task_id")
            if task_id in self.tasks:
                return self.tasks[task_id].to_dict()
            else:
                return {"error": "Task not found"}
        
        elif query_type == "schedule_status":
            schedule_id = message.content.get("schedule_id")
            if schedule_id in self.schedules:
                return self.schedules[schedule_id].to_dict()
            else:
                return {"error": "Schedule not found"}
        
        elif query_type == "queue_status":
            return await self.get_queue_status()
        
        elif query_type == "capabilities":
            return {"capabilities": self.capabilities}
        
        else:
            return {"error": "Unknown query type"}
    
    async def handle_event(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle event messages"""
        event_type = message.content.get("event_type")
        
        if event_type == "task_completed":
            task_id = message.content.get("task_id")
            result = message.content.get("result")
            await self.handle_task_completion(task_id, result)
        
        elif event_type == "task_failed":
            task_id = message.content.get("task_id")
            error = message.content.get("error")
            await self.handle_task_failure(task_id, error)
        
        return {"status": "acknowledged"}
    
    async def schedule_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a single task"""
        with self.tracer.start_as_current_span("schedule_task") as span:
            task = ScheduledTask(
                name=task_data.get("name", ""),
                description=task_data.get("description", ""),
                agent_type=task_data.get("agent_type", ""),
                task_data=task_data.get("task_data", {}),
                priority=SchedulePriority(task_data.get("priority", 3)),
                scheduled_time=datetime.fromisoformat(task_data["scheduled_time"]) if task_data.get("scheduled_time") else None,
                deadline=datetime.fromisoformat(task_data["deadline"]) if task_data.get("deadline") else None,
                estimated_duration=timedelta(seconds=task_data.get("estimated_duration", 60)),
                dependencies=task_data.get("dependencies", []),
                max_retries=task_data.get("max_retries", 3),
                metadata=task_data.get("metadata", {})
            )
            
            # Store task
            self.tasks[task.task_id] = task
            
            # Update dependency graph
            for dep_id in task.dependencies:
                if dep_id not in self.dependency_graph:
                    self.dependency_graph[dep_id] = []
                self.dependency_graph[dep_id].append(task.task_id)
            
            # Add to appropriate queue
            if task.scheduled_time and task.scheduled_time > datetime.utcnow():
                heapq.heappush(self.scheduled_queue, task)
                task.status = TaskStatus.SCHEDULED
            else:
                # Check if dependencies are satisfied
                if await self.check_dependencies(task):
                    heapq.heappush(self.ready_queue, task)
                    task.status = TaskStatus.SCHEDULED
                else:
                    self.blocked_tasks[task.task_id] = task
                    task.status = TaskStatus.BLOCKED
            
            span.set_attribute("task_id", task.task_id)
            span.set_attribute("agent_type", task.agent_type)
            
            return {
                "task_id": task.task_id,
                "status": task.status.value,
                "scheduled_time": task.scheduled_time.isoformat() if task.scheduled_time else None
            }
    
    async def create_schedule(self, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a schedule with multiple tasks"""
        schedule = Schedule(
            name=schedule_data.get("name", ""),
            description=schedule_data.get("description", "")
        )
        
        tasks_data = schedule_data.get("tasks", [])
        task_ids = []
        
        for task_data in tasks_data:
            result = await self.schedule_task(task_data)
            task_ids.append(result["task_id"])
        
        # Get task objects
        for task_id in task_ids:
            if task_id in self.tasks:
                schedule.tasks.append(self.tasks[task_id])
        
        self.schedules[schedule.schedule_id] = schedule
        
        return {
            "schedule_id": schedule.schedule_id,
            "task_count": len(schedule.tasks),
            "status": schedule.status.value
        }
    
    async def cancel_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a scheduled task"""
        task_id = task_data.get("task_id")
        
        if task_id in self.tasks:
            task = self.tasks[task_id]
            
            if task.status in [TaskStatus.PENDING, TaskStatus.SCHEDULED, TaskStatus.BLOCKED]:
                task.status = TaskStatus.CANCELLED
                
                # Remove from queues
                self.ready_queue = [t for t in self.ready_queue if t.task_id != task_id]
                self.scheduled_queue = [t for t in self.scheduled_queue if t.task_id != task_id]
                self.blocked_tasks.pop(task_id, None)
                
                return {"status": "cancelled", "task_id": task_id}
            else:
                return {"error": "Task cannot be cancelled in current state"}
        else:
            return {"error": "Task not found"}
    
    async def update_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a scheduled task"""
        task_id = task_data.get("task_id")
        updates = task_data.get("updates", {})
        
        if task_id in self.tasks:
            task = self.tasks[task_id]
            
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            return {"status": "updated", "task_id": task_id}
        else:
            return {"error": "Task not found"}
    
    async def check_dependencies(self, task: ScheduledTask) -> bool:
        """Check if task dependencies are satisfied"""
        for dep_id in task.dependencies:
            if dep_id in self.tasks:
                dep_task = self.tasks[dep_id]
                if dep_task.status != TaskStatus.COMPLETED:
                    return False
        return True
    
    async def scheduler_loop(self):
        """Main scheduling loop"""
        while self.status.value == "running":
            try:
                await asyncio.sleep(1)  # Check every second
                
                # Move scheduled tasks to ready queue
                now = datetime.utcnow()
                while self.scheduled_queue and self.scheduled_queue[0].scheduled_time <= now:
                    task = heapq.heappop(self.scheduled_queue)
                    
                    if await self.check_dependencies(task):
                        heapq.heappush(self.ready_queue, task)
                        task.status = TaskStatus.SCHEDULED
                    else:
                        self.blocked_tasks[task.task_id] = task
                        task.status = TaskStatus.BLOCKED
                
                # Check blocked tasks
                blocked_to_ready = []
                for task_id, task in list(self.blocked_tasks.items()):
                    if await self.check_dependencies(task):
                        blocked_to_ready.append(task_id)
                
                for task_id in blocked_to_ready:
                    task = self.blocked_tasks.pop(task_id)
                    heapq.heappush(self.ready_queue, task)
                    task.status = TaskStatus.SCHEDULED
                
                # Execute ready tasks
                await self.execute_ready_tasks()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
    
    async def execute_ready_tasks(self):
        """Execute tasks from the ready queue"""
        while self.ready_queue and self.active_tasks < self.max_concurrent_tasks:
            task = heapq.heappop(self.ready_queue)
            
            # Check deadline
            if task.deadline and task.deadline < datetime.utcnow():
                task.status = TaskStatus.FAILED
                task.error = "Deadline exceeded"
                continue
            
            # Execute task
            await self.execute_task(task)
    
    async def execute_task(self, task: ScheduledTask):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self.running_tasks[task.task_id] = task
        self.active_tasks += 1
        
        try:
            # Send task to appropriate agent
            response = await self.send_task_request(
                task.agent_type,
                task.task_data,
                priority=task.priority.value
            )
            
            if response:
                await self.handle_task_completion(task.task_id, response)
            else:
                await self.handle_task_failure(task.task_id, "No response from agent")
        
        except Exception as e:
            await self.handle_task_failure(task.task_id, str(e))
    
    async def handle_task_completion(self, task_id: str, result: Dict[str, Any]):
        """Handle task completion"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = result
            
            # Update dependent tasks
            await self.update_dependent_tasks(task_id)
            
            # Remove from running tasks
            del self.running_tasks[task_id]
            self.active_tasks -= 1
            
            self.logger.info(f"Task {task_id} completed successfully")
    
    async def handle_task_failure(self, task_id: str, error: str):
        """Handle task failure"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.error = error
            
            # Check if retry is possible
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                
                # Re-schedule task
                heapq.heappush(self.ready_queue, task)
                
                self.logger.info(f"Retrying task {task_id} (attempt {task.retry_count})")
            else:
                task.status = TaskStatus.FAILED
            
            # Remove from running tasks
            del self.running_tasks[task_id]
            self.active_tasks -= 1
            
            self.logger.error(f"Task {task_id} failed: {error}")
    
    async def update_dependent_tasks(self, completed_task_id: str):
        """Update tasks that depend on completed task"""
        if completed_task_id in self.dependency_graph:
            dependent_ids = self.dependency_graph[completed_task_id]
            
            for dep_id in dependent_ids:
                if dep_id in self.blocked_tasks:
                    task = self.blocked_tasks[dep_id]
                    
                    if await self.check_dependencies(task):
                        del self.blocked_tasks[dep_id]
                        heapq.heappush(self.ready_queue, task)
                        task.status = TaskStatus.SCHEDULED
    
    async def deadline_monitor_loop(self):
        """Monitor task deadlines"""
        while self.status.value == "running":
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                now = datetime.utcnow()
                
                # Check running tasks for deadline violations
                for task_id, task in list(self.running_tasks.items()):
                    if task.deadline and task.deadline < now:
                        task.status = TaskStatus.FAILED
                        task.error = "Deadline exceeded"
                        del self.running_tasks[task_id]
                        self.active_tasks -= 1
                        
                        self.logger.warning(f"Task {task_id} exceeded deadline")
                
                # Check scheduled tasks for imminent deadlines
                for task in self.scheduled_queue:
                    if task.deadline:
                        time_until_deadline = (task.deadline - now).total_seconds()
                        if time_until_deadline < 300:  # Less than 5 minutes
                            self.logger.warning(f"Task {task.task_id} deadline approaching in {time_until_deadline}s")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Deadline monitor error: {e}")
    
    async def execution_monitor_loop(self):
        """Monitor task execution"""
        while self.status.value == "running":
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check for stuck tasks
                now = datetime.utcnow()
                for task_id, task in list(self.running_tasks.items()):
                    if task.started_at:
                        execution_time = (now - task.started_at).total_seconds()
                        
                        # Check if task is running too long
                        if task.estimated_duration:
                            max_duration = task.estimated_duration.total_seconds() * 3  # 3x estimate
                            if execution_time > max_duration:
                                self.logger.warning(f"Task {task_id} running longer than expected: {execution_time}s")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Execution monitor error: {e}")
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "ready_queue_size": len(self.ready_queue),
            "scheduled_queue_size": len(self.scheduled_queue),
            "blocked_tasks": len(self.blocked_tasks),
            "running_tasks": len(self.running_tasks),
            "active_tasks": self.active_tasks,
            "max_concurrent_tasks": self.max_concurrent_tasks
        }
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a scheduling task"""
        task_type = task.get("task_type")
        
        if task_type == "schedule_task":
            return await self.schedule_task(task)
        elif task_type == "create_schedule":
            return await self.create_schedule(task)
        else:
            return {"error": "Unknown task type"}


async def main():
    """Main entry point for the scheduler agent"""
    agent = SchedulerAgent()
    
    try:
        await agent.start()
        
        # Start consuming messages
        await agent.consume_messages()
        
    except KeyboardInterrupt:
        await agent.stop()
    except Exception as e:
        agent.logger.error(f"Agent error: {e}")
        await agent.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())