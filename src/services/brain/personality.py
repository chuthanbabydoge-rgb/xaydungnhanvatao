"""
Personality Engine - Personality Traits and Expression
Local personality management, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
import json
import random


class PersonalityTrait(Enum):
    """Big Five personality traits"""
    OPENNESS = "openness"  # Openness to experience
    CONSCIENTIOUSNESS = "conscientiousness"  # Self-discipline
    EXTRAVERSION = "extraversion"  # Social energy
    AGREEABLENESS = "agreeableness"  # Cooperation
    NEUROTICISM = "neuroticism"  # Emotional stability


class SecondaryTrait(Enum):
    """Secondary personality traits"""
    HUMOR = "humor"  # Sense of humor
    CURIOSITY = "curiosity"  # Desire to learn
    CREATIVITY = "creativity"  # Creative thinking
    EMPATHY = "empathy"  # Understanding others
    ASSERTIVENESS = "assertiveness"  # Confidence
    OPTIMISM = "optimism"  # Positive outlook
    ADVENTUROUSNESS = "adventurousness"  # Risk-taking


class Personality:
    """Represents a character's personality - ENHANCED LOCAL TRAIT MANAGEMENT"""
    def __init__(
        self,
        character_id: str,
        big_five: Optional[Dict[str, float]] = None,
        secondary_traits: Optional[Dict[str, float]] = None,
        quirks: Optional[List[str]] = None
    ):
        self.character_id = character_id
        
        # Big Five traits (0.0 to 1.0)
        self.big_five = big_five or {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5
        }
        
        # Secondary traits (0.0 to 1.0)
        self.secondary_traits = secondary_traits or {
            "humor": 0.5,
            "curiosity": 0.5,
            "creativity": 0.5,
            "empathy": 0.5,
            "assertiveness": 0.5,
            "optimism": 0.5,
            "adventurousness": 0.5
        }
        
        # Character quirks
        self.quirks = quirks or []
        
        # Response style
        self.response_style = "casual"  # casual, formal, playful, etc.
        
        # Enhanced personality dynamics
        self.trait_history: Dict[str, List[float]] = {}  # Track trait changes over time
        self.personality_conflicts: List[str] = []  # Track conflicting traits
        self.stability_score = 0.8  # How stable the personality is
        self.adaptability_score = 0.5  # How adaptable to change
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "big_five": self.big_five,
            "secondary_traits": self.secondary_traits,
            "quirks": self.quirks,
            "response_style": self.response_style
        }
    
    def get_trait(self, trait_name: str) -> float:
        """Get a specific trait value"""
        if trait_name in self.big_five:
            return self.big_five[trait_name]
        elif trait_name in self.secondary_traits:
            return self.secondary_traits[trait_name]
        return 0.5
    
    def set_trait(self, trait_name: str, value: float):
        """Set a specific trait value with enhanced local tracking"""
        value = max(0.0, min(value, 1.0))
        
        # Track trait history
        if trait_name not in self.trait_history:
            self.trait_history[trait_name] = []
        
        old_value = self.get_trait(trait_name)
        self.trait_history[trait_name].append(old_value)
        
        # Keep history limited
        if len(self.trait_history[trait_name]) > 50:
            self.trait_history[trait_name].pop(0)
        
        # Set new value
        if trait_name in self.big_five:
            self.big_five[trait_name] = value
        elif trait_name in self.secondary_traits:
            self.secondary_traits[trait_name] = value
        
        # Check for personality conflicts
        self._check_personality_conflicts()
        
        # Update stability based on trait volatility
        self._update_stability_score()
    
    def _check_personality_conflicts(self):
        """Check for conflicting personality traits using local analysis"""
        self.personality_conflicts = []
        
        # High neuroticism vs high optimism
        if self.big_five["neuroticism"] > 0.7 and self.secondary_traits["optimism"] > 0.7:
            self.personality_conflicts.append("neuroticism_optimism")
        
        # High agreeableness vs high assertiveness
        if self.big_five["agreeableness"] > 0.7 and self.secondary_traits["assertiveness"] > 0.7:
            self.personality_conflicts.append("agreeableness_assertiveness")
        
        # High conscientiousness vs high adventurousness
        if self.big_five["conscientiousness"] > 0.7 and self.secondary_traits["adventurousness"] > 0.7:
            self.personality_conflicts.append("conscientiousness_adventurousness")
        
        # Low extraversion vs high humor
        if self.big_five["extraversion"] < 0.3 and self.secondary_traits["humor"] > 0.7:
            self.personality_conflicts.append("introversion_humor")
    
    def _update_stability_score(self):
        """Update personality stability based on trait volatility"""
        if not self.trait_history:
            return
        
        # Calculate volatility for each trait
        volatilities = []
        for trait_name, history in self.trait_history.items():
            if len(history) > 1:
                recent_changes = [abs(history[i] - history[i-1]) for i in range(1, len(history))]
                avg_volatility = sum(recent_changes) / len(recent_changes)
                volatilities.append(avg_volatility)
        
        if volatilities:
            avg_volatility = sum(volatilities) / len(volatilities)
            # Higher volatility = lower stability
            self.stability_score = max(0.1, 1.0 - avg_volatility * 2)
    
    def get_trait_volatility(self, trait_name: str) -> float:
        """Get volatility for a specific trait"""
        if trait_name not in self.trait_history or len(self.trait_history[trait_name]) < 2:
            return 0.0
        
        history = self.trait_history[trait_name]
        changes = [abs(history[i] - history[i-1]) for i in range(1, len(history))]
        return sum(changes) / len(changes)
    
    def adapt_to_context(self, context_type: str, adaptation_amount: float = 0.1):
        """Adapt personality traits based on context using local algorithms"""
        if context_type == "stressful":
            # Increase neuroticism, decrease optimism temporarily
            old_neuroticism = self.big_five["neuroticism"]
            old_optimism = self.secondary_traits["optimism"]
            
            self.big_five["neuroticism"] = min(1.0, old_neuroticism + adaptation_amount)
            self.secondary_traits["optimism"] = max(0.0, old_optimism - adaptation_amount)
            
        elif context_type == "social":
            # Increase extraversion and agreeableness
            old_extraversion = self.big_five["extraversion"]
            old_agreeableness = self.big_five["agreeableness"]
            
            self.big_five["extraversion"] = min(1.0, old_extraversion + adaptation_amount * 0.5)
            self.big_five["agreeableness"] = min(1.0, old_agreeableness + adaptation_amount * 0.3)
            
        elif context_type == "creative":
            # Increase openness and creativity
            old_openness = self.big_five["openness"]
            old_creativity = self.secondary_traits["creativity"]
            
            self.big_five["openness"] = min(1.0, old_openness + adaptation_amount * 0.4)
            self.secondary_traits["creativity"] = min(1.0, old_creativity + adaptation_amount * 0.6)
        
        # Update adaptability score
        self.adaptability_score = min(1.0, self.adaptability_score + adaptation_amount * 0.1)
    
    def resolve_conflicts(self):
        """Resolve personality conflicts using local balancing"""
        for conflict in self.personality_conflicts:
            if conflict == "neuroticism_optimism":
                # Balance towards the middle
                avg = (self.big_five["neuroticism"] + self.secondary_traits["optimism"]) / 2
                self.big_five["neuroticism"] = avg
                self.secondary_traits["optimism"] = avg
                
            elif conflict == "agreeableness_assertiveness":
                # Reduce the higher one slightly
                if self.big_five["agreeableness"] > self.secondary_traits["assertiveness"]:
                    self.big_five["agreeableness"] *= 0.9
                else:
                    self.secondary_traits["assertiveness"] *= 0.9
                    
            elif conflict == "conscientiousness_adventurousness":
                # Balance based on stability score
                if self.stability_score > 0.7:
                    # Favor conscientiousness
                    self.big_five["conscientiousness"] = min(1.0, self.big_five["conscientiousness"] + 0.1)
                    self.secondary_traits["adventurousness"] = max(0.0, self.secondary_traits["adventurousness"] - 0.1)
                else:
                    # Favor adventurousness
                    self.secondary_traits["adventurousness"] = min(1.0, self.secondary_traits["adventurousness"] + 0.1)
                    self.big_five["conscientiousness"] = max(0.0, self.big_five["conscientiousness"] - 0.1)
                    
            elif conflict == "introversion_humor":
                # Reduce humor for introverts
                self.secondary_traits["humor"] = max(0.0, self.secondary_traits["humor"] - 0.1)
        
        # Re-check conflicts after resolution
        self._check_personality_conflicts()
    
    def add_quirk(self, quirk: str):
        """Add a character quirk"""
        if quirk not in self.quirks:
            self.quirks.append(quirk)
    
    def should_use_humor(self) -> bool:
        """Determine if humor should be used based on personality"""
        humor_trait = self.secondary_traits.get("humor", 0.5)
        openness = self.big_five.get("openness", 0.5)
        extraversion = self.big_five.get("extraversion", 0.5)
        
        # Higher humor, openness, and extraversion increase likelihood
        humor_score = (humor_trait * 0.5) + (openness * 0.25) + (extraversion * 0.25)
        
        return random.random() < humor_score
    
    def should_be_curious(self) -> bool:
        """Determine if curiosity should drive behavior"""
        curiosity = self.secondary_traits.get("curiosity", 0.5)
        openness = self.big_five.get("openness", 0.5)
        
        curiosity_score = (curiosity * 0.7) + (openness * 0.3)
        
        return random.random() < curiosity_score
    
    def get_response_formality(self) -> float:
        """Get formality level (0.0 = casual, 1.0 = formal)"""
        conscientiousness = self.big_five.get("conscientiousness", 0.5)
        agreeableness = self.big_five.get("agreeableness", 0.5)
        
        # Higher conscientiousness and agreeableness increase formality
        formality = (conscientiousness * 0.6) + (agreeableness * 0.4)
        
        return formality
    
    def get_risk_tolerance(self) -> float:
        """Get risk tolerance (0.0 = cautious, 1.0 = risk-taking)"""
        adventurousness = self.secondary_traits.get("adventurousness", 0.5)
        openness = self.big_five.get("openness", 0.5)
        neuroticism = self.big_five.get("neuroticism", 0.5)
        
        # Higher adventurousness and openness increase risk tolerance
        # Higher neuroticism decreases risk tolerance
        risk_tolerance = (adventurousness * 0.5) + (openness * 0.3) - (neuroticism * 0.2)
        
        return max(0.0, min(risk_tolerance, 1.0))


class PersonalityEngine:
    """
    Personality engine for managing character personality
    Local personality algorithms, not LLM-dependent
    """
    
    def __init__(self):
        self.personalities: Dict[str, Personality] = {}  # character_id -> Personality
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize personality engine"""
        self.is_initialized = True
        print("Personality Engine initialized")
    
    async def shutdown(self):
        """Shutdown personality engine"""
        self.is_initialized = False
        print("Personality Engine shutdown")
    
    async def create_personality(
        self,
        character_id: str,
        big_five: Optional[Dict[str, float]] = None,
        secondary_traits: Optional[Dict[str, float]] = None,
        quirks: Optional[List[str]] = None
    ) -> Personality:
        """Create a personality for a character"""
        
        personality = Personality(
            character_id=character_id,
            big_five=big_five,
            secondary_traits=secondary_traits,
            quirks=quirks
        )
        
        self.personalities[character_id] = personality
        return personality
    
    async def get_personality(self, character_id: str) -> Dict[str, Any]:
        """Get personality for a character"""
        
        if character_id not in self.personalities:
            # Create default personality
            await self.create_personality(character_id)
        
        return self.personalities[character_id].to_dict()
    
    async def update_trait(
        self,
        character_id: str,
        trait_name: str,
        value: float
    ):
        """Update a personality trait"""
        
        if character_id not in self.personalities:
            await self.create_personality(character_id)
        
        self.personalities[character_id].set_trait(trait_name, value)
    
    async def influence_decision(
        self,
        character_id: str,
        decision_type: str,
        options: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Influence a decision based on personality
        Local decision influence, not LLM-dependent
        """
        
        if character_id not in self.personalities:
            await self.create_personality(character_id)
        
        personality = self.personalities[character_id]
        
        # Score options based on personality
        scored_options = []
        for option in options:
            score = await self._score_option(personality, decision_type, option)
            scored_options.append((option, score))
        
        # Select best option
        scored_options.sort(key=lambda x: x[1], reverse=True)
        best_option = scored_options[0][0] if scored_options else options[0]
        
        return best_option
    
    async def _score_option(
        self,
        personality: Personality,
        decision_type: str,
        option: Dict[str, Any]
    ) -> float:
        """Score an option based on personality"""
        
        score = 0.5  # Base score
        
        # Adjust based on decision type and personality traits
        if decision_type == "social":
            extraversion = personality.get_trait("extraversion")
            agreeableness = personality.get_trait("agreeableness")
            
            if option.get("social", False):
                score += (extraversion * 0.3) + (agreeableness * 0.2)
        
        elif decision_type == "risk":
            risk_tolerance = personality.get_risk_tolerance()
            
            if option.get("risky", False):
                score += risk_tolerance * 0.4
            else:
                score += (1.0 - risk_tolerance) * 0.4
        
        elif decision_type == "learning":
            curiosity = personality.get_trait("curiosity")
            openness = personality.get_trait("openness")
            
            if option.get("educational", False):
                score += (curiosity * 0.3) + (openness * 0.2)
        
        elif decision_type == "creative":
            creativity = personality.get_trait("creativity")
            openness = personality.get_trait("openness")
            
            if option.get("creative", False):
                score += (creativity * 0.3) + (openness * 0.2)
        
        return max(0.0, min(score, 1.0))
    
    async def generate_personality_response(
        self,
        character_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate personality-influenced response parameters"""
        
        if character_id not in self.personalities:
            await self.create_personality(character_id)
        
        personality = self.personalities[character_id]
        
        return {
            "use_humor": personality.should_use_humor(),
            "be_curious": personality.should_be_curious(),
            "formality": personality.get_response_formality(),
            "risk_tolerance": personality.get_risk_tolerance(),
            "response_style": personality.response_style,
            "quirk": random.choice(personality.quirks) if personality.quirks else None
        }
    
    async def mutate_personality(
        self,
        character_id: str,
        mutation_rate: float = 0.05
    ):
        """Slightly mutate personality traits over time"""
        
        if character_id not in self.personalities:
            return
        
        personality = self.personalities[character_id]
        
        # Mutate Big Five traits
        for trait in personality.big_five:
            mutation = (random.random() - 0.5) * 2 * mutation_rate
            personality.set_trait(trait, personality.get_trait(trait) + mutation)
        
        # Mutate secondary traits
        for trait in personality.secondary_traits:
            mutation = (random.random() - 0.5) * 2 * mutation_rate
            personality.set_trait(trait, personality.get_trait(trait) + mutation)
    
    async def get_personality_summary(self, character_id: str) -> Dict[str, Any]:
        """Get personality summary"""
        
        if character_id not in self.personalities:
            await self.create_personality(character_id)
        
        personality = self.personalities[character_id]
        
        # Determine dominant traits
        dominant_big_five = max(
            personality.big_five.items(),
            key=lambda x: x[1]
        )
        
        dominant_secondary = max(
            personality.secondary_traits.items(),
            key=lambda x: x[1]
        )
        
        return {
            "dominant_big_five": dominant_big_five[0],
            "dominant_secondary": dominant_secondary[0],
            "quirk_count": len(personality.quirks),
            "overall_openness": personality.get_trait("openness"),
            "overall_stability": 1.0 - personality.get_trait("neuroticism"),
            "social_tendency": personality.get_trait("extraversion")
        }