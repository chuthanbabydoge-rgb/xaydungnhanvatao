"""
Action Planner - Action Planning and Execution
Local action planning, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
import uuid


class Action:
    """Represents an action to be executed"""
    def __init__(
        self,
        action_id: str,
        action_type: str,
        parameters: Dict[str, Any],
        priority: float,
        duration: float
    ):
        self.action_id = action_id
        self.action_type = action_type
        self.parameters = parameters
        self.priority = priority
        self.duration = duration
        self.status = "pending"
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "parameters": self.parameters,
            "priority": self.priority,
            "duration": self.duration,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class ActionPlanner:
    """
    Action planner for converting decisions into executable actions
    Local action planning, not LLM-dependent
    """
    
    def __init__(self):
        self.decision_engine = None
        self.behavior_tree = None
        self.active_actions: Dict[str, List[Action]] = {}  # character_id -> List[Action]
        self.action_history: Dict[str, List[Action]] = {}  # character_id -> List[Action]
        self.is_initialized = False
    
    def set_decision_engine(self, decision_engine):
        """Set decision engine dependency"""
        self.decision_engine = decision_engine
    
    def set_behavior_tree(self, behavior_tree):
        """Set behavior tree dependency"""
        self.behavior_tree = behavior_tree
    
    async def initialize(self):
        """Initialize action planner"""
        self.is_initialized = True
        print("Action Planner initialized")
    
    async def shutdown(self):
        """Shutdown action planner"""
        self.is_initialized = False
        print("Action Planner shutdown")
    
    async def plan_actions(
        self,
        character_id: str,
        decision: Dict[str, Any],
        behavior_tree_state: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Plan actions based on decision
        Local action planning, not LLM-dependent
        """
        
        # Extract action from decision
        action_type = decision.get("action", "idle")
        
        # Generate action sequence
        action_sequence = await self._generate_action_sequence(
            character_id,
            action_type,
            decision,
            behavior_tree_state
        )
        
        # Add actions to active queue
        for action in action_sequence:
            await self._add_action(character_id, action)
        
        return [action.to_dict() for action in action_sequence]
    
    async def _generate_action_sequence(
        self,
        character_id: str,
        action_type: str,
        decision: Dict[str, Any],
        behavior_tree_state: Optional[Dict[str, Any]]
    ) -> List[Action]:
        """Generate a sequence of actions for the given action type"""
        
        actions = []
        
        # Action type definitions
        action_sequences = {
            "respond": [
                {"type": "turn_to_face", "duration": 0.5},
                {"type": "prepare_speech", "duration": 0.3},
                {"type": "speak", "duration": 2.0},
                {"type": "finish_speech", "duration": 0.2}
            ],
            "move": [
                {"type": "calculate_path", "duration": 0.5},
                {"type": "turn_to_direction", "duration": 0.3},
                {"type": "walk", "duration": 3.0},
                {"type": "stop", "duration": 0.2}
            ],
            "interact": [
                {"type": "locate_object", "duration": 0.5},
                {"type": "approach_object", "duration": 1.0},
                {"type": "prepare_interaction", "duration": 0.3},
                {"type": "perform_interaction", "duration": 1.5},
                {"type": "finish_interaction", "duration": 0.2}
            ],
            "observe": [
                {"type": "turn_to_target", "duration": 0.3},
                {"type": "scan_environment", "duration": 2.0},
                {"type": "process_visual_data", "duration": 0.5}
            ],
            "idle": [
                {"type": "relax", "duration": 1.0},
                {"type": "look_around", "duration": 2.0}
            ],
            "explore": [
                {"type": "select_destination", "duration": 0.5},
                {"type": "move_to_destination", "duration": 3.0},
                {"type": "observe_area", "duration": 2.0}
            ],
            "socialize": [
                {"type": "approach_entity", "duration": 1.0},
                {"type": "greet", "duration": 1.0},
                {"type": "engage_conversation", "duration": 3.0}
            ],
            "seek_safety": [
                {"type": "assess_threat", "duration": 0.5},
                {"type": "identify_safe_location", "duration": 0.5},
                {"type": "move_to_safety", "duration": 2.0},
                {"type": "alert_posture", "duration": 1.0}
            ]
        }
        
        # Get sequence for action type
        sequence = action_sequences.get(action_type, [{"type": "idle", "duration": 1.0}])
        
        # Create Action objects
        priority = decision.get("confidence", 0.5)
        
        for i, step in enumerate(sequence):
            action_id = str(uuid.uuid4())
            
            parameters = {
                "step_index": i,
                "total_steps": len(sequence),
                "animation": decision.get("animation"),
                "decision_id": decision.get("decision_id")
            }
            
            action = Action(
                action_id=action_id,
                action_type=step["type"],
                parameters=parameters,
                priority=priority,
                duration=step["duration"]
            )
            
            actions.append(action)
        
        return actions
    
    async def _add_action(self, character_id: str, action: Action):
        """Add an action to the active queue"""
        
        if character_id not in self.active_actions:
            self.active_actions[character_id] = []
        
        self.active_actions[character_id].append(action)
    
    async def execute_next_action(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Execute the next action in the queue"""
        
        if character_id not in self.active_actions:
            return None
        
        if not self.active_actions[character_id]:
            return None
        
        # Get next pending action
        action = None
        for a in self.active_actions[character_id]:
            if a.status == "pending":
                action = a
                break
        
        if not action:
            return None
        
        # Mark as started
        action.status = "executing"
        action.started_at = datetime.utcnow()
        
        return action.to_dict()
    
    async def complete_action(self, character_id: str, action_id: str):
        """Mark an action as completed"""
        
        if character_id not in self.active_actions:
            return
        
        for action in self.active_actions[character_id]:
            if action.action_id == action_id:
                action.status = "completed"
                action.completed_at = datetime.utcnow()
                
                # Move to history
                if character_id not in self.action_history:
                    self.action_history[character_id] = []
                
                self.action_history[character_id].append(action)
                
                # Remove from active
                self.active_actions[character_id].remove(action)
                break
    
    async def fail_action(self, character_id: str, action_id: str, reason: str):
        """Mark an action as failed"""
        
        if character_id not in self.active_actions:
            return
        
        for action in self.active_actions[character_id]:
            if action.action_id == action_id:
                action.status = "failed"
                action.completed_at = datetime.utcnow()
                action.parameters["failure_reason"] = reason
                
                # Move to history
                if character_id not in self.action_history:
                    self.action_history[character_id] = []
                
                self.action_history[character_id].append(action)
                
                # Remove from active
                self.active_actions[character_id].remove(action)
                break
    
    async def get_active_actions(self, character_id: str) -> List[Dict[str, Any]]:
        """Get active actions for a character"""
        
        if character_id not in self.active_actions:
            return []
        
        return [action.to_dict() for action in self.active_actions[character_id]]
    
    async def get_action_history(self, character_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get action history for a character"""
        
        if character_id not in self.action_history:
            return []
        
        history = self.action_history[character_id]
        history.sort(key=lambda a: a.completed_at or a.created_at, reverse=True)
        
        return [action.to_dict() for action in history[:limit]]
    
    async def cancel_all_actions(self, character_id: str):
        """Cancel all active actions for a character"""
        
        if character_id not in self.active_actions:
            return
        
        for action in self.active_actions[character_id]:
            if action.status == "pending":
                action.status = "cancelled"
                action.completed_at = datetime.utcnow()
                
                if character_id not in self.action_history:
                    self.action_history[character_id] = []
                
                self.action_history[character_id].append(action)
        
        self.active_actions[character_id] = []
    
    async def get_action_status(self, character_id: str, action_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific action"""
        
        # Check active actions
        if character_id in self.active_actions:
            for action in self.active_actions[character_id]:
                if action.action_id == action_id:
                    return action.to_dict()
        
        # Check action history
        if character_id in self.action_history:
            for action in self.action_history[character_id]:
                if action.action_id == action_id:
                    return action.to_dict()
        
        return None