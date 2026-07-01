"""
Motivation Engine - Need detection, goal generation, priority scoring, and action planning
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import logging
import uuid

from shared.database.mongodb import get_mongodb
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Motivation Service",
    description="Need detection, goal generation, priority scoring, and action planning for AI Companion",
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
class NeedType(str, Enum):
    """Need types"""
    PHYSIOLOGICAL = "physiological"
    SOCIAL = "social"
    TASK = "task"
    LEARNING = "learning"


class DetectedNeed(BaseModel):
    """Detected need model"""
    need_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID")
    type: NeedType = Field(..., description="Need type")
    name: str = Field(..., description="Need name")
    description: str = Field(..., description="Need description")
    urgency: float = Field(..., description="Urgency score (0-1)")
    priority: float = Field(..., description="Priority score (0-1)")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class NeedObservation(BaseModel):
    """Need observation request"""
    user_id: str = Field(..., description="User ID")
    observation_type: str = Field(..., description="Type of observation: work_duration, tiredness, social_interaction")
    value: float = Field(..., description="Observed value")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class GoalType(str, Enum):
    """Goal types"""
    ASSISTANCE = "assistance"
    SOCIAL_INTERACTION = "social_interaction"
    REMINDER = "reminder"
    INFORMATION_PROVISION = "information_provision"
    TASK_EXECUTION = "task_execution"


class GoalPriority(str, Enum):
    """Goal priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GoalStatus(str, Enum):
    """Goal status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Goal(BaseModel):
    """Goal model"""
    goal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID")
    type: GoalType = Field(..., description="Goal type")
    name: str = Field(..., description="Goal name")
    description: str = Field(..., description="Goal description")
    need_id: Optional[str] = Field(default=None, description="Related need ID")
    priority: GoalPriority = Field(default=GoalPriority.MEDIUM, description="Goal priority")
    deadline: Optional[str] = Field(default=None, description="Goal deadline")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Goal parameters")
    status: GoalStatus = Field(default=GoalStatus.PENDING, description="Goal status")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ActionPlan(BaseModel):
    """Action plan model"""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str = Field(..., description="Related goal ID")
    steps: List[Dict[str, Any]] = Field(..., description="Action steps")
    estimated_duration: float = Field(..., description="Estimated duration in seconds")
    dependencies: List[str] = Field(default_factory=list, description="Dependent goal IDs")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Need detection system
class NeedDetectionSystem:
    """Detects user needs from observations"""
    
    def __init__(self):
        self.physiological_thresholds = {
            "water": 0.7,
            "food": 0.6,
            "rest": 0.8,
            "exercise": 0.5
        }
        
        self.social_thresholds = {
            "attention": 0.6,
            "companionship": 0.5,
            "affirmation": 0.4
        }
        
        self.task_thresholds = {
            "reminder": 0.5,
            "assistance": 0.6,
            "information": 0.4
        }
        
        self.learning_thresholds = {
            "new_knowledge": 0.3,
            "skill_improvement": 0.4,
            "exploration": 0.5
        }
    
    async def observe_and_detect(self, user_id: str, observation: NeedObservation) -> List[DetectedNeed]:
        """Observe user and detect needs"""
        detected_needs = []
        
        if observation.observation_type == "work_duration":
            # Check for water/rest needs
            if observation.value > 6.0:  # More than 6 hours
                detected_needs.append(DetectedNeed(
                    user_id=user_id,
                    type=NeedType.PHYSIOLOGICAL,
                    name="water",
                    description="User has been working for a long time without water",
                    urgency=0.7,
                    priority=0.6
                ))
            
            if observation.value > 8.0:  # More than 8 hours
                detected_needs.append(DetectedNeed(
                    user_id=user_id,
                    type=NeedType.PHYSIOLOGICAL,
                    name="rest",
                    description="User has been working for a very long time",
                    urgency=0.8,
                    priority=0.7
                ))
        
        elif observation.observation_type == "tiredness":
            # Check for rest need
            if observation.value > 0.7:
                detected_needs.append(DetectedNeed(
                    user_id=user_id,
                    type=NeedType.PHYSIOLOGICAL,
                    name="rest",
                    description="User appears tired",
                    urgency=observation.value,
                    priority=0.8
                ))
        
        elif observation.observation_type == "social_interaction":
            # Check for social needs
            if observation.value < 0.3:  # Low social interaction
                detected_needs.append(DetectedNeed(
                    user_id=user_id,
                    type=NeedType.SOCIAL,
                    name="companionship",
                    description="User has low social interaction",
                    urgency=0.6,
                    priority=0.5
                ))
        
        # Store detected needs
        for need in detected_needs:
            await self._store_need(need)
        
        return detected_needs
    
    async def _store_need(self, need: DetectedNeed):
        """Store detected need in database"""
        db = await get_mongodb()
        needs = db["detected_needs"]
        
        await needs.insert_one(need.dict())
    
    async def get_active_needs(self, user_id: str) -> List[DetectedNeed]:
        """Get active needs for a user"""
        db = await get_mongodb()
        needs = db["detected_needs"]
        
        cursor = needs.find({"user_id": user_id}) \
            .sort("timestamp", -1) \
            .limit(20)
        
        result = []
        async for need in cursor:
            need.pop("_id", None)
            result.append(DetectedNeed(**need))
        
        return result


# Goal generation system
class GoalGenerationSystem:
    """Generates goals from detected needs"""
    
    def __init__(self):
        self.goal_templates = {
            NeedType.PHYSIOLOGICAL: {
                "water": {
                    "type": GoalType.ASSISTANCE,
                    "name": "Encourage hydration",
                    "description": "Encourage user to drink water",
                    "default_priority": GoalPriority.HIGH
                },
                "food": {
                    "type": GoalType.ASSISTANCE,
                    "name": "Encourage eating",
                    "description": "Encourage user to eat",
                    "default_priority": GoalPriority.HIGH
                },
                "rest": {
                    "type": GoalType.ASSISTANCE,
                    "name": "Encourage rest",
                    "description": "Encourage user to take a break",
                    "default_priority": GoalPriority.HIGH
                },
                "exercise": {
                    "type": GoalType.ASSISTANCE,
                    "name": "Encourage exercise",
                    "description": "Encourage user to exercise",
                    "default_priority": GoalPriority.MEDIUM
                }
            },
            NeedType.SOCIAL: {
                "attention": {
                    "type": GoalType.SOCIAL_INTERACTION,
                    "name": "Provide attention",
                    "description": "Engage user in conversation",
                    "default_priority": GoalPriority.MEDIUM
                },
                "companionship": {
                    "type": GoalType.SOCIAL_INTERACTION,
                    "name": "Provide companionship",
                    "description": "Be present and supportive",
                    "default_priority": GoalPriority.MEDIUM
                },
                "affirmation": {
                    "type": GoalType.SOCIAL_INTERACTION,
                    "name": "Provide affirmation",
                    "description": "Offer encouragement and support",
                    "default_priority": GoalPriority.MEDIUM
                }
            },
            NeedType.TASK: {
                "reminder": {
                    "type": GoalType.REMINDER,
                    "name": "Provide reminder",
                    "description": "Remind user of scheduled task",
                    "default_priority": GoalPriority.MEDIUM
                },
                "assistance": {
                    "type": GoalType.ASSISTANCE,
                    "name": "Provide assistance",
                    "description": "Help user with task",
                    "default_priority": GoalPriority.HIGH
                },
                "information": {
                    "type": GoalType.INFORMATION_PROVISION,
                    "name": "Provide information",
                    "description": "Share relevant information",
                    "default_priority": GoalPriority.LOW
                }
            },
            NeedType.LEARNING: {
                "new_knowledge": {
                    "type": GoalType.INFORMATION_PROVISION,
                    "name": "Share knowledge",
                    "description": "Share interesting information",
                    "default_priority": GoalPriority.LOW
                },
                "skill_improvement": {
                    "type": GoalType.ASSISTANCE,
                    "name": "Support skill development",
                    "description": "Help user improve skills",
                    "default_priority": GoalPriority.MEDIUM
                },
                "exploration": {
                    "type": GoalType.SOCIAL_INTERACTION,
                    "name": "Encourage exploration",
                    "description": "Encourage user to explore new topics",
                    "default_priority": GoalPriority.LOW
                }
            }
        }
    
    async def generate_goal(self, need: DetectedNeed) -> Optional[Goal]:
        """Generate a goal from a detected need"""
        templates = self.goal_templates.get(need.type, {})
        template = templates.get(need.name)
        
        if not template:
            return None
        
        # Calculate priority based on urgency
        if need.urgency > 0.8:
            priority = GoalPriority.CRITICAL
        elif need.urgency > 0.6:
            priority = GoalPriority.HIGH
        elif need.urgency > 0.4:
            priority = GoalPriority.MEDIUM
        else:
            priority = GoalPriority.LOW
        
        # Calculate deadline
        from datetime import timedelta
        if priority == GoalPriority.CRITICAL:
            deadline = datetime.utcnow() + timedelta(minutes=5)
        elif priority == GoalPriority.HIGH:
            deadline = datetime.utcnow() + timedelta(minutes=15)
        elif priority == GoalPriority.MEDIUM:
            deadline = datetime.utcnow() + timedelta(hours=1)
        else:
            deadline = datetime.utcnow() + timedelta(hours=3)
        
        goal = Goal(
            user_id=need.user_id,
            type=template["type"],
            name=template["name"],
            description=template["description"],
            need_id=need.need_id,
            priority=priority,
            deadline=deadline.isoformat(),
            parameters={
                "urgency": need.urgency,
                "context": need.description
            }
        )
        
        # Store goal
        await self._store_goal(goal)
        
        return goal
    
    async def _store_goal(self, goal: Goal):
        """Store goal in database"""
        db = await get_mongodb()
        goals = db["goals"]
        
        await goals.insert_one(goal.dict())
    
    async def get_active_goals(self, user_id: str) -> List[Goal]:
        """Get active goals for a user"""
        db = await get_mongodb()
        goals = db["goals"]
        
        cursor = goals.find({
            "user_id": user_id,
            "status": {"$in": [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]}
        }).sort("priority", -1)
        
        result = []
        async for goal in cursor:
            goal.pop("_id", None)
            result.append(Goal(**goal))
        
        return result
    
    async def update_goal_status(self, goal_id: str, status: GoalStatus) -> bool:
        """Update goal status"""
        db = await get_mongodb()
        goals = db["goals"]
        
        result = await goals.update_one(
            {"goal_id": goal_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        return result.modified_count > 0


# Priority scoring system
class PriorityScoringSystem:
    """Scores goals based on multiple factors"""
    
    def score_goal(self, goal: Goal, context: Optional[Dict[str, Any]] = None) -> float:
        """Score a goal based on multiple factors"""
        score = 0.0
        
        # Base priority score
        priority_scores = {
            GoalPriority.CRITICAL: 1.0,
            GoalPriority.HIGH: 0.8,
            GoalPriority.MEDIUM: 0.5,
            GoalPriority.LOW: 0.3
        }
        score += priority_scores.get(goal.priority, 0.5)
        
        # Urgency factor
        urgency = goal.parameters.get("urgency", 0.5)
        score += urgency * 0.3
        
        # Deadline proximity factor
        if goal.deadline:
            deadline = datetime.fromisoformat(goal.deadline)
            time_until_deadline = (deadline - datetime.utcnow()).total_seconds()
            
            if time_until_deadline < 300:  # Less than 5 minutes
                score += 0.2
            elif time_until_deadline < 3600:  # Less than 1 hour
                score += 0.1
        
        # Context factors
        if context:
            user_energy = context.get("user_energy", 0.5)
            if user_energy < 0.3 and goal.type == GoalType.ASSISTANCE:
                score += 0.1  # Boost assistance goals when user is low energy
        
        return min(score, 1.0)


# Action planning system
class ActionPlanningSystem:
    """Plans actions to achieve goals"""
    
    def __init__(self):
        self.action_templates = {
            GoalType.ASSISTANCE: [
                {"action": "assess_situation", "description": "Assess current situation"},
                {"action": "offer_help", "description": "Offer help to user"},
                {"action": "execute_assistance", "description": "Execute the assistance"}
            ],
            GoalType.SOCIAL_INTERACTION: [
                {"action": "initiate_conversation", "description": "Start conversation"},
                {"action": "maintain_engagement", "description": "Keep conversation going"},
                {"action": "provide_emotional_support", "description": "Offer emotional support"}
            ],
            GoalType.REMINDER: [
                {"action": "check_schedule", "description": "Check user's schedule"},
                {"action": "deliver_reminder", "description": "Deliver the reminder"},
                {"action": "confirm_acknowledgment", "description": "Confirm user acknowledged"}
            ],
            GoalType.INFORMATION_PROVISION: [
                {"action": "retrieve_information", "description": "Retrieve relevant information"},
                {"action": "present_information", "description": "Present information to user"},
                {"action": "answer_questions", "description": "Answer follow-up questions"}
            ],
            GoalType.TASK_EXECUTION: [
                {"action": "understand_task", "description": "Understand the task"},
                {"action": "plan_execution", "description": "Plan how to execute"},
                {"action": "execute_task", "description": "Execute the task"},
                {"action": "report_results", "description": "Report results to user"}
            ]
        }
    
    def create_action_plan(self, goal: Goal) -> ActionPlan:
        """Create an action plan for a goal"""
        template = self.action_templates.get(goal.type, [])
        
        steps = []
        for i, step_template in enumerate(template):
            step = {
                "step_id": f"step_{i}",
                "action": step_template["action"],
                "description": step_template["description"],
                "status": "pending",
                "estimated_duration": 30  # Default 30 seconds per step
            }
            steps.append(step)
        
        # Calculate total duration
        total_duration = sum(step["estimated_duration"] for step in steps)
        
        plan = ActionPlan(
            goal_id=goal.goal_id,
            steps=steps,
            estimated_duration=total_duration
        )
        
        return plan
    
    async def store_action_plan(self, plan: ActionPlan):
        """Store action plan in database"""
        db = await get_mongodb()
        action_plans = db["action_plans"]
        
        await action_plans.insert_one(plan.dict())


# Global instances
need_detection = NeedDetectionSystem()
goal_generation = GoalGenerationSystem()
priority_scoring = PriorityScoringSystem()
action_planning = ActionPlanningSystem()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Motivation Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Motivation Service")


# API endpoints
@app.post("/api/v1/motivation/observe")
async def observe_needs(request: NeedObservation):
    """
    Observe user and detect needs
    """
    try:
        detected_needs = await need_detection.observe_and_detect(
            request.user_id,
            request
        )
        
        logger.info(f"Detected {len(detected_needs)} needs for user {request.user_id}")
        
        return {
            "user_id": request.user_id,
            "needs_detected": [need.dict() for need in detected_needs],
            "count": len(detected_needs)
        }
        
    except Exception as e:
        logger.error(f"Failed to observe needs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to observe needs: {str(e)}"
        )


@app.get("/api/v1/motivation/needs/{user_id}")
async def get_needs(user_id: str):
    """
    Get active needs for a user
    """
    try:
        needs = await need_detection.get_active_needs(user_id)
        
        return {
            "user_id": user_id,
            "needs": [need.dict() for need in needs],
            "count": len(needs)
        }
        
    except Exception as e:
        logger.error(f"Failed to get needs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get needs: {str(e)}"
        )


@app.post("/api/v1/motivation/goals/generate")
async def generate_goal(need_id: str):
    """
    Generate a goal from a detected need
    """
    try:
        db = await get_mongodb()
        needs = db["detected_needs"]
        
        need_doc = await needs.find_one({"need_id": need_id})
        if not need_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Need {need_id} not found"
            )
        
        need_doc.pop("_id", None)
        need = DetectedNeed(**need_doc)
        
        goal = await goal_generation.generate_goal(need)
        
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not generate goal from this need"
            )
        
        logger.info(f"Generated goal {goal.goal_id} from need {need_id}")
        
        return goal.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate goal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate goal: {str(e)}"
        )


@app.get("/api/v1/motivation/goals/{user_id}")
async def get_goals(user_id: str):
    """
    Get active goals for a user
    """
    try:
        goals = await goal_generation.get_active_goals(user_id)
        
        return {
            "user_id": user_id,
            "goals": [goal.dict() for goal in goals],
            "count": len(goals)
        }
        
    except Exception as e:
        logger.error(f"Failed to get goals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get goals: {str(e)}"
        )


@app.put("/api/v1/motivation/goals/{goal_id}/status")
async def update_goal_status(goal_id: str, status: GoalStatus):
    """
    Update goal status
    """
    try:
        success = await goal_generation.update_goal_status(goal_id, status)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal {goal_id} not found"
            )
        
        logger.info(f"Updated goal {goal_id} status to {status}")
        
        return {
            "goal_id": goal_id,
            "status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update goal status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update goal status: {str(e)}"
        )


@app.post("/api/v1/motivation/plans/create")
async def create_action_plan(goal_id: str):
    """
    Create an action plan for a goal
    """
    try:
        db = await get_mongodb()
        goals = db["goals"]
        
        goal_doc = await goals.find_one({"goal_id": goal_id})
        if not goal_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal {goal_id} not found"
            )
        
        goal_doc.pop("_id", None)
        goal = Goal(**goal_doc)
        
        plan = action_planning.create_action_plan(goal)
        await action_planning.store_action_plan(plan)
        
        logger.info(f"Created action plan {plan.plan_id} for goal {goal_id}")
        
        return plan.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create action plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create action plan: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "motivation-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)

