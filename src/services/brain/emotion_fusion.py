"""
Emotion Fusion Engine - Multi-source Emotion Integration
Local emotion fusion algorithms, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
import math
from datetime import datetime


class EmotionType(Enum):
    """Types of emotions"""
    HAPPINESS = "happiness"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    DISGUST = "disgust"
    SURPRISE = "surprise"
    CURIOSITY = "curiosity"
    EXCITEMENT = "excitement"
    BOREDOM = "boredom"
    CALM = "calm"
    ANXIETY = "anxiety"
    LOVE = "love"
    HATE = "hate"
    PRIDE = "pride"
    SHAME = "shame"


class EmotionSource(Enum):
    """Sources of emotions"""
    NEEDS = "needs"  # From need satisfaction
    PERSONALITY = "personality"  # From personality traits
    SOCIAL = "social"  # From social interactions
    STIMULUS = "stimulus"  # From external stimuli
    MEMORY = "memory"  # From recalled memories
    BASELINE = "baseline"  # Baseline emotional state


class EmotionState:
    """Represents current emotional state - ENHANCED LOCAL PROCESSING"""
    def __init__(self, character_id: str):
        self.character_id = character_id
        self.emotions: Dict[EmotionType, float] = {
            emotion: 0.0 for emotion in EmotionType
        }
        self.mood = 0.5  # Overall mood (-1.0 to 1.0)
        self.arousal = 0.5  # Arousal level (0.0 to 1.0)
        self.last_updated = datetime.utcnow()
        
        # Enhanced emotion dynamics
        self.emotion_history: List[Dict[str, Any]] = []  # Track emotion changes
        self.emotion_intensity_trend: Dict[EmotionType, float] = {}  # Track intensity trends
        self.emotional_stability = 0.8  # How stable emotions are
        self.emotional_reactivity = 0.5  # How reactive to stimuli
        self.emotional_conflicts: List[Tuple[EmotionType, EmotionType]] = []  # Conflicting emotions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "emotions": {e.value: v for e, v in self.emotions.items()},
            "mood": self.mood,
            "arousal": self.arousal,
            "last_updated": self.last_updated.isoformat()
        }
    
    def set_emotion(self, emotion: EmotionType, value: float):
        """Set an emotion value with enhanced local tracking"""
        old_value = self.emotions.get(emotion, 0.0)
        self.emotions[emotion] = max(0.0, min(value, 1.0))
        self.last_updated = datetime.utcnow()
        
        # Track emotion history
        self.emotion_history.append({
            "emotion": emotion.value,
            "old_value": old_value,
            "new_value": value,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep history limited
        if len(self.emotion_history) > 100:
            self.emotion_history.pop(0)
        
        # Update intensity trend
        self._update_intensity_trend(emotion, old_value, value)
        
        # Check for emotional conflicts
        self._check_emotional_conflicts()
        
        # Update emotional stability
        self._update_emotional_stability()
    
    def _update_intensity_trend(self, emotion: EmotionType, old_value: float, new_value: float):
        """Update intensity trend for an emotion"""
        if emotion not in self.emotion_intensity_trend:
            self.emotion_intensity_trend[emotion] = 0.0
        
        # Calculate trend (positive = increasing, negative = decreasing)
        trend = new_value - old_value
        
        # Smooth the trend using exponential moving average
        alpha = 0.3
        self.emotion_intensity_trend[emotion] = (alpha * trend) + ((1 - alpha) * self.emotion_intensity_trend[emotion])
    
    def _check_emotional_conflicts(self):
        """Check for conflicting emotions using local analysis"""
        self.emotional_conflicts = []
        
        # Define emotion pairs that can conflict
        conflict_pairs = [
            (EmotionType.HAPPINESS, EmotionType.SADNESS),
            (EmotionType.HAPPINESS, EmotionType.ANGER),
            (EmotionType.LOVE, EmotionType.HATE),
            (EmotionType.CALM, EmotionType.ANXIETY),
            (EmotionType.EXCITEMENT, EmotionType.BOREDOM),
            (EmotionType.PRIDE, EmotionType.SHAME)
        ]
        
        for emotion1, emotion2 in conflict_pairs:
            value1 = self.emotions.get(emotion1, 0.0)
            value2 = self.emotions.get(emotion2, 0.0)
            
            # Both emotions are strong (> 0.6)
            if value1 > 0.6 and value2 > 0.6:
                self.emotional_conflicts.append((emotion1, emotion2))
    
    def _update_emotional_stability(self):
        """Update emotional stability based on volatility"""
        if len(self.emotion_history) < 10:
            return
        
        # Calculate volatility from recent history
        recent_history = self.emotion_history[-10:]
        changes = [abs(entry["new_value"] - entry["old_value"]) for entry in recent_history]
        
        if changes:
            avg_volatility = sum(changes) / len(changes)
            # Higher volatility = lower stability
            self.emotional_stability = max(0.1, 1.0 - avg_volatility * 2)
    
    def resolve_emotional_conflicts(self):
        """Resolve emotional conflicts using local balancing"""
        for emotion1, emotion2 in self.emotional_conflicts:
            value1 = self.emotions.get(emotion1, 0.0)
            value2 = self.emotions.get(emotion2, 0.0)
            
            # Reduce the stronger emotion slightly
            if value1 > value2:
                self.emotions[emotion1] = max(0.0, value1 * 0.9)
            else:
                self.emotions[emotion2] = max(0.0, value2 * 0.9)
        
        # Re-check conflicts
        self._check_emotional_conflicts()
    
    def get_emotional_complexity(self) -> float:
        """Calculate emotional complexity using local analysis"""
        # Count emotions above threshold
        significant_emotions = sum(1 for v in self.emotions.values() if v > 0.3)
        
        # Calculate emotional variance
        emotion_values = list(self.emotions.values())
        if emotion_values:
            mean = sum(emotion_values) / len(emotion_values)
            variance = sum((v - mean) ** 2 for v in emotion_values) / len(emotion_values)
            complexity = (significant_emotions / len(EmotionType)) + math.sqrt(variance)
        else:
            complexity = 0.0
        
        return min(complexity, 1.0)
    
    def adjust_emotion(self, emotion: EmotionType, amount: float):
        """Adjust an emotion value"""
        current = self.emotions.get(emotion, 0.0)
        self.emotions[emotion] = max(0.0, min(current + amount, 1.0))
        self.last_updated = datetime.utcnow()
    
    def get_dominant_emotion(self) -> tuple:
        """Get the dominant emotion"""
        return max(self.emotions.items(), key=lambda x: x[1])


class EmotionFusion:
    """
    Emotion fusion engine for integrating emotions from multiple sources
    Local emotion fusion, not LLM-dependent
    """
    
    def __init__(self):
        self.emotion_states: Dict[str, EmotionState] = {}  # character_id -> EmotionState
        self.need_system = None
        self.personality = None
        self.social_system = None
        self.is_initialized = False
    
    def set_need_system(self, need_system):
        """Set need system dependency"""
        self.need_system = need_system
    
    def set_personality(self, personality):
        """Set personality engine dependency"""
        self.personality = personality
    
    def set_social_system(self, social_system):
        """Set social system dependency"""
        self.social_system = social_system
    
    async def initialize(self):
        """Initialize emotion fusion engine"""
        self.is_initialized = True
        print("Emotion Fusion initialized")
    
    async def shutdown(self):
        """Shutdown emotion fusion engine"""
        self.is_initialized = False
        print("Emotion Fusion shutdown")
    
    async def process_stimulus(
        self,
        character_id: str,
        stimulus: Any,
        memories: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Process stimulus and update emotions
        Local emotion processing, not LLM-dependent
        """
        
        # Get or create emotion state
        emotion_state = await self._get_or_create_emotion_state(character_id)
        
        # Get emotions from different sources
        need_emotions = await self._get_emotions_from_needs(character_id)
        personality_emotions = await self._get_emotions_from_personality(character_id)
        social_emotions = await self._get_emotions_from_social(character_id)
        stimulus_emotions = await self._get_emotions_from_stimulus(stimulus)
        memory_emotions = await self._get_emotions_from_memory(memories)
        
        # Fuse emotions using weighted average
        fused_emotions = await self._fuse_emotions(
            {
                EmotionSource.NEEDS: need_emotions,
                EmotionSource.PERSONALITY: personality_emotions,
                EmotionSource.SOCIAL: social_emotions,
                EmotionSource.STIMULUS: stimulus_emotions,
                EmotionSource.MEMORY: memory_emotions
            }
        )
        
        # Update emotion state
        for emotion, value in fused_emotions.items():
            emotion_state.set_emotion(emotion, value)
        
        # Update mood and arousal
        await self._update_mood_and_arousal(emotion_state)
        
        # Apply emotion decay
        await self._apply_emotion_decay(emotion_state)
        
        return {e.value: v for e, v in emotion_state.emotions.items()}
    
    async def _get_or_create_emotion_state(self, character_id: str) -> EmotionState:
        """Get or create emotion state for character"""
        
        if character_id not in self.emotion_states:
            self.emotion_states[character_id] = EmotionState(character_id)
        
        return self.emotion_states[character_id]
    
    async def _get_emotions_from_needs(self, character_id: str) -> Dict[EmotionType, float]:
        """Get emotions based on need satisfaction"""
        
        emotions = {e: 0.0 for e in EmotionType}
        
        if not self.need_system:
            return emotions
        
        needs = await self.need_system.get_needs(character_id)
        
        # Map needs to emotions
        need_emotion_mapping = {
            "energy": (EmotionType.BOREDOM, -1.0),  # Low energy -> boredom
            "comfort": (EmotionType.CALM, 1.0),  # High comfort -> calm
            "security": (EmotionType.FEAR, -1.0),  # Low security -> fear
            "belonging": (EmotionType.SADNESS, -1.0),  # Low belonging -> sadness
            "affection": (EmotionType.LOVE, 1.0),  # High affection -> love
            "respect": (EmotionType.PRIDE, 1.0),  # High respect -> pride
            "achievement": (EmotionType.EXCITEMENT, 1.0),  # High achievement -> excitement
            "growth": (EmotionType.CURIOSITY, 1.0),  # High growth -> curiosity
        }
        
        for need_name, need_data in needs.items():
            if need_name in need_emotion_mapping:
                emotion_type, direction = need_emotion_mapping[need_name]
                need_level = need_data.get("current_level", 0.5)
                urgency = need_data.get("urgency", 0.0)
                
                # Emotion based on need level and urgency
                if direction > 0:
                    # Positive emotion increases with need satisfaction
                    emotion_value = need_level * 0.7
                else:
                    # Negative emotion increases with need urgency
                    emotion_value = urgency * 0.8
                
                emotions[emotion_type] = max(emotions[emotion_type], emotion_value)
        
        return emotions
    
    async def _get_emotions_from_personality(self, character_id: str) -> Dict[EmotionType, float]:
        """Get emotions based on personality traits"""
        
        emotions = {e: 0.0 for e in EmotionType}
        
        if not self.personality:
            return emotions
        
        personality = await self.personality.get_personality(character_id)
        
        # Map personality traits to baseline emotions
        personality_emotion_mapping = {
            "extraversion": (EmotionType.EXCITEMENT, 0.3),
            "neuroticism": (EmotionType.ANXIETY, 0.4),
            "agreeableness": (EmotionType.LOVE, 0.2),
            "openness": (EmotionType.CURIOSITY, 0.3),
            "conscientiousness": (EmotionType.PRIDE, 0.2),
            "humor": (EmotionType.HAPPINESS, 0.3),
            "optimism": (EmotionType.HAPPINESS, 0.4),
            "empathy": (EmotionType.LOVE, 0.3)
        }
        
        for trait, trait_value in personality.get("big_five", {}).items():
            if trait in personality_emotion_mapping:
                emotion_type, baseline = personality_emotion_mapping[trait]
                emotions[emotion_type] = baseline * trait_value
        
        for trait, trait_value in personality.get("secondary_traits", {}).items():
            if trait in personality_emotion_mapping:
                emotion_type, baseline = personality_emotion_mapping[trait]
                emotions[emotion_type] = max(emotions[emotion_type], baseline * trait_value)
        
        return emotions
    
    async def _get_emotions_from_social(self, character_id: str) -> Dict[EmotionType, float]:
        """Get emotions based on social relationships"""
        
        emotions = {e: 0.0 for e in EmotionType}
        
        if not self.social_system:
            return emotions
        
        social_state = await self.social_system.get_social_state(character_id)
        
        # Social emotions based on relationship quality
        avg_trust = social_state.get("average_trust", 0.5)
        avg_affinity = social_state.get("average_affinity", 0.5)
        
        # High trust and affinity -> positive social emotions
        emotions[EmotionType.LOVE] = avg_affinity * 0.5
        emotions[EmotionType.HAPPINESS] = (avg_trust + avg_affinity) / 2 * 0.4
        
        # Many relationships -> social excitement
        total_relationships = social_state.get("total_relationships", 0)
        if total_relationships > 5:
            emotions[EmotionType.EXCITEMENT] = 0.3
        
        return emotions
    
    async def _get_emotions_from_stimulus(self, stimulus: Any) -> Dict[EmotionType, float]:
        """Get emotions based on stimulus"""
        
        emotions = {e: 0.0 for e in EmotionType}
        
        if not hasattr(stimulus, 'content'):
            return emotions
        
        content = str(stimulus.content).lower()
        
        # Simple keyword-based emotion detection
        emotion_keywords = {
            EmotionType.HAPPINESS: ["happy", "joy", "great", "wonderful", "love", "fun"],
            EmotionType.SADNESS: ["sad", "unhappy", "depressed", "sorry", "tragic"],
            EmotionType.ANGER: ["angry", "mad", "furious", "hate", "annoyed"],
            EmotionType.FEAR: ["scared", "afraid", "fear", "terrified", "worried"],
            EmotionType.SURPRISE: ["surprised", "shocked", "amazed", "unexpected"],
            EmotionType.CURIOSITY: ["curious", "wonder", "interested", "how", "why"],
            EmotionType.EXCITEMENT: ["excited", "thrilled", "eager", "can't wait"],
            EmotionType.BOREDOM: ["bored", "boring", "dull", "uninteresting"],
            EmotionType.LOVE: ["love", "adore", "cherish", "care"]
        }
        
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in content:
                    emotions[emotion] = max(emotions[emotion], 0.6)
        
        return emotions
    
    async def _get_emotions_from_memory(self, memories: List[Dict[str, Any]]) -> Dict[EmotionType, float]:
        """Get emotions based on recalled memories"""
        
        emotions = {e: 0.0 for e in EmotionType}
        
        if not memories:
            return emotions
        
        # Emotional valence from memories
        for memory in memories:
            valence = memory.get("emotional_valence", 0.0)
            
            if valence > 0.5:
                emotions[EmotionType.HAPPINESS] = max(emotions[EmotionType.HAPPINESS], valence * 0.3)
            elif valence < -0.5:
                emotions[EmotionType.SADNESS] = max(emotions[EmotionType.SADNESS], abs(valence) * 0.3)
        
        return emotions
    
    async def _fuse_emotions(
        self,
        source_emotions: Dict[EmotionSource, Dict[EmotionType, float]]
    ) -> Dict[EmotionType, float]:
        """Fuse emotions from multiple sources"""
        
        # Source weights
        source_weights = {
            EmotionSource.STIMULUS: 0.4,  # Immediate stimulus has highest weight
            EmotionSource.NEEDS: 0.25,  # Needs are important
            EmotionSource.SOCIAL: 0.15,  # Social context
            EmotionSource.PERSONALITY: 0.1,  # Personality baseline
            EmotionSource.MEMORY: 0.1  # Memory influence
        }
        
        fused_emotions = {e: 0.0 for e in EmotionType}
        
        # Weighted sum
        for source, emotions in source_emotions.items():
            weight = source_weights.get(source, 0.1)
            for emotion, value in emotions.items():
                fused_emotions[emotion] += value * weight
        
        # Normalize
        max_emotion = max(fused_emotions.values()) if fused_emotions else 1.0
        if max_emotion > 1.0:
            for emotion in fused_emotions:
                fused_emotions[emotion] /= max_emotion
        
        return fused_emotions
    
    async def _update_mood_and_arousal(self, emotion_state: EmotionState):
        """Update overall mood and arousal based on emotions"""
        
        # Calculate mood (positive vs negative emotions)
        positive_emotions = [EmotionType.HAPPINESS, EmotionType.EXCITEMENT, 
                           EmotionType.LOVE, EmotionType.PRIDE, EmotionType.CURIOSITY]
        negative_emotions = [EmotionType.SADNESS, EmotionType.ANGER, 
                          EmotionType.FEAR, EmotionType.DISGUST, EmotionType.SHAME]
        
        positive_sum = sum(emotion_state.emotions[e] for e in positive_emotions)
        negative_sum = sum(emotion_state.emotions[e] for e in negative_emotions)
        
        # Mood: -1.0 (very negative) to 1.0 (very positive)
        total = positive_sum + negative_sum
        if total > 0:
            emotion_state.mood = (positive_sum - negative_sum) / total
        else:
            emotion_state.mood = 0.0
        
        # Calculate arousal (high vs low energy emotions)
        high_arousal = [EmotionType.EXCITEMENT, EmotionType.ANGER, 
                        EmotionType.FEAR, EmotionType.SURPRISE]
        low_arousal = [EmotionType.CALM, EmotionType.BOREDOM, EmotionType.SADNESS]
        
        high_arousal_sum = sum(emotion_state.emotions[e] for e in high_arousal)
        low_arousal_sum = sum(emotion_state.emotions[e] for e in low_arousal)
        
        # Arousal: 0.0 (calm) to 1.0 (excited)
        total_arousal = high_arousal_sum + low_arousal_sum
        if total_arousal > 0:
            emotion_state.arousal = high_arousal_sum / total_arousal
        else:
            emotion_state.arousal = 0.5
    
    async def _apply_emotion_decay(self, emotion_state: EmotionState):
        """Apply decay to emotions over time"""
        
        time_since_update = (datetime.utcnow() - emotion_state.last_updated).total_seconds()
        
        # Decay rate per second
        decay_rate = 0.01
        
        for emotion in emotion_state.emotions:
            # Decay emotion
            decay_amount = time_since_update * decay_rate
            emotion_state.emotions[emotion] = max(0.0, 
                emotion_state.emotions[emotion] - decay_amount)
        
        emotion_state.last_updated = datetime.utcnow()
    
    async def get_emotions(self, character_id: str) -> Dict[str, float]:
        """Get current emotions for a character"""
        
        if character_id not in self.emotion_states:
            await self._get_or_create_emotion_state(character_id)
        
        return self.emotion_states[character_id].to_dict()
    
    async def set_emotion(self, character_id: str, emotion: str, value: float):
        """Manually set an emotion"""
        
        emotion_state = await self._get_or_create_emotion_state(character_id)
        
        try:
            emotion_type = EmotionType(emotion)
            emotion_state.set_emotion(emotion_type, value)
        except ValueError:
            pass  # Invalid emotion type
    
    async def adjust_emotion(self, character_id: str, emotion: str, amount: float):
        """Adjust an emotion by amount"""
        
        emotion_state = await self._get_or_create_emotion_state(character_id)
        
        try:
            emotion_type = EmotionType(emotion)
            emotion_state.adjust_emotion(emotion_type, amount)
        except ValueError:
            pass  # Invalid emotion type
    
    async def get_emotion_summary(self, character_id: str) -> Dict[str, Any]:
        """Get summary of emotional state"""
        
        if character_id not in self.emotion_states:
            await self._get_or_create_emotion_state(character_id)
        
        emotion_state = self.emotion_states[character_id]
        dominant_emotion, dominant_value = emotion_state.get_dominant_emotion()
        
        return {
            "dominant_emotion": dominant_emotion.value,
            "dominant_intensity": dominant_value,
            "mood": emotion_state.mood,
            "arousal": emotion_state.arousal,
            "emotional_stability": 1.0 - emotion_state.emotions.get(EmotionType.ANXIETY, 0.0)
        }