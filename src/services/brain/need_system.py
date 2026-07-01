"""
Need System - Maslow-inspired Need Management
Local need tracking and motivation generation, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
from datetime import datetime, timedelta
import math


class NeedType(Enum):
    """Types of needs based on Maslow's hierarchy"""
    PHYSIOLOGICAL = "physiological"  # Basic survival needs
    SAFETY = "safety"  # Security and stability
    SOCIAL = "social"  # Belonging and love
    ESTEEM = "esteem"  # Respect and recognition
    SELF_ACTUALIZATION = "self_actualization"  # Personal growth


class Need:
    """Represents a need with its current satisfaction level"""
    def __init__(
        self,
        need_type: NeedType,
        name: str,
        current_level: float = 0.5,
        decay_rate: float = 0.01,
        importance: float = 0.5
    ):
        self.need_type = need_type
        self.name = name
        self.current_level = current_level  # 0.0 = unsatisfied, 1.0 = fully satisfied
        self.decay_rate = decay_rate  # How fast the need decays over time
        self.importance = importance  # Base importance of this need
        self.last_updated = datetime.utcnow()
        self.satisfaction_history: List[float] = [current_level]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "need_type": self.need_type.value,
            "name": self.name,
            "current_level": self.current_level,
            "decay_rate": self.decay_rate,
            "importance": self.importance,
            "last_updated": self.last_updated.isoformat(),
            "urgency": self.calculate_urgency()
        }
    
    def calculate_urgency(self) -> float:
        """Calculate urgency based on current level and importance"""
        # Urgency increases as level decreases
        return self.importance * (1.0 - self.current_level)
    
    def decay(self, delta_time: float):
        """Decay need level over time"""
        decay_amount = self.decay_rate * delta_time
        self.current_level = max(0.0, self.current_level - decay_amount)
        self.last_updated = datetime.utcnow()
        
        # Track history
        self.satisfaction_history.append(self.current_level)
        if len(self.satisfaction_history) > 100:
            self.satisfaction_history.pop(0)
    
    def satisfy(self, amount: float):
        """Satisfy need by given amount"""
        self.current_level = min(1.0, self.current_level + amount)
        self.last_updated = datetime.utcnow()
        self.satisfaction_history.append(self.current_level)
        if len(self.satisfaction_history) > 100:
            self.satisfaction_history.pop(0)


class NeedSystem:
    """
    Manages needs for AI characters
    Uses Maslow's hierarchy of needs with local decision making
    """
    
    def __init__(self):
        self.needs: Dict[str, Dict[str, Need]] = {}  # character_id -> need_name -> Need
        self.is_initialized = False
        self.last_update: Dict[str, datetime] = {}
    
    async def initialize(self):
        """Initialize need system"""
        self.is_initialized = True
        print("Need System initialized")
    
    async def shutdown(self):
        """Shutdown need system"""
        self.is_initialized = False
        print("Need System shutdown")
    
    async def initialize_character_needs(self, character_id: str):
        """Initialize default needs for a character"""
        
        # Physiological needs
        physiological_needs = [
            Need(NeedType.PHYSIOLOGICAL, "energy", 0.8, 0.005, 0.9),
            Need(NeedType.PHYSIOLOGICAL, "comfort", 0.7, 0.003, 0.7),
        ]
        
        # Safety needs
        safety_needs = [
            Need(NeedType.SAFETY, "security", 0.9, 0.002, 0.95),
            Need(NeedType.SAFETY, "stability", 0.8, 0.003, 0.8),
        ]
        
        # Social needs
        social_needs = [
            Need(NeedType.SOCIAL, "belonging", 0.6, 0.004, 0.8),
            Need(NeedType.SOCIAL, "affection", 0.5, 0.005, 0.7),
        ]
        
        # Esteem needs
        esteem_needs = [
            Need(NeedType.ESTEEM, "respect", 0.6, 0.003, 0.7),
            Need(NeedType.ESTEEM, "achievement", 0.5, 0.004, 0.8),
        ]
        
        # Self-actualization needs
        self_actualization_needs = [
            Need(NeedType.SELF_ACTUALIZATION, "growth", 0.4, 0.002, 0.6),
            Need(NeedType.SELF_ACTUALIZATION, "purpose", 0.3, 0.003, 0.7),
        ]
        
        all_needs = (
            physiological_needs + safety_needs + social_needs + 
            esteem_needs + self_actualization_needs
        )
        
        self.needs[character_id] = {need.name: need for need in all_needs}
        self.last_update[character_id] = datetime.utcnow()
    
    async def update_needs(self, character_id: str):
        """Update all needs for a character (decay over time)"""
        
        if character_id not in self.needs:
            await self.initialize_character_needs(character_id)
        
        # Calculate time since last update
        last_update = self.last_update.get(character_id, datetime.utcnow())
        delta_time = (datetime.utcnow() - last_update).total_seconds()
        
        # Decay all needs
        for need in self.needs[character_id].values():
            need.decay(delta_time)
        
        self.last_update[character_id] = datetime.utcnow()
    
    async def satisfy_need(self, character_id: str, need_name: str, amount: float):
        """Satisfy a specific need"""
        if character_id in self.needs and need_name in self.needs[character_id]:
            self.needs[character_id][need_name].satisfy(amount)
    
    async def get_needs(self, character_id: str) -> Dict[str, Any]:
        """Get all needs for a character"""
        if character_id not in self.needs:
            await self.initialize_character_needs(character_id)
        
        return {
            need_name: need.to_dict()
            for need_name, need in self.needs[character_id].items()
        }
    
    async def get_most_urgent_need(self, character_id: str) -> Optional[Need]:
        """Get the most urgent need for a character"""
        if character_id not in self.needs:
            return None
        
        urgent_need = None
        max_urgency = 0.0
        
        for need in self.needs[character_id].values():
            urgency = need.calculate_urgency()
            if urgency > max_urgency:
                max_urgency = urgency
                urgent_need = need
        
        return urgent_need
    
    async def get_need_by_type(self, character_id: str, need_type: NeedType) -> List[Need]:
        """Get all needs of a specific type"""
        if character_id not in self.needs:
            return []
        
        return [
            need for need in self.needs[character_id].values()
            if need.need_type == need_type
        ]
    
    async def calculate_motivation(
        self, 
        character_id: str, 
        action: str
    ) -> float:
        """
        Calculate motivation for an action based on needs - ADVANCED LOCAL CALCULATION
        Enhanced with multi-factor analysis, not LLM-dependent
        """
        
        if character_id not in self.needs:
            await self.initialize_character_needs(character_id)
        
        # Enhanced action-need mapping with weights
        action_need_mapping = {
            "rest": {
                "needs": ["energy", "comfort"],
                "weights": {"energy": 0.7, "comfort": 0.3},
                "base_motivation": 0.5
            },
            "seek_safety": {
                "needs": ["security", "stability"],
                "weights": {"security": 0.6, "stability": 0.4},
                "base_motivation": 0.6
            },
            "socialize": {
                "needs": ["belonging", "affection"],
                "weights": {"belonging": 0.5, "affection": 0.5},
                "base_motivation": 0.5
            },
            "achieve": {
                "needs": ["respect", "achievement"],
                "weights": {"respect": 0.4, "achievement": 0.6},
                "base_motivation": 0.6
            },
            "learn": {
                "needs": ["growth", "purpose"],
                "weights": {"growth": 0.5, "purpose": 0.5},
                "base_motivation": 0.5
            },
            "explore": {
                "needs": ["growth", "purpose"],
                "weights": {"growth": 0.4, "purpose": 0.6},
                "base_motivation": 0.5
            },
            "help": {
                "needs": ["respect", "achievement", "belonging"],
                "weights": {"respect": 0.3, "achievement": 0.3, "belonging": 0.4},
                "base_motivation": 0.6
            },
            "seek_comfort": {
                "needs": ["comfort", "energy"],
                "weights": {"comfort": 0.8, "energy": 0.2},
                "base_motivation": 0.5
            },
            "maintain_stability": {
                "needs": ["stability", "security"],
                "weights": {"stability": 0.7, "security": 0.3},
                "base_motivation": 0.5
            },
            "seek_affection": {
                "needs": ["affection", "belonging"],
                "weights": {"affection": 0.7, "belonging": 0.3},
                "base_motivation": 0.5
            },
            "engage_in_meaningful_activity": {
                "needs": ["purpose", "growth", "achievement"],
                "weights": {"purpose": 0.5, "growth": 0.3, "achievement": 0.2},
                "base_motivation": 0.6
            }
        }
        
        action_config = action_need_mapping.get(action)
        
        if not action_config:
            return 0.5  # Default motivation for unknown actions
        
        relevant_needs = action_config["needs"]
        weights = action_config["weights"]
        base_motivation = action_config["base_motivation"]
        
        # Calculate weighted motivation based on urgency of relevant needs
        weighted_motivation = 0.0
        total_weight = 0.0
        
        for need_name in relevant_needs:
            if need_name in self.needs[character_id]:
                need = self.needs[character_id][need_name]
                urgency = need.calculate_urgency()
                weight = weights.get(need_name, 1.0)
                
                weighted_motivation += urgency * weight
                total_weight += weight
        
        # Normalize weighted motivation
        if total_weight > 0:
            normalized_motivation = weighted_motivation / total_weight
        else:
            normalized_motivation = base_motivation
        
        # Apply Maslow hierarchy adjustment
        motivation = await self._apply_maslow_adjustment(
            character_id, 
            action, 
            normalized_motivation
        )
        
        # Apply temporal decay adjustment (needs decay over time)
        motivation = await self._apply_temporal_adjustment(
            character_id, 
            motivation
        )
        
        return max(0.0, min(motivation, 1.0))
    
    async def _apply_maslow_adjustment(
        self, 
        character_id: str, 
        action: str, 
        base_motivation: float
    ) -> float:
        """Apply Maslow hierarchy - lower needs have higher priority"""
        
        # Get priority needs based on Maslow hierarchy
        priority_needs = await self.apply_maslow_hierarchy(character_id)
        
        if not priority_needs:
            return base_motivation
        
        # Define which need types each action primarily satisfies
        action_need_types = {
            "rest": NeedType.PHYSIOLOGICAL,
            "seek_safety": NeedType.SAFETY,
            "socialize": NeedType.SOCIAL,
            "seek_affection": NeedType.SOCIAL,
            "achieve": NeedType.ESTEEM,
            "engage_in_meaningful_activity": NeedType.SELF_ACTUALIZATION,
            "learn": NeedType.SELF_ACTUALIZATION,
            "explore": NeedType.SELF_ACTUALIZATION,
            "help": NeedType.ESTEEM,
            "seek_comfort": NeedType.PHYSIOLOGICAL,
            "maintain_stability": NeedType.SAFETY
        }
        
        action_need_type = action_need_types.get(action)
        
        if not action_need_type:
            return base_motivation
        
        # If action addresses highest priority need, boost motivation
        if action_need_type == priority_needs[0]:
            return min(base_motivation + 0.3, 1.0)
        
        # If action addresses lower priority need while higher needs are urgent, reduce motivation
        if action_need_type in priority_needs[1:]:  # Not the highest priority
            highest_priority = priority_needs[0]
            
            # Calculate how much higher priority needs are unsatisfied
            high_priority_needs = await self.get_need_by_type(character_id, highest_priority)
            if high_priority_needs:
                avg_high_priority_urgency = sum(
                    n.calculate_urgency() for n in high_priority_needs
                ) / len(high_priority_needs)
                
                if avg_high_priority_urgency > 0.7:  # Higher priority needs are very urgent
                    return max(base_motivation - 0.2, 0.1)
        
        return base_motivation
    
    async def _apply_temporal_adjustment(
        self, 
        character_id: str, 
        base_motivation: float
    ) -> float:
        """Apply temporal adjustments based on need decay patterns"""
        
        if character_id not in self.needs:
            return base_motivation
        
        # Calculate average decay rate across all needs
        all_needs = list(self.needs[character_id].values())
        avg_decay_rate = sum(n.decay_rate for n in all_needs) / len(all_needs)
        
        # If needs are decaying rapidly, increase base motivation for need-satisfying actions
        if avg_decay_rate > 0.004:  # High decay rate
            return min(base_motivation + 0.1, 1.0)
        
        # If needs are stable, maintain base motivation
        return base_motivation
    
    async def get_motivation_profile(self, character_id: str) -> Dict[str, float]:
        """Get motivation profile for different action types"""
        
        action_types = [
            "rest", "seek_safety", "socialize", "achieve", 
            "learn", "explore", "help"
        ]
        
        motivation_profile = {}
        for action in action_types:
            motivation = await self.calculate_motivation(character_id, action)
            motivation_profile[action] = motivation
        
        return motivation_profile
    
    async def apply_maslow_hierarchy(self, character_id: str) -> List[NeedType]:
        """
        Apply Maslow's hierarchy - lower needs must be satisfied before higher needs
        Returns ordered list of need types to focus on
        """
        
        if character_id not in self.needs:
            await self.initialize_character_needs(character_id)
        
        # Calculate average satisfaction for each need type
        need_type_satisfaction = {}
        
        for need_type in NeedType:
            needs_of_type = await self.get_need_by_type(character_id, need_type)
            if needs_of_type:
                avg_satisfaction = sum(n.current_level for n in needs_of_type) / len(needs_of_type)
                need_type_satisfaction[need_type] = avg_satisfaction
        
        # Order by hierarchy (lower needs first) and satisfaction level
        hierarchy_order = [
            NeedType.PHYSIOLOGICAL,
            NeedType.SAFETY,
            NeedType.SOCIAL,
            NeedType.ESTEEM,
            NeedType.SELF_ACTUALIZATION
        ]
        
        # Filter to need types that need attention (satisfaction < 0.7)
        priority_needs = [
            need_type for need_type in hierarchy_order
            if need_type in need_type_satisfaction and need_type_satisfaction[need_type] < 0.7
        ]
        
        return priority_needs
    
    async def generate_goal_from_needs(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Generate a goal based on the most urgent need"""
        
        urgent_need = await self.get_most_urgent_need(character_id)
        
        if not urgent_need:
            return None
        
        # Generate goal based on need type
        goal_templates = {
            NeedType.PHYSIOLOGICAL: {
                "energy": "Rest and recover energy",
                "comfort": "Seek comfortable environment"
            },
            NeedType.SAFETY: {
                "security": "Ensure personal safety",
                "stability": "Maintain stable environment"
            },
            NeedType.SOCIAL: {
                "belonging": "Engage in social interaction",
                "affection": "Seek positive social contact"
            },
            NeedType.ESTEEM: {
                "respect": "Act to gain respect",
                "achievement": "Pursue achievable goals"
            },
            NeedType.SELF_ACTUALIZATION: {
                "growth": "Learn and develop skills",
                "purpose": "Engage in meaningful activities"
            }
        }
        
        if urgent_need.need_type in goal_templates:
            if urgent_need.name in goal_templates[urgent_need.need_type]:
                return {
                    "description": goal_templates[urgent_need.need_type][urgent_need.name],
                    "priority": urgent_need.calculate_urgency(),
                    "goal_type": "need_satisfaction",
                    "metadata": {
                        "need_type": urgent_need.need_type.value,
                        "need_name": urgent_need.name
                    }
                }
        
        return None
    
    async def set_need_level(self, character_id: str, need_name: str, level: float):
        """Manually set a need level (for testing or external events)"""
        if character_id in self.needs and need_name in self.needs[character_id]:
            self.needs[character_id][need_name].current_level = max(0.0, min(level, 1.0))
            self.needs[character_id][need_name].last_updated = datetime.utcnow()
    
    async def get_need_summary(self, character_id: str) -> Dict[str, Any]:
        """Get summary of need state"""
        if character_id not in self.needs:
            await self.initialize_character_needs(character_id)
        
        # Calculate overall metrics
        all_needs = list(self.needs[character_id].values())
        avg_satisfaction = sum(n.current_level for n in all_needs) / len(all_needs)
        
        most_urgent = await self.get_most_urgent_need(character_id)
        
        priority_hierarchy = await self.apply_maslow_hierarchy(character_id)
        
        return {
            "average_satisfaction": avg_satisfaction,
            "most_urgent_need": most_urgent.name if most_urgent else None,
            "most_urgent_urgency": most_urgent.calculate_urgency() if most_urgent else 0.0,
            "priority_hierarchy": [nt.value for nt in priority_hierarchy],
            "total_needs": len(all_needs),
            "critical_needs": [
                n.name for n in all_needs if n.current_level < 0.3
            ]
        }