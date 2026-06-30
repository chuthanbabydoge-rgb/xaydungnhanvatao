"""
Planner Agent - Task planning and coordination
Plans complex tasks and coordinates execution across multiple agents
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from shared.agent_base import BaseAgent, AgentMessage, MessageType


class TaskStatus(Enum):
    """Task status states"""
    PENDING = "pending"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class Task:
    """Represents a task to be planned and executed"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    estimated_duration: Optional[timedelta] = None
    actual_duration: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "dependencies": self.dependencies,
            "subtasks": self.subtasks,
            "assigned_agent": self.assigned_agent,
            "estimated_duration": str(self.estimated_duration) if self.estimated_duration else None,
            "actual_duration": str(self.actual_duration) if self.actual_duration else None,
            "metadata": self.metadata
        }


@dataclass
class ExecutionPlan:
    """Represents an execution plan for a complex task"""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    name: str = ""
    description: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    agent_assignments: Dict[str, str] = field(default_factory=dict)
    estimated_duration: Optional[timedelta] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: TaskStatus = TaskStatus.PLANNED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "agent_assignments": self.agent_assignments,
            "estimated_duration": str(self.estimated_duration) if self.estimated_duration else None,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value
        }


class PlannerAgent(BaseAgent):
    """
    Planner Agent - Plans and coordinates complex tasks
    Breaks down complex tasks into subtasks and assigns them to appropriate agents
    """
    
    def __init__(
        self,
        agent_id: str = "planner-agent-1",
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        enable_tracing: bool = True,
        enable_metrics: bool = True
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="planner",
            rabbitmq_url=rabbitmq_url,
            enable_tracing=enable_tracing,
            enable_metrics=enable_metrics
        )
        
        # Task storage
        self.tasks: Dict[str, Task] = {}
        self.plans: Dict[str, ExecutionPlan] = {}
        
        # Agent capabilities registry
        self.agent_capabilities: Dict[str, List[str]] = {}
        
        # Planning strategies
        self.planning_strategies = {
            "sequential": self.plan_sequential,
            "parallel": self.plan_parallel,
            "hierarchical": self.plan_hierarchical
        }
    
    def register_handlers(self):
        """Register message handlers"""
        self.message_handlers[MessageType.TASK_REQUEST] = self.handle_task_request
        self.message_handlers[MessageType.QUERY] = self.handle_query
        self.message_handlers[MessageType.EVENT] = self.handle_event
    
    async def handle_task_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming task request"""
        task_data = message.content
        
        # Create task
        task = Task(
            name=task_data.get("name", ""),
            description=task_data.get("description", ""),
            priority=TaskPriority(task_data.get("priority", 3)),
            deadline=datetime.fromisoformat(task_data["deadline"]) if task_data.get("deadline") else None,
            metadata=task_data.get("metadata", {})
        )
        
        self.tasks[task.task_id] = task
        
        # Plan the task
        plan = await self.plan_task(task)
        
        return {
            "task_id": task.task_id,
            "plan_id": plan.plan_id,
            "status": "planned",
            "steps": len(plan.steps)
        }
    
    async def handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle query messages"""
        query_type = message.content.get("query_type")
        
        if query_type == "task_status":
            task_id = message.content.get("task_id")
            if task_id in self.tasks:
                return self.tasks[task_id].to_dict()
            else:
                return {"error": "Task not found"}
        
        elif query_type == "plan_status":
            plan_id = message.content.get("plan_id")
            if plan_id in self.plans:
                return self.plans[plan_id].to_dict()
            else:
                return {"error": "Plan not found"}
        
        elif query_type == "agent_capabilities":
            return self.agent_capabilities
        
        else:
            return {"error": "Unknown query type"}
    
    async def handle_event(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle event messages"""
        event_type = message.content.get("event_type")
        
        if event_type == "agent_capabilities":
            agent_id = message.content.get("agent_id")
            capabilities = message.content.get("capabilities", [])
            self.agent_capabilities[agent_id] = capabilities
            self.logger.info(f"Updated capabilities for {agent_id}: {capabilities}")
        
        elif event_type == "task_completed":
            task_id = message.content.get("task_id")
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.COMPLETED
                self.logger.info(f"Task {task_id} completed")
        
        elif event_type == "task_failed":
            task_id = message.content.get("task_id")
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.FAILED
                self.logger.error(f"Task {task_id} failed")
        
        return {"status": "acknowledged"}
    
    async def plan_task(self, task: Task) -> ExecutionPlan:
        """Plan a task by breaking it down into steps"""
        with self.tracer.start_as_current_span("plan_task") as span:
            span.set_attribute("task_id", task.task_id)
            span.set_attribute("task_name", task.name)
            
            # Determine planning strategy
            strategy = task.metadata.get("planning_strategy", "sequential")
            
            # Execute planning strategy
            planning_func = self.planning_strategies.get(strategy, self.plan_sequential)
            plan = await planning_func(task)
            
            self.plans[plan.plan_id] = plan
            task.status = TaskStatus.PLANNED
            
            return plan
    
    async def plan_sequential(self, task: Task) -> ExecutionPlan:
        """Plan task with sequential execution"""
        plan = ExecutionPlan(
            task_id=task.task_id,
            name=f"Plan for {task.name}",
            description=f"Sequential execution plan for {task.description}"
        )
        
        # Analyze task and create steps
        steps = await self.analyze_task(task)
        
        # Order steps sequentially
        for i, step in enumerate(steps):
            step["order"] = i
            if i > 0:
                step["dependencies"] = [steps[i-1]["step_id"]]
            
            # Assign to appropriate agent
            agent = await self.assign_step_to_agent(step)
            step["assigned_agent"] = agent
            plan.agent_assignments[step["step_id"]] = agent
        
        plan.steps = steps
        plan.estimated_duration = timedelta(seconds=len(steps) * 30)  # Estimate 30s per step
        
        return plan
    
    async def plan_parallel(self, task: Task) -> ExecutionPlan:
        """Plan task with parallel execution where possible"""
        plan = ExecutionPlan(
            task_id=task.task_id,
            name=f"Parallel plan for {task.name}",
            description=f"Parallel execution plan for {task.description}"
        )
        
        # Analyze task and create steps
        steps = await self.analyze_task(task)
        
        # Group independent steps for parallel execution
        independent_groups = await self.group_independent_steps(steps)
        
        # Create parallel execution structure
        for group in independent_groups:
            for step in group:
                agent = await self.assign_step_to_agent(step)
                step["assigned_agent"] = agent
                step["parallel_group"] = independent_groups.index(group)
                plan.agent_assignments[step["step_id"]] = agent
        
        plan.steps = steps
        plan.estimated_duration = timedelta(seconds=len(independent_groups) * 30)
        
        return plan
    
    async def plan_hierarchical(self, task: Task) -> ExecutionPlan:
        """Plan task with hierarchical structure"""
        plan = ExecutionPlan(
            task_id=task.task_id,
            name=f"Hierarchical plan for {task.name}",
            description=f"Hierarchical execution plan for {task.description}"
        )
        
        # Create hierarchical breakdown
        main_steps = await self.analyze_task(task)
        
        for main_step in main_steps:
            # Break down each main step into sub-steps
            sub_steps = await self.analyze_subtasks(main_step)
            
            main_step["subtasks"] = sub_steps
            main_step["assigned_agent"] = await self.assign_step_to_agent(main_step)
            
            for sub_step in sub_steps:
                sub_step["parent_step"] = main_step["step_id"]
                sub_step["assigned_agent"] = await self.assign_step_to_agent(sub_step)
                plan.agent_assignments[sub_step["step_id"]] = sub_step["assigned_agent"]
            
            plan.agent_assignments[main_step["step_id"]] = main_step["assigned_agent"]
        
        plan.steps = main_steps
        plan.estimated_duration = timedelta(seconds=len(main_steps) * 60)
        
        return plan
    
    async def analyze_task(self, task: Task) -> List[Dict[str, Any]]:
        """Analyze task and break it down into steps"""
        steps = []
        
        # Task type analysis
        task_type = task.metadata.get("task_type", "general")
        
        if task_type == "research":
            steps = [
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Identify research sources",
                    "type": "research",
                    "agent_type": "research",
                    "description": "Find relevant information sources"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Gather information",
                    "type": "research",
                    "agent_type": "research",
                    "description": "Collect information from sources"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Analyze findings",
                    "type": "analysis",
                    "agent_type": "planner",
                    "description": "Analyze and synthesize research findings"
                }
            ]
        
        elif task_type == "code_generation":
            steps = [
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Understand requirements",
                    "type": "analysis",
                    "agent_type": "planner",
                    "description": "Analyze coding requirements"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Generate code",
                    "type": "code",
                    "agent_type": "coder",
                    "description": "Generate code based on requirements"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Review code",
                    "type": "review",
                    "agent_type": "coder",
                    "description": "Review and validate generated code"
                }
            ]
        
        elif task_type == "data_processing":
            steps = [
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Load data",
                    "type": "data",
                    "agent_type": "memory",
                    "description": "Load and validate data"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Process data",
                    "type": "processing",
                    "agent_type": "coder",
                    "description": "Process and transform data"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Store results",
                    "type": "storage",
                    "agent_type": "memory",
                    "description": "Store processed results"
                }
            ]
        
        else:  # general task
            steps = [
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Analyze task",
                    "type": "analysis",
                    "agent_type": "planner",
                    "description": "Analyze task requirements"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Execute task",
                    "type": "execution",
                    "agent_type": "general",
                    "description": "Execute the main task"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Verify results",
                    "type": "verification",
                    "agent_type": "planner",
                    "description": "Verify and validate results"
                }
            ]
        
        return steps
    
    async def analyze_subtasks(self, step: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze a step and break it into subtasks"""
        subtasks = []
        
        # Simple subtask generation based on step type
        if step["type"] == "research":
            subtasks = [
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Search web",
                    "type": "search",
                    "agent_type": "research",
                    "description": "Search web for information"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Extract data",
                    "type": "extraction",
                    "agent_type": "research",
                    "description": "Extract relevant data"
                }
            ]
        
        elif step["type"] == "code":
            subtasks = [
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Design structure",
                    "type": "design",
                    "agent_type": "coder",
                    "description": "Design code structure"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Implement logic",
                    "type": "implementation",
                    "agent_type": "coder",
                    "description": "Implement core logic"
                },
                {
                    "step_id": str(uuid.uuid4()),
                    "name": "Add tests",
                    "type": "testing",
                    "agent_type": "coder",
                    "description": "Add unit tests"
                }
            ]
        
        return subtasks
    
    async def group_independent_steps(self, steps: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group steps that can be executed in parallel"""
        # Simple grouping based on agent type and dependencies
        groups = []
        current_group = []
        used_agent_types = set()
        
        for step in steps:
            if not step.get("dependencies") and step["agent_type"] not in used_agent_types:
                current_group.append(step)
                used_agent_types.add(step["agent_type"])
            else:
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    used_agent_types = set()
                current_group.append(step)
                used_agent_types.add(step["agent_type"])
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    async def assign_step_to_agent(self, step: Dict[str, Any]) -> str:
        """Assign a step to an appropriate agent"""
        agent_type = step["agent_type"]
        
        # Find available agent with required capabilities
        available_agents = [
            agent_id for agent_id, capabilities in self.agent_capabilities.items()
            if agent_type in capabilities or "general" in capabilities
        ]
        
        if available_agents:
            # Simple round-robin assignment
            return available_agents[0]
        else:
            # Fallback to default agent naming
            return f"{agent_type}-agent-1"
    
    async def execute_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Execute an execution plan"""
        plan.status = TaskStatus.IN_PROGRESS
        
        results = []
        
        for step in plan.steps:
            if step.get("dependencies"):
                # Wait for dependencies to complete
                await self.wait_for_dependencies(step["dependencies"])
            
            # Execute step
            result = await self.execute_step(step)
            results.append(result)
        
        plan.status = TaskStatus.COMPLETED
        
        return {
            "plan_id": plan.plan_id,
            "status": "completed",
            "results": results
        }
    
    async def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step"""
        assigned_agent = step.get("assigned_agent")
        
        if not assigned_agent:
            return {"error": "No agent assigned"}
        
        # Send task to assigned agent
        task_request = {
            "task_id": step["step_id"],
            "name": step["name"],
            "description": step["description"],
            "type": step["type"]
        }
        
        response = await self.send_task_request(
            assigned_agent,
            task_request,
            priority=5
        )
        
        return response or {"error": "No response from agent"}
    
    async def wait_for_dependencies(self, dependency_ids: List[str]) -> bool:
        """Wait for dependencies to complete"""
        # Simple implementation - in production, use proper dependency tracking
        await asyncio.sleep(1)
        return True
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task (main entry point)"""
        # Create task object
        task_obj = Task(
            name=task.get("name", ""),
            description=task.get("description", ""),
            priority=TaskPriority(task.get("priority", 3)),
            metadata=task.get("metadata", {})
        )
        
        # Plan the task
        plan = await self.plan_task(task_obj)
        
        # Execute the plan
        result = await self.execute_plan(plan)
        
        return result


async def main():
    """Main entry point for the planner agent"""
    agent = PlannerAgent()
    
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