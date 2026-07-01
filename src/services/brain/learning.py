"""
Learning Engine - Experience-based Learning
Local learning algorithms, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
from datetime import datetime, timedelta
import json
from collections import defaultdict


class LearningType(Enum):
    """Types of learning"""
    PREFERENCE_LEARNING = "preference_learning"  # Learn user preferences
    PATTERN_LEARNING = "pattern_learning"  # Learn behavioral patterns
    ASSOCIATIVE_LEARNING = "associative_learning"  # Learn associations
    REINFORCEMENT_LEARNING = "reinforcement_learning"  # Learn from feedback
    SOCIAL_LEARNING = "social_learning"  # Learn from social interactions


class Learning:
    """Represents a learned item"""
    def __init__(
        self,
        learning_id: str,
        learning_type: LearningType,
        content: str,
        confidence: float = 0.5,
        strength: float = 0.5
    ):
        self.learning_id = learning_id
        self.learning_type = learning_type
        self.content = content
        self.confidence = confidence  # How confident we are in this learning
        self.strength = strength  # How strong the association is
        self.created_at = datetime.utcnow()
        self.last_reinforced = datetime.utcnow()
        self.reinforcement_count = 0
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "learning_id": self.learning_id,
            "learning_type": self.learning_type.value,
            "content": self.content,
            "confidence": self.confidence,
            "strength": self.strength,
            "created_at": self.created_at.isoformat(),
            "last_reinforced": self.last_reinforced.isoformat(),
            "reinforcement_count": self.reinforcement_count,
            "metadata": self.metadata
        }
    
    def reinforce(self, amount: float = 0.1):
        """Reinforce this learning"""
        self.strength = min(1.0, self.strength + amount)
        self.confidence = min(1.0, self.confidence + amount * 0.5)
        self.last_reinforced = datetime.utcnow()
        self.reinforcement_count += 1
    
    def decay(self, amount: float = 0.05):
        """Decay this learning over time"""
        self.strength = max(0.0, self.strength - amount)
        self.confidence = max(0.0, self.confidence - amount * 0.5)


class LearningEngine:
    """
    Learning engine for experience-based learning
    Local learning algorithms, not LLM-dependent
    """
    
    def __init__(self):
        self.learnings: Dict[str, Dict[str, Learning]] = {}  # character_id -> learning_id -> Learning
        self.learning_patterns: Dict[str, Dict[str, List[float]]] = {}  # character_id -> pattern -> values
        self.preferences: Dict[str, Dict[str, float]] = {}  # character_id -> preference -> value
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize learning engine"""
        self.is_initialized = True
        print("Learning Engine initialized")
    
    async def shutdown(self):
        """Shutdown learning engine"""
        self.is_initialized = False
        print("Learning Engine shutdown")
    
    async def learn_from_interaction(
        self,
        character_id: str,
        stimulus: Any,
        decision: Dict[str, Any],
        actions: List[Dict[str, Any]],
        emotions: Dict[str, float]
    ):
        """Learn from an interaction"""
        
        # Learn from decision outcomes
        await self._learn_from_decision(character_id, decision, emotions)
        
        # Learn from action effectiveness
        await self._learn_from_actions(character_id, actions, emotions)
        
        # Learn preferences from stimulus
        await self._learn_preferences(character_id, stimulus, emotions)
        
        # Learn patterns
        await self._learn_patterns(character_id, stimulus, decision, actions)
    
    async def _learn_from_decision(
        self,
        character_id: str,
        decision: Dict[str, Any],
        emotions: Dict[str, float]
    ):
        """Learn from decision outcomes"""
        
        if character_id not in self.learnings:
            self.learnings[character_id] = {}
        
        # Analyze emotional response to decision
        primary_emotion = max(emotions.items(), key=lambda x: x[1])
        
        if primary_emotion[1] > 0.6:  # Strong emotion
            import uuid
            learning_id = str(uuid.uuid4())
            
            learning = Learning(
                learning_id=learning_id,
                learning_type=LearningType.REINFORCEMENT_LEARNING,
                content=f"Decision '{decision.get('action', 'unknown')}' led to {primary_emotion[0]} emotion",
                confidence=0.7,
                strength=primary_emotion[1]
            )
            
            # If positive emotion, reinforce the decision type
            if primary_emotion[0] in ["happiness", "excitement", "love"]:
                learning.reinforce(0.2)
            # If negative emotion, weaken the association
            elif primary_emotion[0] in ["anger", "fear", "sadness"]:
                learning.decay(0.1)
            
            self.learnings[character_id][learning_id] = learning
    
    async def _learn_from_actions(
        self,
        character_id: str,
        actions: List[Dict[str, Any]],
        emotions: Dict[str, float]
    ):
        """Learn from action effectiveness"""
        
        for action in actions:
            action_type = action.get("action", "unknown")
            
            # Track action patterns
            if character_id not in self.learning_patterns:
                self.learning_patterns[character_id] = defaultdict(list)
            
            # Record emotional outcome for this action
            primary_emotion = max(emotions.items(), key=lambda x: x[1])
            self.learning_patterns[character_id][action_type].append(primary_emotion[1])
            
            # Keep only recent patterns
            if len(self.learning_patterns[character_id][action_type]) > 20:
                self.learning_patterns[character_id][action_type].pop(0)
    
    async def _learn_preferences(
        self,
        character_id: str,
        stimulus: Any,
        emotions: Dict[str, float]
    ):
        """Learn user/character preferences"""
        
        if character_id not in self.preferences:
            self.preferences[character_id] = {}
        
        # Extract preference information from stimulus
        if hasattr(stimulus, 'content'):
            content = str(stimulus.content).lower()
            
            # Simple preference extraction
            if "like" in content or "love" in content:
                # Extract what is liked
                words = content.split()
                for i, word in enumerate(words):
                    if word in ["like", "love"] and i + 1 < len(words):
                        preference = words[i + 1]
                        current_value = self.preferences[character_id].get(preference, 0.5)
                        self.preferences[character_id][preference] = min(1.0, current_value + 0.1)
            
            if "dislike" in content or "hate" in content:
                # Extract what is disliked
                words = content.split()
                for i, word in enumerate(words):
                    if word in ["dislike", "hate"] and i + 1 < len(words):
                        preference = words[i + 1]
                        current_value = self.preferences[character_id].get(preference, 0.5)
                        self.preferences[character_id][preference] = max(0.0, current_value - 0.1)
    
    async def _learn_patterns(
        self,
        character_id: str,
        stimulus: Any,
        decision: Dict[str, Any],
        actions: List[Dict[str, Any]]
    ):
        """Learn behavioral patterns"""
        
        import uuid
        
        # Learn stimulus-response patterns
        if hasattr(stimulus, 'content'):
            stimulus_content = str(stimulus.content)
            action_type = decision.get("action", "unknown")
            
            # Create associative learning
            learning_id = str(uuid.uuid4())
            
            learning = Learning(
                learning_id=learning_id,
                learning_type=LearningType.ASSOCIATIVE_LEARNING,
                content=f"Stimulus '{stimulus_content[:50]}...' associated with action '{action_type}'",
                confidence=0.5,
                strength=0.5
            )
            
            if character_id not in self.learnings:
                self.learnings[character_id] = {}
            
            self.learnings[character_id][learning_id] = learning
    
    async def reinforce_learning(
        self,
        character_id: str,
        learning_id: str,
        amount: float = 0.1
    ):
        """Reinforce a specific learning"""
        
        if character_id in self.learnings and learning_id in self.learnings[character_id]:
            self.learnings[character_id][learning_id].reinforce(amount)
    
    async def get_learnings(
        self,
        character_id: str,
        learning_type: Optional[LearningType] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get learnings for a character"""
        
        if character_id not in self.learnings:
            return []
        
        learnings = list(self.learnings[character_id].values())
        
        # Filter by type if specified
        if learning_type:
            learnings = [l for l in learnings if l.learning_type == learning_type]
        
        # Sort by strength and confidence
        learnings.sort(
            key=lambda l: (l.strength, l.confidence),
            reverse=True
        )
        
        return [l.to_dict() for l in learnings[:limit]]
    
    async def get_preferences(self, character_id: str) -> Dict[str, float]:
        """Get learned preferences for a character"""
        
        if character_id not in self.preferences:
            return {}
        
        return self.preferences[character_id]
    
    async def get_action_effectiveness(
        self,
        character_id: str,
        action_type: str
    ) -> float:
        """Get the effectiveness score for an action type"""
        
        if character_id not in self.learning_patterns:
            return 0.5
        
        if action_type not in self.learning_patterns[character_id]:
            return 0.5
        
        outcomes = self.learning_patterns[character_id][action_type]
        
        if not outcomes:
            return 0.5
        
        # Calculate average emotional outcome
        avg_outcome = sum(outcomes) / len(outcomes)
        
        return avg_outcome
    
    async def predict_action_outcome(
        self,
        character_id: str,
        action_type: str
    ) -> Dict[str, Any]:
        """Predict the outcome of an action based on learning"""
        
        effectiveness = await self.get_action_effectiveness(character_id, action_type)
        
        # Find related learnings
        related_learnings = []
        if character_id in self.learnings:
            for learning in self.learnings[character_id].values():
                if action_type.lower() in learning.content.lower():
                    related_learnings.append(learning)
        
        return {
            "action_type": action_type,
            "predicted_effectiveness": effectiveness,
            "confidence": 0.5 if not related_learnings else max(l.confidence for l in related_learnings),
            "related_learnings": len(related_learnings)
        }
    
    async def decay_learnings(self, character_id: str):
        """Decay learnings over time"""
        
        if character_id not in self.learnings:
            return
        
        for learning in self.learnings[character_id].values():
            # Decay based on time since last reinforcement
            time_since_reinforcement = (datetime.utcnow() - learning.last_reinforced).total_seconds()
            decay_amount = time_since_reinforcement / 86400 * 0.01  # 1% per day
            learning.decay(decay_amount)
        
        # Remove weak learnings
        to_remove = [
            learning_id for learning_id, learning in self.learnings[character_id].items()
            if learning.strength < 0.1 and learning.confidence < 0.1
        ]
        
        for learning_id in to_remove:
            del self.learnings[character_id][learning_id]
    
    async def get_learning_summary(self, character_id: str) -> Dict[str, Any]:
        """Get summary of learning state"""
        
        if character_id not in self.learnings:
            return {
                "total_learnings": 0,
                "by_type": {},
                "average_strength": 0.0,
                "total_preferences": 0
            }
        
        total_learnings = len(self.learnings[character_id])
        by_type = {}
        total_strength = 0.0
        
        for learning in self.learnings[character_id].values():
            l_type = learning.learning_type.value
            by_type[l_type] = by_type.get(l_type, 0) + 1
            total_strength += learning.strength
        
        return {
            "total_learnings": total_learnings,
            "by_type": by_type,
            "average_strength": total_strength / total_learnings if total_learnings > 0 else 0.0,
            "total_preferences": len(self.preferences.get(character_id, {}))
        }
    
    async def set_preference(self, character_id: str, preference: str, value: float):
        """Manually set a preference"""
        
        if character_id not in self.preferences:
            self.preferences[character_id] = {}
        
        self.preferences[character_id][preference] = max(0.0, min(value, 1.0))
    
    async def get_preference(self, character_id: str, preference: str) -> float:
        """Get a specific preference value"""
        
        if character_id in self.preferences and preference in self.preferences[character_id]:
            return self.preferences[character_id][preference]
        
        return 0.5  # Default neutral value