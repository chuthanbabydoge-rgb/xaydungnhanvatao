"""
Goal System - Goal Management and Prioritization
Local goal management, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
from datetime import datetime, timedelta
import uuid


class GoalPriority(Enum):
    """Goal priority levels"""
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    MINIMAL = 0.2


class GoalStatus(Enum):
    """Goal status"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Goal:
    """Represents a goal"""
    def __init__(
        self,
        goal_id: str,
        description: str,
        priority: float,
        goal_type: str,
        deadline: Optional[datetime] = None,
        parent_goal_id: Optional[str] = None
    ):
        self.goal_id = goal_id
        self.description = description
        self.priority = priority
        self.goal_type = goal_type
        self.status = GoalStatus.ACTIVE
        self.created_at = datetime.utcnow()
        self.deadline = deadline
        self.parent_goal_id = parent_goal_id
        self.progress = 0.0
        self.sub_goals: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "priority": self.priority,
            "goal_type": self.goal_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "parent_goal_id": self.parent_goal_id,
            "progress": self.progress,
            "sub_goals": self.sub_goals,
            "metadata": self.metadata
        }


class GoalSystem:
    """Manages goals for AI characters"""
    
    def __init__(self):
        self.goals: Dict[str, Dict[str, Goal]] = {}  # character_id -> goal_id -> Goal
        self.goal_hierarchy: Dict[str, List[str]] = {}  # parent_goal_id -> child_goal_ids
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize goal system"""
        self.is_initialized = True
        print("Goal System initialized")
    
    async def shutdown(self):
        """Shutdown goal system"""
        self.is_initialized = False
        print("Goal System shutdown")
    
    async def add_goal(
        self,
        character_id: str,
        description: str,
        priority: float = 0.5,
        goal_type: str = "general",
        deadline: Optional[datetime] = None,
        parent_goal_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Goal:
        """Add a new goal"""
        
        goal_id = str(uuid.uuid4())
        
        goal = Goal(
            goal_id=goal_id,
            description=description,
            priority=priority,
            goal_type=goal_type,
            deadline=deadline,
            parent_goal_id=parent_goal_id
        )
        
        if metadata:
            goal.metadata = metadata
        
        # Store goal
        if character_id not in self.goals:
            self.goals[character_id] = {}
        
        self.goals[character_id][goal_id] = goal
        
        # Update hierarchy
        if parent_goal_id:
            if parent_goal_id not in self.goal_hierarchy:
                self.goal_hierarchy[parent_goal_id] = []
            self.goal_hierarchy[parent_goal_id].append(goal_id)
            
            # Add to parent's sub_goals
            for char_goals in self.goals.values():
                if parent_goal_id in char_goals:
                    char_goals[parent_goal_id].sub_goals.append(goal_id)
                    break
        
        return goal
    
    async def update_goals(
        self,
        character_id: str,
        stimulus: Any,
        emotions: Dict[str, float],
        reasoning_result: Optional[Any] = None
    ) -> List[Goal]:
        """Update goals based on current state"""
        
        if character_id not in self.goals:
            # Initialize with default goals
            await self._initialize_default_goals(character_id)
        
        # Update existing goals
        await self._update_goal_progress(character_id)
        
        # Check for goal completion
        await self._check_goal_completion(character_id)
        
        # Generate new goals based on stimulus
        new_goals = await self._generate_goals_from_stimulus(
            character_id,
            stimulus,
            emotions,
            reasoning_result
        )
        
        # Re-prioritize goals
        await self._reprioritize_goals(character_id, emotions)
        
        # Return active goals
        return await self.get_active_goals(character_id)
    
    async def _initialize_default_goals(self, character_id: str):
        """Initialize default goals for a character"""
        
        default_goals = [
            {
                "description": "Maintain social interaction",
                "priority": 0.7,
                "goal_type": "social",
                "metadata": {"ongoing": True}
            },
            {
                "description": "Stay safe and avoid danger",
                "priority": 0.9,
                "goal_type": "safety",
                "metadata": {"ongoing": True}
            },
            {
                "description": "Learn about the environment",
                "priority": 0.5,
                "goal_type": "exploration",
                "metadata": {"ongoing": True}
            }
        ]
        
        for goal_data in default_goals:
            await self.add_goal(
                character_id=character_id,
                description=goal_data["description"],
                priority=goal_data["priority"],
                goal_type=goal_data["goal_type"],
                metadata=goal_data["metadata"]
            )
    
    async def _update_goal_progress(self, character_id: str):
        """Update progress for active goals"""
        if character_id not in self.goals:
            return
        
        for goal in self.goals[character_id].values():
            if goal.status == GoalStatus.ACTIVE:
                # Update progress based on goal type
                if goal.metadata.get("ongoing"):
                    # Ongoing goals maintain baseline progress
                    goal.progress = min(goal.progress + 0.01, 0.95)
                else:
                    # Time-based progress
                    if goal.deadline:
                        time_elapsed = (datetime.utcnow() - goal.created_at).total_seconds()
                        total_time = (goal.deadline - goal.created_at).total_seconds()
                        goal.progress = min(time_elapsed / total_time, 1.0)
    
    async def _check_goal_completion(self, character_id: str):
        """Check if goals are completed"""
        if character_id not in self.goals:
            return
        
        for goal in list(self.goals[character_id].values()):
            if goal.status == GoalStatus.ACTIVE:
                # Check completion conditions
                if goal.progress >= 1.0:
                    goal.status = GoalStatus.COMPLETED
                    print(f"Goal completed: {goal.description}")
                
                # Check deadline
                if goal.deadline and datetime.utcnow() > goal.deadline:
                    if goal.progress < 0.8:
                        goal.status = GoalStatus.FAILED
                        print(f"Goal failed (deadline): {goal.description}")
    
    async def _generate_goals_from_stimulus(
        self,
        character_id: str,
        stimulus: Any,
        emotions: Dict[str, float],
        reasoning_result: Optional[Any] = None
    ):
        """Generate new goals based on stimulus"""
        
        new_goals = []
        
        # Analyze stimulus for goal opportunities
        if hasattr(stimulus, 'content'):
            content = str(stimulus.content)
            
            # Check for requests in text
            if "help" in content.lower():
                new_goals.append({
                    "description": "Help the user",
                    "priority": 0.8,
                    "goal_type": "assistance"
                })
            
            if "move" in content.lower() or "go" in content.lower():
                new_goals.append({
                    "description": "Move to requested location",
                    "priority": 0.7,
                    "goal_type": "movement"
                })
            
            if "tell" in content.lower() or "explain" in content.lower():
                new_goals.append({
                    "description": "Provide information",
                    "priority": 0.6,
                    "goal_type": "communication"
                })
        
        # Generate goals based on emotions
        if emotions.get("curiosity", 0) > 0.7:
            new_goals.append({
                "description": "Satisfy curiosity",
                "priority": 0.6,
                "goal_type": "exploration"
            })
        
        if emotions.get("fear", 0) > 0.6:
            new_goals.append({
                "description": "Ensure safety",
                "priority": 0.9,
                "goal_type": "safety"
            })
        
        # Add generated goals
        for goal_data in new_goals:
            # Check if similar goal already exists
            if not await self._has_similar_goal(character_id, goal_data["description"]):
                await self.add_goal(
                    character_id=character_id,
                    **goal_data
                )
    
    async def _has_similar_goal(self, character_id: str, description: str) -> bool:
        """Check if similar goal already exists"""
        if character_id not in self.goals:
            return False
        
        for goal in self.goals[character_id].values():
            if goal.status == GoalStatus.ACTIVE:
                # Simple similarity check
                if description.lower() in goal.description.lower() or \
                   goal.description.lower() in description.lower():
                    return True
        
        return False
    
    async def _reprioritize_goals(self, character_id: str, emotions: Dict[str, float]):
        """Re-prioritize goals based on current state"""
        if character_id not in self.goals:
            return
        
        for goal in self.goals[character_id].values():
            if goal.status == GoalStatus.ACTIVE:
                # Adjust priority based on emotions
                if goal.goal_type == "safety" and emotions.get("fear", 0) > 0.5:
                    goal.priority = min(goal.priority + 0.2, 1.0)
                
                if goal.goal_type == "social" and emotions.get("happiness", 0) > 0.7:
                    goal.priority = min(goal.priority + 0.1, 1.0)
                
                # Adjust based on deadline proximity
                if goal.deadline:
                    time_remaining = (goal.deadline - datetime.utcnow()).total_seconds()
                    if time_remaining < 300:  # Less than 5 minutes
                        goal.priority = min(goal.priority + 0.3, 1.0)
    
    async def complete_goal(self, character_id: str, goal_id: str):
        """Mark a goal as completed"""
        if character_id in self.goals and goal_id in self.goals[character_id]:
            self.goals[character_id][goal_id].status = GoalStatus.COMPLETED
            self.goals[character_id][goal_id].progress = 1.0
    
    async def fail_goal(self, character_id: str, goal_id: str):
        """Mark a goal as failed"""
        if character_id in self.goals and goal_id in self.goals[character_id]:
            self.goals[character_id][goal_id].status = GoalStatus.FAILED
    
    async def cancel_goal(self, character_id: str, goal_id: str):
        """Cancel a goal"""
        if character_id in self.goals and goal_id in self.goals[character_id]:
            self.goals[character_id][goal_id].status = GoalStatus.CANCELLED
    
    async def get_active_goals(self, character_id: str) -> List[Goal]:
        """Get all active goals for a character"""
        if character_id not in self.goals:
            return []
        
        return [
            goal for goal in self.goals[character_id].values()
            if goal.status == GoalStatus.ACTIVE
        ]
    
    async def get_all_goals(self, character_id: str) -> List[Goal]:
        """Get all goals for a character"""
        if character_id not in self.goals:
            return []
        
        return list(self.goals[character_id].values())
    
    async def get_goal_by_id(self, character_id: str, goal_id: str) -> Optional[Goal]:
        """Get a specific goal"""
        if character_id in self.goals and goal_id in self.goals[character_id]:
            return self.goals[character_id][goal_id]
        return None
    
    async def update_goal_progress(self, character_id: str, goal_id: str, progress: float):
        """Update progress for a specific goal"""
        if character_id in self.goals and goal_id in self.goals[character_id]:
            self.goals[character_id][goal_id].progress = max(0.0, min(progress, 1.0))
    
    def get_goal_hierarchy(self, character_id: str) -> Dict[str, List[str]]:
        """Get goal hierarchy for a character"""
        return self.goal_hierarchy