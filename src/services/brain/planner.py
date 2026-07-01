"""
Planner - Strategic Planning Component
Implements multiple planning strategies for goal achievement
Local decision-making, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
from datetime import datetime, timedelta


class PlanningStrategy(Enum):
    """Different planning strategies"""
    REACTIVE = "reactive"  # Immediate response to stimuli
    DELIBERATIVE = "deliberative"  # Careful consideration of options
    HIERARCHICAL = "hierarchical"  # Top-down goal decomposition
    HYBRID = "hybrid"  # Combination of strategies


class Plan:
    """Represents a plan with steps"""
    def __init__(self, plan_id: str, goal: str, steps: List[Dict[str, Any]], 
                 strategy: PlanningStrategy, estimated_duration: float):
        self.plan_id = plan_id
        self.goal = goal
        self.steps = steps
        self.strategy = strategy
        self.estimated_duration = estimated_duration
        self.current_step = 0
        self.created_at = datetime.utcnow()
        self.status = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": self.steps,
            "strategy": self.strategy.value,
            "estimated_duration": self.estimated_duration,
            "current_step": self.current_step,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }


class Planner:
    """Main planner implementing multiple planning strategies"""
    
    def __init__(self):
        self.active_plans: Dict[str, Dict[str, Plan]] = {}  # character_id -> plan_id -> Plan
        self.plan_history: Dict[str, List[Plan]] = {}  # character_id -> List[Plan]
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize planner"""
        self.is_initialized = True
        print("Planner initialized")
    
    async def shutdown(self):
        """Shutdown planner"""
        self.is_initialized = False
        print("Planner shutdown")
    
    async def create_plan(
        self, 
        character_id: str, 
        goal: str, 
        context: Dict[str, Any],
        strategy: PlanningStrategy = PlanningStrategy.HYBRID
    ) -> Plan:
        """Create a plan to achieve a goal"""
        
        plan_id = str(uuid.uuid4())
        
        # Select planning strategy
        if strategy == PlanningStrategy.REACTIVE:
            steps = await self._reactive_planning(goal, context)
        elif strategy == PlanningStrategy.DELIBERATIVE:
            steps = await self._deliberative_planning(goal, context)
        elif strategy == PlanningStrategy.HIERARCHICAL:
            steps = await self._hierarchical_planning(goal, context)
        else:  # HYBRID
            steps = await self._hybrid_planning(goal, context)
        
        # Estimate duration
        duration = self._estimate_duration(steps)
        
        plan = Plan(plan_id, goal, steps, strategy, duration)
        
        # Store plan
        if character_id not in self.active_plans:
            self.active_plans[character_id] = {}
        
        self.active_plans[character_id][plan_id] = plan
        
        return plan
    
    async def _reactive_planning(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Reactive planning - immediate actions"""
        steps = []
        
        # Analyze goal type
        if "move" in goal.lower():
            steps = [
                {"action": "rotate_towards_target", "priority": 1.0},
                {"action": "calculate_path", "priority": 0.9},
                {"action": "move_to_target", "priority": 0.8}
            ]
        elif "interact" in goal.lower():
            steps = [
                {"action": "locate_object", "priority": 1.0},
                {"action": "approach_object", "priority": 0.9},
                {"action": "perform_interaction", "priority": 0.8}
            ]
        elif "speak" in goal.lower():
            steps = [
                {"action": "formulate_response", "priority": 1.0},
                {"action": "trigger_animation", "priority": 0.7},
                {"action": "speak", "priority": 0.9}
            ]
        else:
            steps = [
                {"action": "analyze_goal", "priority": 1.0},
                {"action": "execute_default_action", "priority": 0.8}
            ]
        
        return steps
    
    async def _deliberative_planning(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Deliberative planning - careful consideration"""
        steps = []
        
        # Step 1: Analyze goal and context
        steps.append({
            "action": "analyze_goal",
            "priority": 1.0,
            "description": "Analyze goal requirements and constraints"
        })
        
        # Step 2: Generate multiple options
        steps.append({
            "action": "generate_options",
            "priority": 0.9,
            "description": "Generate multiple approaches"
        })
        
        # Step 3: Evaluate options
        steps.append({
            "action": "evaluate_options",
            "priority": 0.85,
            "description": "Evaluate each option against criteria"
        })
        
        # Step 4: Select best option
        steps.append({
            "action": "select_option",
            "priority": 0.8,
            "description": "Select optimal approach"
        })
        
        # Step 5: Create detailed steps
        steps.append({
            "action": "create_detailed_steps",
            "priority": 0.75,
            "description": "Break down into detailed steps"
        })
        
        # Step 6: Execute
        steps.append({
            "action": "execute_plan",
            "priority": 0.7,
            "description": "Execute the plan"
        })
        
        return steps
    
    async def _hierarchical_planning(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Hierarchical planning - top-down decomposition"""
        steps = []
        
        # Level 1: High-level goal
        steps.append({
            "action": "set_high_level_goal",
            "priority": 1.0,
            "goal": goal,
            "level": 1
        })
        
        # Level 2: Decompose into sub-goals
        sub_goals = await self._decompose_goal(goal, context)
        for sub_goal in sub_goals:
            steps.append({
                "action": "set_sub_goal",
                "priority": 0.9,
                "goal": sub_goal,
                "level": 2
            })
        
        # Level 3: Break down into actions
        for sub_goal in sub_goals:
            actions = await self._get_actions_for_goal(sub_goal)
            for action in actions:
                steps.append({
                    "action": action,
                    "priority": 0.8,
                    "parent_goal": sub_goal,
                    "level": 3
                })
        
        return steps
    
    async def _hybrid_planning(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Hybrid planning - combination of strategies"""
        steps = []
        
        # Use reactive for urgent goals
        urgency = context.get("urgency", 0.5)
        
        if urgency > 0.7:
            # Reactive planning for urgent goals
            steps = await self._reactive_planning(goal, context)
        else:
            # Deliberative planning for non-urgent goals
            steps = await self._deliberative_planning(goal, context)
        
        return steps
    
    async def _decompose_goal(self, goal: str, context: Dict[str, Any]) -> List[str]:
        """Decompose high-level goal into sub-goals"""
        sub_goals = []
        
        # Goal decomposition logic
        if "move" in goal.lower():
            sub_goals = ["plan_path", "avoid_obstacles", "reach_destination"]
        elif "interact" in goal.lower():
            sub_goals = ["locate_target", "approach_target", "perform_interaction"]
        elif "communicate" in goal.lower():
            sub_goals = ["understand_message", "formulate_response", "deliver_response"]
        else:
            sub_goals = ["analyze", "plan", "execute"]
        
        return sub_goals
    
    async def _get_actions_for_goal(self, goal: str) -> List[str]:
        """Get actions for a specific goal"""
        actions = []
        
        goal_actions = {
            "plan_path": ["scan_environment", "calculate_path", "validate_path"],
            "avoid_obstacles": ["detect_obstacles", "calculate_avoidance", "adjust_path"],
            "reach_destination": ["move_towards", "check_arrival", "stop"],
            "locate_target": ["search_area", "identify_target", "confirm_location"],
            "approach_target": ["calculate_approach", "move_to_target", "maintain_distance"],
            "perform_interaction": ["prepare_interaction", "execute_interaction", "finalize"],
            "understand_message": ["parse_input", "extract_intent", "identify_entities"],
            "formulate_response": ["generate_content", "check_appropriateness", "format_output"],
            "deliver_response": ["trigger_animation", "speak", "monitor_feedback"]
        }
        
        actions = goal_actions.get(goal, ["execute_default"])
        
        return actions
    
    def _estimate_duration(self, steps: List[Dict[str, Any]]) -> float:
        """Estimate plan duration based on steps"""
        base_duration = len(steps) * 2.0  # 2 seconds per step
        return base_duration
    
    async def execute_step(self, character_id: str, plan_id: str) -> Optional[Dict[str, Any]]:
        """Execute next step in plan"""
        if character_id not in self.active_plans:
            return None
        
        if plan_id not in self.active_plans[character_id]:
            return None
        
        plan = self.active_plans[character_id][plan_id]
        
        if plan.current_step >= len(plan.steps):
            # Plan completed
            plan.status = "completed"
            await self._archive_plan(character_id, plan)
            return {"status": "completed", "plan_id": plan_id}
        
        step = plan.steps[plan.current_step]
        plan.current_step += 1
        
        return {
            "status": "executing",
            "step": step,
            "progress": plan.current_step / len(plan.steps)
        }
    
    async def _archive_plan(self, character_id: str, plan: Plan):
        """Archive completed plan"""
        if character_id not in self.plan_history:
            self.plan_history[character_id] = []
        
        self.plan_history[character_id].append(plan)
        
        # Remove from active plans
        del self.active_plans[character_id][plan.plan_id]
    
    async def cancel_plan(self, character_id: str, plan_id: str):
        """Cancel an active plan"""
        if character_id in self.active_plans and plan_id in self.active_plans[character_id]:
            plan = self.active_plans[character_id][plan_id]
            plan.status = "cancelled"
            await self._archive_plan(character_id, plan)
    
    def get_active_plans(self, character_id: str) -> List[Dict[str, Any]]:
        """Get all active plans for a character"""
        if character_id not in self.active_plans:
            return []
        
        return [plan.to_dict() for plan in self.active_plans[character_id].values()]
    
    def get_plan_history(self, character_id: str) -> List[Dict[str, Any]]:
        """Get plan history for a character"""
        if character_id not in self.plan_history:
            return []
        
        return [plan.to_dict() for plan in self.plan_history[character_id]]


import uuid