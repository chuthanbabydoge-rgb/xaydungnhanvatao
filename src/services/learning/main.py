"""
Learning Engine - Preference learning, pattern learning, and adaptive behavior
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from shared.database.mongodb import get_mongodb
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Learning Service",
    description="Preference learning, pattern learning, and adaptive behavior for AI Companion",
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
class UserPreference(BaseModel):
    """User preference model"""
    user_id: str = Field(..., description="User ID")
    topic: str = Field(..., description="Preference topic")
    score: float = Field(default=0.5, description="Preference score (0-1)")
    interaction_count: int = Field(default=0, description="Number of interactions")
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PreferenceObserveRequest(BaseModel):
    """Preference observation request"""
    user_id: str = Field(..., description="User ID")
    action: str = Field(..., description="User action")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Action context")


class PreferenceReactionRequest(BaseModel):
    """Preference reaction request"""
    user_id: str = Field(..., description="User ID")
    topic: str = Field(..., description="Topic of reaction")
    reaction: str = Field(..., description="Reaction type: positive, negative, neutral")
    intensity: float = Field(default=0.5, description="Reaction intensity (0-1)")


class InteractionPattern(BaseModel):
    """Interaction pattern model"""
    pattern_id: str = Field(..., description="Pattern ID")
    user_id: str = Field(..., description="User ID")
    sequence: List[str] = Field(..., description="Action sequence")
    confidence: float = Field(default=0.5, description="Pattern confidence (0-1)")
    occurrence_count: int = Field(default=1, description="Number of occurrences")
    suggested_behavior: str = Field(default="neutral", description="Suggested behavior")
    last_observed: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PatternAnalyzeRequest(BaseModel):
    """Pattern analysis request"""
    user_id: str = Field(..., description="User ID")
    interaction: Dict[str, Any] = Field(..., description="Interaction to analyze")


class AdaptiveBehaviorRequest(BaseModel):
    """Adaptive behavior request"""
    user_id: str = Field(..., description="User ID")
    topic: str = Field(..., description="Topic for adaptation")
    base_response: str = Field(..., description="Base response to adapt")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class AdaptiveBehaviorResponse(BaseModel):
    """Adaptive behavior response"""
    adapted_response: str = Field(..., description="Adapted response")
    adaptation_type: str = Field(..., description="Type of adaptation applied")
    confidence: float = Field(..., description="Confidence in adaptation (0-1)")


# Preference learning system
class PreferenceLearningSystem:
    """Learns user preferences from actions and reactions"""
    
    def __init__(self):
        self.learning_rate = 0.1
        self.decay_rate = 0.001
    
    async def observe_action(self, user_id: str, action: str, context: Optional[Dict[str, Any]]) -> List[str]:
        """Extract preferences from user actions"""
        # Extract topics from action
        topics = self._extract_topics(action, context)
        
        return topics
    
    def _extract_topics(self, action: str, context: Optional[Dict[str, Any]]) -> List[str]:
        """Extract topics from action and context"""
        topics = []
        
        # Simple keyword extraction
        words = action.lower().split()
        
        # Common topic keywords
        topic_keywords = {
            "anime": ["anime", "manga", "one piece", "naruto", "dragon ball"],
            "music": ["music", "song", "spotify", "listen", "play"],
            "gaming": ["game", "play", "gaming", "steam", "console"],
            "coding": ["code", "programming", "development", "python", "javascript"],
            "reading": ["read", "book", "novel", "manga", "article"],
            "cooking": ["cook", "recipe", "food", "meal", "kitchen"],
            "fitness": ["exercise", "workout", "gym", "fitness", "run"],
            "travel": ["travel", "trip", "vacation", "destination", "visit"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in words for keyword in keywords):
                topics.append(topic)
        
        # Extract from context
        if context:
            for key, value in context.items():
                if isinstance(value, str):
                    for topic, keywords in topic_keywords.items():
                        if any(keyword in value.lower() for keyword in keywords):
                            if topic not in topics:
                                topics.append(topic)
        
        return topics
    
    async def update_preference(self, user_id: str, topic: str, delta: float) -> UserPreference:
        """Update preference score for a topic"""
        db = await get_mongodb()
        preferences = db["user_preferences"]
        
        # Get existing preference
        existing = await preferences.find_one({"user_id": user_id, "topic": topic})
        
        if existing:
            # Update existing preference
            new_score = existing["score"] + delta
            new_score = max(0.0, min(1.0, new_score))
            
            await preferences.update_one(
                {"user_id": user_id, "topic": topic},
                {
                    "$set": {
                        "score": new_score,
                        "interaction_count": existing["interaction_count"] + 1,
                        "last_updated": datetime.utcnow().isoformat()
                    }
                }
            )
            
            return UserPreference(
                user_id=user_id,
                topic=topic,
                score=new_score,
                interaction_count=existing["interaction_count"] + 1,
                last_updated=datetime.utcnow().isoformat()
            )
        else:
            # Create new preference
            new_score = max(0.0, min(1.0, 0.5 + delta))
            
            preference = UserPreference(
                user_id=user_id,
                topic=topic,
                score=new_score,
                interaction_count=1,
                last_updated=datetime.utcnow().isoformat()
            )
            
            await preferences.insert_one(preference.dict())
            
            return preference
    
    async def get_preference_score(self, user_id: str, topic: str) -> float:
        """Get preference score for a topic"""
        db = await get_mongodb()
        preferences = db["user_preferences"]
        
        preference = await preferences.find_one({"user_id": user_id, "topic": topic})
        
        if preference:
            return preference["score"]
        
        return 0.5  # Default neutral score
    
    async def get_top_preferences(self, user_id: str, count: int = 10) -> List[UserPreference]:
        """Get top preferences for a user"""
        db = await get_mongodb()
        preferences = db["user_preferences"]
        
        cursor = preferences.find({"user_id": user_id}) \
            .sort("score", -1) \
            .limit(count)
        
        result = []
        async for pref in cursor:
            pref.pop("_id", None)
            result.append(UserPreference(**pref))
        
        return result


# Pattern learning system
class PatternLearningSystem:
    """Detects and learns interaction patterns"""
    
    def __init__(self):
        self.pattern_confidence_threshold = 0.7
        self.min_occurrence_count = 3
    
    async def analyze_interaction(self, user_id: str, interaction: Dict[str, Any]) -> List[InteractionPattern]:
        """Analyze interaction for patterns"""
        db = await get_mongodb()
        patterns = db["interaction_patterns"]
        
        detected_patterns = []
        
        # Get existing patterns
        cursor = patterns.find({"user_id": user_id})
        existing_patterns = []
        async for pattern in cursor:
            pattern.pop("_id", None)
            existing_patterns.append(InteractionPattern(**pattern))
        
        # Check if interaction matches existing patterns
        for pattern in existing_patterns:
            if self._matches_pattern(interaction, pattern):
                # Confirm pattern
                new_confidence = min(1.0, pattern.confidence + 0.1)
                new_count = pattern.occurrence_count + 1
                
                await patterns.update_one(
                    {"pattern_id": pattern.pattern_id},
                    {
                        "$set": {
                            "confidence": new_confidence,
                            "occurrence_count": new_count,
                            "last_observed": datetime.utcnow().isoformat()
                        }
                    }
                )
                
                pattern.confidence = new_confidence
                pattern.occurrence_count = new_count
                pattern.last_observed = datetime.utcnow().isoformat()
                
                if new_confidence >= self.pattern_confidence_threshold:
                    detected_patterns.append(pattern)
        
        # Try to create new pattern
        new_pattern = self._try_create_pattern(user_id, interaction, existing_patterns)
        if new_pattern:
            await patterns.insert_one(new_pattern.dict())
            detected_patterns.append(new_pattern)
        
        return detected_patterns
    
    def _matches_pattern(self, interaction: Dict[str, Any], pattern: InteractionPattern) -> bool:
        """Check if interaction matches a pattern"""
        # Simple matching based on action type
        interaction_action = interaction.get("action", "")
        pattern_sequence = pattern.sequence
        
        return interaction_action in pattern_sequence
    
    def _try_create_pattern(
        self,
        user_id: str,
        interaction: Dict[str, Any],
        existing_patterns: List[InteractionPattern]
    ) -> Optional[InteractionPattern]:
        """Try to create a new pattern from interaction"""
        import uuid
        
        # Check if similar pattern already exists
        interaction_action = interaction.get("action", "")
        
        for pattern in existing_patterns:
            if interaction_action in pattern.sequence:
                return None  # Pattern already exists
        
        # Create new pattern
        suggested_behavior = self._suggest_behavior(interaction)
        
        new_pattern = InteractionPattern(
            pattern_id=str(uuid.uuid4()),
            user_id=user_id,
            sequence=[interaction_action],
            confidence=0.3,
            occurrence_count=1,
            suggested_behavior=suggested_behavior
        )
        
        return new_pattern
    
    def _suggest_behavior(self, interaction: Dict[str, Any]) -> str:
        """Suggest behavior based on interaction"""
        action = interaction.get("action", "").lower()
        
        behavior_mapping = {
            "ask": "helpful",
            "request": "helpful",
            "greet": "friendly",
            "goodbye": "polite",
            "complain": "empathetic",
            "praise": "grateful",
            "question": "informative",
            "command": "obedient"
        }
        
        for keyword, behavior in behavior_mapping.items():
            if keyword in action:
                return behavior
        
        return "neutral"
    
    async def get_patterns(self, user_id: str) -> List[InteractionPattern]:
        """Get confirmed patterns for a user"""
        db = await get_mongodb()
        patterns = db["interaction_patterns"]
        
        cursor = patterns.find({
            "user_id": user_id,
            "confidence": {"$gte": self.pattern_confidence_threshold}
        })
        
        result = []
        async for pattern in cursor:
            pattern.pop("_id", None)
            result.append(InteractionPattern(**pattern))
        
        return result


# Adaptive behavior system
class AdaptiveBehaviorSystem:
    """Adapts behavior based on learned preferences and patterns"""
    
    def __init__(self):
        self.adaptation_rate = 0.05
    
    async def adapt_response(
        self,
        user_id: str,
        topic: str,
        base_response: str,
        context: Optional[Dict[str, Any]]
    ) -> AdaptiveBehaviorResponse:
        """Adapt response based on preferences"""
        preference_learning = PreferenceLearningSystem()
        pattern_learning = PatternLearningSystem()
        
        # Get preference score
        preference_score = await preference_learning.get_preference_score(user_id, topic)
        
        # Get patterns
        patterns = await pattern_learning.get_patterns(user_id)
        
        # Adapt response
        if preference_score > 0.7:
            adapted_response = self._enthusiastic_response(base_response)
            adaptation_type = "enthusiastic"
            confidence = preference_score
        elif preference_score < 0.3:
            adapted_response = self._cautious_response(base_response)
            adaptation_type = "cautious"
            confidence = 1.0 - preference_score
        else:
            adapted_response = base_response
            adaptation_type = "neutral"
            confidence = 0.5
        
        # Apply pattern-based adaptation
        for pattern in patterns:
            if pattern.suggested_behavior != "neutral":
                adapted_response = self._apply_behavior_style(adapted_response, pattern.suggested_behavior)
                adaptation_type = f"pattern_{pattern.suggested_behavior}"
                confidence = pattern.confidence
                break
        
        return AdaptiveBehaviorResponse(
            adapted_response=adapted_response,
            adaptation_type=adaptation_type,
            confidence=confidence
        )
    
    def _enthusiastic_response(self, base_response: str) -> str:
        """Make response more enthusiastic"""
        enthusiastic_prefixes = [
            "Great! ",
            "Awesome! ",
            "Wonderful! ",
            "Fantastic! ",
            "Excellent! "
        ]
        
        import random
        prefix = random.choice(enthusiastic_prefixes)
        
        return prefix + base_response
    
    def _cautious_response(self, base_response: str) -> str:
        """Make response more cautious"""
        cautious_prefixes = [
            "I think ",
            "It seems like ",
            "Based on what I know, ",
            "From my understanding, ",
            "If I'm not mistaken, "
        ]
        
        import random
        prefix = random.choice(cautious_prefixes)
        
        return prefix + base_response
    
    def _apply_behavior_style(self, response: str, behavior: str) -> str:
        """Apply specific behavior style to response"""
        style_modifiers = {
            "helpful": "I'd be happy to help with that. " + response,
            "friendly": "Hey there! " + response,
            "polite": "Thank you for asking. " + response,
            "empathetic": "I understand how you feel. " + response,
            "grateful": "Thank you! " + response,
            "informative": "Here's what I know: " + response,
            "obedient": "Of course. " + response
        }
        
        return style_modifiers.get(behavior, response)


# Global instances
preference_learning = PreferenceLearningSystem()
pattern_learning = PatternLearningSystem()
adaptive_behavior = AdaptiveBehaviorSystem()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Learning Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Learning Service")


# API endpoints
@app.post("/api/v1/learning/observe-action")
async def observe_action(request: PreferenceObserveRequest):
    """
    Observe user action and extract preferences
    """
    try:
        topics = await preference_learning.observe_action(
            request.user_id,
            request.action,
            request.context
        )
        
        # Update preferences for extracted topics
        for topic in topics:
            await preference_learning.update_preference(request.user_id, topic, 0.1)
        
        logger.info(f"Observed action for user {request.user_id}, extracted topics: {topics}")
        
        return {
            "user_id": request.user_id,
            "topics_extracted": topics,
            "preferences_updated": len(topics)
        }
        
    except Exception as e:
        logger.error(f"Failed to observe action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to observe action: {str(e)}"
        )


@app.post("/api/v1/learning/react")
async def react_to_topic(request: PreferenceReactionRequest):
    """
    Record user reaction to a topic
    """
    try:
        delta = 0.0
        
        if request.reaction == "positive":
            delta = request.intensity * 0.2
        elif request.reaction == "negative":
            delta = -request.intensity * 0.2
        else:  # neutral
            delta = 0.0
        
        preference = await preference_learning.update_preference(
            request.user_id,
            request.topic,
            delta
        )
        
        logger.info(f"Recorded reaction for user {request.user_id} to topic {request.topic}")
        
        return {
            "user_id": request.user_id,
            "topic": request.topic,
            "reaction": request.reaction,
            "new_score": preference.score
        }
        
    except Exception as e:
        logger.error(f"Failed to record reaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record reaction: {str(e)}"
        )


@app.get("/api/v1/learning/preferences/{user_id}")
async def get_preferences(user_id: str, limit: int = 20):
    """
    Get user preferences
    """
    try:
        preferences = await preference_learning.get_top_preferences(user_id, limit)
        
        return {
            "user_id": user_id,
            "preferences": [pref.dict() for pref in preferences],
            "count": len(preferences)
        }
        
    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get preferences: {str(e)}"
        )


@app.post("/api/v1/learning/analyze-pattern")
async def analyze_pattern(request: PatternAnalyzeRequest):
    """
    Analyze interaction for patterns
    """
    try:
        patterns = await pattern_learning.analyze_interaction(
            request.user_id,
            request.interaction
        )
        
        logger.info(f"Analyzed pattern for user {request.user_id}")
        
        return {
            "user_id": request.user_id,
            "patterns": [pattern.dict() for pattern in patterns],
            "count": len(patterns)
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze pattern: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze pattern: {str(e)}"
        )


@app.get("/api/v1/learning/patterns/{user_id}")
async def get_patterns(user_id: str):
    """
    Get confirmed patterns for a user
    """
    try:
        patterns = await pattern_learning.get_patterns(user_id)
        
        return {
            "user_id": user_id,
            "patterns": [pattern.dict() for pattern in patterns],
            "count": len(patterns)
        }
        
    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patterns: {str(e)}"
        )


@app.post("/api/v1/learning/adapt")
async def adapt_behavior(request: AdaptiveBehaviorRequest) -> AdaptiveBehaviorResponse:
    """
    Adapt behavior based on learned preferences and patterns
    """
    try:
        response = await adaptive_behavior.adapt_response(
            request.user_id,
            request.topic,
            request.base_response,
            request.context
        )
        
        logger.info(f"Adapted behavior for user {request.user_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to adapt behavior: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to adapt behavior: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "learning-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
