"""
Social System - Relationship Management, Trust, and Affinity
Local social algorithms, not LLM-dependent
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import asyncio
from datetime import datetime, timedelta
import json


class RelationshipType(Enum):
    """Types of relationships"""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    FAMILY = "family"
    PARTNER = "partner"
    ENEMY = "enemy"


class Relationship:
    """Represents a relationship with another entity - ENHANCED LOCAL ALGORITHMS"""
    def __init__(
        self,
        entity_id: str,
        relationship_type: RelationshipType = RelationshipType.STRANGER,
        trust: float = 0.5,
        affinity: float = 0.5,
        familiarity: float = 0.0
    ):
        self.entity_id = entity_id
        self.relationship_type = relationship_type
        self.trust = trust  # 0.0 to 1.0
        self.affinity = affinity  # 0.0 to 1.0 (liking)
        self.familiarity = familiarity  # 0.0 to 1.0
        self.interaction_count = 0
        self.last_interaction = datetime.utcnow()
        self.positive_interactions = 0
        self.negative_interactions = 0
        self.shared_experiences: List[str] = []
        self.metadata: Dict[str, Any] = {}
        
        # Enhanced social traits
        self.humor_compatibility = 0.5  # How well humor matches
        self.curiosity_alignment = 0.5  # Shared curiosity interests
        self.communication_style_match = 0.5  # Communication style compatibility
        self.emotional_resonance = 0.5  # Emotional understanding
        self.dependency_level = 0.3  # How dependent on this relationship
        self.influence_potential = 0.5  # Potential for mutual influence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "relationship_type": self.relationship_type.value,
            "trust": self.trust,
            "affinity": self.affinity,
            "familiarity": self.familiarity,
            "interaction_count": self.interaction_count,
            "last_interaction": self.last_interaction.isoformat(),
            "positive_interactions": self.positive_interactions,
            "negative_interactions": self.negative_interactions,
            "shared_experiences": self.shared_experiences,
            "metadata": self.metadata,
            "humor_compatibility": self.humor_compatibility,
            "curiosity_alignment": self.curiosity_alignment,
            "communication_style_match": self.communication_style_match,
            "emotional_resonance": self.emotional_resonance,
            "dependency_level": self.dependency_level,
            "influence_potential": self.influence_potential
        }
    
    def record_interaction(self, positive: bool = True, interaction_type: str = "general"):
        """Record an interaction with enhanced local analysis"""
        self.interaction_count += 1
        self.last_interaction = datetime.utcnow()
        
        # Enhanced interaction analysis
        interaction_weights = {
            "humor": 0.03,  # Humor affects humor_compatibility
            "curiosity": 0.02,  # Curiosity affects curiosity_alignment
            "emotional": 0.04,  # Emotional interactions affect emotional_resonance
            "communication": 0.03,  # Communication affects style match
            "help": 0.05,  # Help increases trust significantly
            "conflict": -0.08,  # Conflict decreases trust significantly
            "general": 0.02
        }
        
        weight = interaction_weights.get(interaction_type, 0.02)
        
        if positive:
            self.positive_interactions += 1
            self.trust = min(1.0, self.trust + abs(weight))
            self.affinity = min(1.0, self.affinity + abs(weight) * 0.8)
            
            # Update specific traits based on interaction type
            if interaction_type == "humor":
                self.humor_compatibility = min(1.0, self.humor_compatibility + 0.05)
            elif interaction_type == "curiosity":
                self.curiosity_alignment = min(1.0, self.curiosity_alignment + 0.05)
            elif interaction_type == "emotional":
                self.emotional_resonance = min(1.0, self.emotional_resonance + 0.05)
            elif interaction_type == "communication":
                self.communication_style_match = min(1.0, self.communication_style_match + 0.03)
        else:
            self.negative_interactions += 1
            self.trust = max(0.0, self.trust + weight)  # weight is negative for negative interactions
            self.affinity = max(0.0, self.affinity + weight * 0.6)
            
            # Negative interactions may decrease specific traits
            if interaction_type == "conflict":
                self.communication_style_match = max(0.0, self.communication_style_match - 0.05)
                self.emotional_resonance = max(0.0, self.emotional_resonance - 0.03)
        
        self.familiarity = min(1.0, self.familiarity + 0.02)
        
        # Update influence potential based on relationship strength
        self.influence_potential = (self.trust * 0.4 + self.affinity * 0.3 + 
                                   self.familiarity * 0.2 + self.emotional_resonance * 0.1)
    
    def update_relationship_type(self):
        """Update relationship type based on metrics"""
        if self.trust > 0.8 and self.affinity > 0.8 and self.familiarity > 0.7:
            self.relationship_type = RelationshipType.CLOSE_FRIEND
        elif self.trust > 0.6 and self.affinity > 0.6:
            self.relationship_type = RelationshipType.FRIEND
        elif self.trust > 0.4 and self.familiarity > 0.3:
            self.relationship_type = RelationshipType.ACQUAINTANCE
        elif self.trust < 0.2 and self.affinity < 0.2:
            self.relationship_type = RelationshipType.ENEMY
        else:
            self.relationship_type = RelationshipType.STRANGER


class SocialSystem:
    """
    Social system for relationship management
    Local social algorithms, not LLM-dependent
    """
    
    def __init__(self):
        self.relationships: Dict[str, Dict[str, Relationship]] = {}  # character_id -> entity_id -> Relationship
        self.social_groups: Dict[str, List[str]] = {}  # character_id -> group_id -> List[entity_id]
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize social system"""
        self.is_initialized = True
        print("Social System initialized")
    
    async def shutdown(self):
        """Shutdown social system"""
        self.is_initialized = False
        print("Social System shutdown")
    
    async def update_interaction(
        self,
        character_id: str,
        entity_id: str,
        stimulus: Any,
        emotions: Dict[str, float],
        decision: Dict[str, Any]
    ):
        """Update relationship based on interaction with enhanced local analysis"""
        
        # Get or create relationship
        relationship = await self._get_or_create_relationship(character_id, entity_id)
        
        # Determine if interaction was positive and get interaction type
        is_positive, interaction_type = await self._evaluate_interaction_quality(emotions, decision)
        
        # Record interaction with type
        relationship.record_interaction(is_positive, interaction_type)
        
        # Update relationship type
        relationship.update_relationship_type()
        
        # Add shared experience
        if hasattr(stimulus, 'content'):
            experience = str(stimulus.content)[:100]  # Limit length
            if experience not in relationship.shared_experiences:
                relationship.shared_experiences.append(experience)
    
    async def _get_or_create_relationship(
        self,
        character_id: str,
        entity_id: str
    ) -> Relationship:
        """Get or create a relationship"""
        
        if character_id not in self.relationships:
            self.relationships[character_id] = {}
        
        if entity_id not in self.relationships[character_id]:
            self.relationships[character_id][entity_id] = Relationship(entity_id)
        
        return self.relationships[character_id][entity_id]
    
    async def _evaluate_interaction_quality(
        self,
        emotions: Dict[str, float],
        decision: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Evaluate if an interaction was positive with enhanced local analysis"""
        
        # Enhanced emotion analysis
        positive_emotions = ["happiness", "excitement", "love", "curiosity", "surprise"]
        negative_emotions = ["anger", "fear", "sadness", "disgust"]
        
        positive_score = sum(emotions.get(e, 0) for e in positive_emotions)
        negative_score = sum(emotions.get(e, 0) for e in negative_emotions)
        
        # Determine interaction type based on decision
        action = decision.get("action", "")
        interaction_type = "general"
        
        if "help" in action or "assist" in action:
            interaction_type = "help"
        elif "conflict" in action or "avoid" in action:
            interaction_type = "conflict"
        elif "humor" in action or "play" in action:
            interaction_type = "humor"
        elif "learn" in action or "curious" in action:
            interaction_type = "curiosity"
        elif "emotional" in action or "comfort" in action:
            interaction_type = "emotional"
        elif "talk" in action or "communicate" in action:
            interaction_type = "communication"
        
        # Complex evaluation
        is_positive = positive_score > negative_score
        
        # Additional factors
        confidence = decision.get("confidence", 0.5)
        if confidence < 0.3:  # Low confidence interactions are less positive
            is_positive = is_positive and positive_score > 0.3
        
        return is_positive, interaction_type
    
    async def get_relationship(
        self,
        character_id: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get relationship information"""
        
        if character_id in self.relationships and entity_id in self.relationships[character_id]:
            return self.relationships[character_id][entity_id].to_dict()
        
        return None
    
    async def get_all_relationships(self, character_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a character"""
        
        if character_id not in self.relationships:
            return []
        
        return [
            relationship.to_dict()
            for relationship in self.relationships[character_id].values()
        ]
    
    async def set_relationship_type(
        self,
        character_id: str,
        entity_id: str,
        relationship_type: RelationshipType
    ):
        """Manually set relationship type"""
        
        relationship = await self._get_or_create_relationship(character_id, entity_id)
        relationship.relationship_type = relationship_type
    
    async def adjust_trust(
        self,
        character_id: str,
        entity_id: str,
        amount: float
    ):
        """Adjust trust level"""
        
        relationship = await self._get_or_create_relationship(character_id, entity_id)
        relationship.trust = max(0.0, min(1.0, relationship.trust + amount))
    
    async def adjust_affinity(
        self,
        character_id: str,
        entity_id: str,
        amount: float
    ):
        """Adjust affinity level"""
        
        relationship = await self._get_or_create_relationship(character_id, entity_id)
        relationship.affinity = max(0.0, min(1.0, relationship.affinity + amount))
    
    async def get_social_state(self, character_id: str) -> Dict[str, Any]:
        """Get overall social state for a character"""
        
        if character_id not in self.relationships:
            return {
                "total_relationships": 0,
                "by_type": {},
                "average_trust": 0.0,
                "average_affinity": 0.0
            }
        
        relationships = list(self.relationships[character_id].values())
        
        by_type = {}
        total_trust = 0.0
        total_affinity = 0.0
        
        for relationship in relationships:
            r_type = relationship.relationship_type.value
            by_type[r_type] = by_type.get(r_type, 0) + 1
            total_trust += relationship.trust
            total_affinity += relationship.affinity
        
        return {
            "total_relationships": len(relationships),
            "by_type": by_type,
            "average_trust": total_trust / len(relationships) if relationships else 0.0,
            "average_affinity": total_affinity / len(relationships) if relationships else 0.0
        }
    
    async def get_closest_relationships(
        self,
        character_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get closest relationships by affinity and trust"""
        
        if character_id not in self.relationships:
            return []
        
        relationships = list(self.relationships[character_id].values())
        
        # Sort by combined score (trust + affinity)
        relationships.sort(
            key=lambda r: (r.trust + r.affinity),
            reverse=True
        )
        
        return [r.to_dict() for r in relationships[:limit]]
    
    async def decay_relationships(self, character_id: str):
        """Decay relationships over time"""
        
        if character_id not in self.relationships:
            return
        
        for relationship in self.relationships[character_id].values():
            # Decay based on time since last interaction
            time_since_interaction = (datetime.utcnow() - relationship.last_interaction).total_seconds()
            days_since = time_since_interaction / 86400
            
            if days_since > 30:  # After 30 days
                decay_amount = min(0.1, days_since / 365 * 0.3)  # Up to 30% per year
                relationship.trust = max(0.0, relationship.trust - decay_amount)
                relationship.affinity = max(0.0, relationship.affinity - decay_amount)
                relationship.familiarity = max(0.0, relationship.familiarity - decay_amount)
                
                # Update relationship type
                relationship.update_relationship_type()
    
    async def create_social_group(
        self,
        character_id: str,
        group_id: str,
        entity_ids: List[str]
    ):
        """Create a social group"""
        
        if character_id not in self.social_groups:
            self.social_groups[character_id] = {}
        
        self.social_groups[character_id][group_id] = entity_ids
    
    async def get_social_groups(self, character_id: str) -> Dict[str, List[str]]:
        """Get social groups for a character"""
        
        if character_id not in self.social_groups:
            return {}
        
        return self.social_groups[character_id]
    
    async def calculate_social_influence(
        self,
        character_id: str,
        entity_id: str
    ) -> float:
        """Calculate how much influence an entity has over the character"""
        
        relationship = await self.get_relationship(character_id, entity_id)
        
        if not relationship:
            return 0.0
        
        # Enhanced influence calculation with additional factors
        trust = relationship["trust"]
        affinity = relationship["affinity"]
        familiarity = relationship["familiarity"]
        emotional_resonance = relationship.get("emotional_resonance", 0.5)
        influence_potential = relationship.get("influence_potential", 0.5)
        
        # Enhanced weighted calculation
        influence = (trust * 0.3) + (affinity * 0.25) + (familiarity * 0.2) + \
                   (emotional_resonance * 0.15) + (influence_potential * 0.1)
        
        return influence