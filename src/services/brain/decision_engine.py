"""
Decision Engine - Local Decision Making
Local decision algorithms, NOT LLM-dependent
LLM is only used for language reasoning, not decisions
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
import random
import math
from datetime import datetime


class DecisionStrategy(Enum):
    """Decision-making strategies"""
    UTILITARIAN = "utilitarian"  # Maximize overall utility
    DEONTOLOGICAL = "deontological"  # Follow rules/duties
    VIRTUE_ETHICS = "virtue_ethics"  # Based on character virtues
    CARE_ETHICS = "care_ethics"  # Focus on relationships
    HYBRID = "hybrid"  # Combination of strategies


class Decision:
    """Represents a decision"""
    def __init__(
        self,
        decision_id: str,
        action: str,
        confidence: float,
        reasoning: List[str],
        alternatives: List[Dict[str, Any]]
    ):
        self.decision_id = decision_id
        self.action = action
        self.confidence = confidence
        self.reasoning = reasoning
        self.alternatives = alternatives
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "action": self.action,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "timestamp": self.timestamp.isoformat()
        }


class DecisionEngine:
    """
    Decision engine for local decision making
    All decisions are made locally, LLM is NOT used for decision making
    """
    
    def __init__(self):
        self.goal_system = None
        self.need_system = None
        self.personality = None
        self.emotion_fusion = None
        self.social_system = None
        self.decision_history: Dict[str, List[Decision]] = {}  # character_id -> List[Decision]
        self.is_initialized = False
    
    def set_goal_system(self, goal_system):
        """Set goal system dependency"""
        self.goal_system = goal_system
    
    def set_need_system(self, need_system):
        """Set need system dependency"""
        self.need_system = need_system
    
    def set_personality(self, personality):
        """Set personality engine dependency"""
        self.personality = personality
    
    def set_emotion_fusion(self, emotion_fusion):
        """Set emotion fusion dependency"""
        self.emotion_fusion = emotion_fusion
    
    def set_social_system(self, social_system):
        """Set social system dependency"""
        self.social_system = social_system
    
    async def initialize(self):
        """Initialize decision engine"""
        self.is_initialized = True
        print("Decision Engine initialized")
    
    async def shutdown(self):
        """Shutdown decision engine"""
        self.is_initialized = False
        print("Decision Engine shutdown")
    
    async def make_decision(
        self,
        character_id: str,
        stimulus: Any,
        emotions: Dict[str, float],
        goals: List[Any],
        memories: List[Dict[str, Any]],
        personality: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make a decision using local algorithms
        This is completely independent of LLM
        """
        
        import uuid
        from datetime import datetime
        
        # Step 1: Generate action options
        action_options = await self._generate_action_options(
            character_id,
            stimulus,
            emotions,
            goals
        )
        
        # Step 2: Score each option using multiple factors
        scored_options = []
        for option in action_options:
            score = await self._score_action_option(
                character_id,
                option,
                emotions,
                goals,
                memories,
                personality
            )
            scored_options.append((option, score))
        
        # Step 3: Select best option
        scored_options.sort(key=lambda x: x[1], reverse=True)
        best_option, best_score = scored_options[0] if scored_options else ({"action": "idle"}, 0.5)
        
        # Step 4: Generate reasoning
        reasoning = await self._generate_reasoning(
            character_id,
            best_option,
            scored_options,
            emotions,
            goals
        )
        
        # Step 5: Create decision
        decision = {
            "action": best_option.get("action", "idle"),
            "confidence": best_score,
            "reasoning": reasoning,
            "alternatives": [opt for opt, score in scored_options[1:4]],
            "animation": best_option.get("animation"),
            "decision_id": str(uuid.uuid4())
        }
        
        # Store in history
        if character_id not in self.decision_history:
            self.decision_history[character_id] = []
        
        self.decision_history[character_id].append(
            Decision(
                decision_id=decision["decision_id"],
                action=decision["action"],
                confidence=decision["confidence"],
                reasoning=decision["reasoning"],
                alternatives=decision["alternatives"]
            )
        )
        
        return decision
    
    async def _generate_action_options(
        self,
        character_id: str,
        stimulus: Any,
        emotions: Dict[str, float],
        goals: List[Any]
    ) -> List[Dict[str, Any]]:
        """Generate possible action options"""
        
        options = []
        
        # Analyze stimulus type
        stimulus_type = getattr(stimulus, 'stimulus_type', 'unknown')
        stimulus_content = str(getattr(stimulus, 'content', ''))
        
        # Generate options based on stimulus
        if stimulus_type in ["text", "voice"]:
            # Communication stimulus
            options.extend([
                {"action": "respond", "animation": "talking", "priority": 0.8},
                {"action": "acknowledge", "animation": "nod", "priority": 0.6},
                {"action": "ask_question", "animation": "curious", "priority": 0.5}
            ])
            
            # Check for specific intents
            if "help" in stimulus_content.lower():
                options.append({"action": "offer_help", "animation": "helpful", "priority": 0.9})
            if "move" in stimulus_content.lower() or "go" in stimulus_content.lower():
                options.append({"action": "move", "animation": "walking", "priority": 0.8})
        
        elif stimulus_type == "vision":
            # Visual stimulus
            options.extend([
                {"action": "observe", "animation": "looking", "priority": 0.7},
                {"action": "approach", "animation": "walking", "priority": 0.6},
                {"action": "avoid", "animation": "retreating", "priority": 0.4}
            ])
        
        else:
            # Default options
            options.extend([
                {"action": "idle", "animation": "idle", "priority": 0.5},
                {"action": "look_around", "animation": "scanning", "priority": 0.4},
                {"action": "wait", "animation": "waiting", "priority": 0.3}
            ])
        
        # Add goal-driven options
        for goal in goals[:3]:  # Limit to top 3 goals
            goal_action = self._goal_to_action(goal.description)
            if goal_action:
                options.append({
                    "action": goal_action,
                    "animation": self._action_to_animation(goal_action),
                    "priority": goal.priority,
                    "goal_id": goal.goal_id
                })
        
        # Add need-driven options
        if self.need_system:
            urgent_need = await self.need_system.get_most_urgent_need(character_id)
            if urgent_need:
                need_action = self._need_to_action(urgent_need.name)
                if need_action:
                    options.append({
                        "action": need_action,
                        "animation": self._action_to_animation(need_action),
                        "priority": urgent_need.calculate_urgency(),
                        "need_type": urgent_need.need_type.value
                    })
        
        return options
    
    def _goal_to_action(self, goal_description: str) -> Optional[str]:
        """Convert goal description to action"""
        goal_lower = goal_description.lower()
        
        if "move" in goal_lower or "go" in goal_lower:
            return "move"
        elif "interact" in goal_lower or "help" in goal_lower:
            return "interact"
        elif "speak" in goal_lower or "communicate" in goal_lower:
            return "respond"
        elif "learn" in goal_lower or "explore" in goal_lower:
            return "explore"
        elif "safe" in goal_lower:
            return "seek_safety"
        
        return None
    
    def _need_to_action(self, need_name: str) -> Optional[str]:
        """Convert need to action"""
        need_actions = {
            "energy": "rest",
            "comfort": "seek_comfort",
            "security": "seek_safety",
            "stability": "maintain_stability",
            "belonging": "socialize",
            "affection": "seek_affection",
            "respect": "achieve",
            "achievement": "achieve",
            "growth": "learn",
            "purpose": "engage_in_meaningful_activity"
        }
        
        return need_actions.get(need_name)
    
    def _action_to_animation(self, action: str) -> str:
        """Convert action to animation"""
        animation_map = {
            "respond": "talking",
            "acknowledge": "nod",
            "ask_question": "curious",
            "move": "walking",
            "interact": "interacting",
            "observe": "looking",
            "approach": "walking",
            "avoid": "retreating",
            "idle": "idle",
            "look_around": "scanning",
            "wait": "waiting",
            "rest": "sitting",
            "seek_comfort": "relaxing",
            "seek_safety": "alert",
            "maintain_stability": "calm",
            "socialize": "social",
            "seek_affection": "friendly",
            "achieve": "proud",
            "learn": "thinking",
            "engage_in_meaningful_activity": "focused",
            "offer_help": "helpful"
        }
        
        return animation_map.get(action, "idle")
    
    async def _score_action_option(
        self,
        character_id: str,
        option: Dict[str, Any],
        emotions: Dict[str, float],
        goals: List[Any],
        memories: List[Dict[str, Any]],
        personality: Dict[str, Any]
    ) -> float:
        """Score an action option using multiple factors"""
        
        score = 0.0
        
        # Factor 1: Priority (from option or default)
        priority = option.get("priority", 0.5)
        score += priority * 0.3
        
        # Factor 2: Emotional alignment
        emotional_score = await self._calculate_emotional_alignment(option, emotions)
        score += emotional_score * 0.25
        
        # Factor 3: Goal alignment
        goal_score = await self._calculate_goal_alignment(option, goals)
        score += goal_score * 0.25
        
        # Factor 4: Personality alignment
        personality_score = await self._calculate_personality_alignment(option, personality)
        score += personality_score * 0.15
        
        # Factor 5: Social appropriateness
        social_score = await self._calculate_social_appropriateness(character_id, option)
        score += social_score * 0.05
        
        return max(0.0, min(score, 1.0))
    
    async def _calculate_emotional_alignment(
        self,
        option: Dict[str, Any],
        emotions: Dict[str, float]
    ) -> float:
        """Calculate how well action aligns with current emotions"""
        
        action = option.get("action", "")
        
        # Fear -> avoid, seek_safety
        if emotions.get("fear", 0) > 0.6:
            if action in ["avoid", "seek_safety", "retreat"]:
                return 0.9
            elif action in ["approach", "interact"]:
                return 0.2
        
        # Happiness -> socialize, interact
        if emotions.get("happiness", 0) > 0.6:
            if action in ["socialize", "interact", "respond"]:
                return 0.9
            elif action in ["avoid", "retreat"]:
                return 0.3
        
        # Curiosity -> explore, learn, observe
        if emotions.get("curiosity", 0) > 0.6:
            if action in ["explore", "learn", "observe", "ask_question"]:
                return 0.9
            elif action in ["idle", "wait"]:
                return 0.4
        
        # Anger -> avoid harmful interactions
        if emotions.get("anger", 0) > 0.6:
            if action in ["avoid", "seek_safety"]:
                return 0.8
            elif action in ["interact", "approach"]:
                return 0.3
        
        return 0.5  # Neutral alignment
    
    async def _calculate_goal_alignment(
        self,
        option: Dict[str, Any],
        goals: List[Any]
    ) -> float:
        """Calculate how well action aligns with active goals"""
        
        if not goals:
            return 0.5
        
        action = option.get("action", "")
        goal_id = option.get("goal_id")
        
        # Direct goal match
        if goal_id:
            matching_goals = [g for g in goals if g.goal_id == goal_id]
            if matching_goals:
                return matching_goals[0].priority
        
        # Action-goal alignment
        action_goals = {
            "move": ["move", "go", "reach"],
            "interact": ["interact", "help", "touch"],
            "respond": ["speak", "communicate", "respond"],
            "explore": ["learn", "explore", "discover"],
            "seek_safety": ["safe", "security", "protect"]
        }
        
        for goal in goals:
            goal_desc = goal.description.lower()
            for goal_keyword in action_goals.get(action, []):
                if goal_keyword in goal_desc:
                    return goal.priority
        
        return 0.5
    
    async def _calculate_personality_alignment(
        self,
        option: Dict[str, Any],
        personality: Dict[str, Any]
    ) -> float:
        """Calculate how well action aligns with personality"""
        
        action = option.get("action", "")
        
        # Extraversion -> social actions
        extraversion = personality.get("extraversion", 0.5)
        if action in ["socialize", "interact", "respond"]:
            return 0.3 + (extraversion * 0.7)
        elif action in ["avoid", "seek_safety"]:
            return 0.7 - (extraversion * 0.5)
        
        # Openness -> exploration
        openness = personality.get("openness", 0.5)
        if action in ["explore", "learn", "ask_question"]:
            return 0.3 + (openness * 0.7)
        
        # Conscientiousness -> goal-oriented actions
        conscientiousness = personality.get("conscientiousness", 0.5)
        if option.get("goal_id"):
            return 0.3 + (conscientiousness * 0.7)
        
        return 0.5
    
    async def _calculate_social_appropriateness(
        self,
        character_id: str,
        option: Dict[str, Any]
    ) -> float:
        """Calculate social appropriateness of action"""
        
        if not self.social_system:
            return 0.5
        
        # Check if action is appropriate given social context
        # This would check relationship status, social norms, etc.
        
        return 0.7  # Default: moderately appropriate
    
    async def _generate_reasoning(
        self,
        character_id: str,
        best_option: Dict[str, Any],
        scored_options: List[tuple],
        emotions: Dict[str, Any],
        goals: List[Any]
    ) -> List[str]:
        """Generate reasoning for the decision"""
        
        reasoning = []
        
        # Reason 1: Primary motivation
        if best_option.get("goal_id"):
            matching_goals = [g for g in goals if g.goal_id == best_option.get("goal_id")]
            if matching_goals:
                reasoning.append(f"Primary motivation: {matching_goals[0].description}")
        elif best_option.get("need_type"):
            reasoning.append(f"Addressing need: {best_option.get('need_type')}")
        else:
            reasoning.append("Responding to immediate stimulus")
        
        # Reason 2: Emotional state
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])
        if dominant_emotion[1] > 0.5:
            reasoning.append(f"Emotional state: {dominant_emotion[0]} ({dominant_emotion[1]:.2f})")
        
        # Reason 3: Action superiority
        if len(scored_options) > 1:
            second_best_score = scored_options[1][1] if len(scored_options) > 1 else 0
            score_diff = scored_options[0][1] - second_best_score
            reasoning.append(f"Action chosen with {score_diff:.2f} score advantage")
        
        return reasoning
    
    async def get_decision_history(
        self,
        character_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get decision history for a character"""
        
        if character_id not in self.decision_history:
            return []
        
        history = self.decision_history[character_id]
        history.sort(key=lambda d: d.timestamp, reverse=True)
        
        return [d.to_dict() for d in history[:limit]]