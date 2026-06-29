"""
Emotion Engine - Manages emotion detection, expression, and memory
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
    title="Emotion Service",
    description="Manages emotion detection, expression, and memory for AI Companion",
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
class EmotionType(str):
    """Emotion types"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEAR = "fear"
    DISGUST = "disgust"
    SURPRISE = "surprise"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    BORED = "bored"
    CONFUSED = "confused"
    PROUD = "proud"
    ASHAMED = "ashamed"
    GUILTY = "guilty"
    JEALOUS = "jealous"
    LOVE = "love"
    HATE = "hate"


class EmotionDetectRequest(BaseModel):
    """Emotion detection request"""
    user_id: str = Field(..., description="User ID")
    text: Optional[str] = Field(default=None, description="Text for emotion detection")
    audio_features: Optional[Dict[str, Any]] = Field(default=None, description="Audio features for emotion detection")
    visual_features: Optional[Dict[str, Any]] = Field(default=None, description="Visual features for emotion detection")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class EmotionDetectResponse(BaseModel):
    """Emotion detection response"""
    emotion: str = Field(..., description="Detected emotion")
    confidence: float = Field(..., description="Confidence score (0-1)")
    all_emotions: Dict[str, float] = Field(..., description="All emotion scores")
    intensity: float = Field(..., description="Emotion intensity (0-1)")
    reasoning: str = Field(..., description="Reasoning for detection")


class EmotionState(BaseModel):
    """Emotion state model"""
    user_id: str = Field(..., description="User ID")
    current_emotion: str = Field(..., description="Current emotion")
    emotion_intensity: float = Field(..., description="Emotion intensity (0-1)")
    mood: float = Field(default=0.5, description="Mood score (0-1)")
    stress: float = Field(default=0.0, description="Stress level (0-1)")
    energy: float = Field(default=0.5, description="Energy level (0-1)")
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class EmotionUpdateRequest(BaseModel):
    """Emotion update request"""
    user_id: str = Field(..., description="User ID")
    emotion: str = Field(..., description="Emotion to set")
    intensity: float = Field(default=0.5, description="Emotion intensity (0-1)")
    reason: Optional[str] = Field(default=None, description="Reason for emotion change")


class EmotionMemory(BaseModel):
    """Emotion memory model"""
    user_id: str = Field(..., description="User ID")
    emotion: str = Field(..., description="Emotion")
    intensity: float = Field(..., description="Emotion intensity (0-1)")
    trigger: str = Field(..., description="What triggered the emotion")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Context")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class EmotionExpression(BaseModel):
    """Emotion expression model"""
    emotion: str = Field(..., description="Emotion to express")
    intensity: float = Field(..., description="Expression intensity (0-1)")
    facial_expression: Dict[str, float] = Field(..., description="Facial expression parameters")
    body_language: Dict[str, float] = Field(..., description="Body language parameters")
    voice_tone: Dict[str, float] = Field(..., description="Voice tone parameters")


# Emotion detector
class EmotionDetector:
    """Emotion detection from text, audio, and visual features"""
    
    def __init__(self):
        self.text_emotion_keywords = {
            "happy": ["happy", "joy", "excited", "great", "wonderful", "love", "enjoy", "amazing", "fantastic"],
            "sad": ["sad", "unhappy", "depressed", "down", "miserable", "crying", "disappointed", "heartbroken"],
            "angry": ["angry", "mad", "furious", "annoyed", "frustrated", "hate", "rage", "irritated"],
            "fear": ["scared", "afraid", "frightened", "terrified", "anxious", "worried", "nervous", "panic"],
            "surprise": ["surprised", "shocked", "amazed", "astonished", "unexpected", "wow", "incredible"],
            "excited": ["excited", "thrilled", "pumped", "enthusiastic", "eager", "can't wait"],
            "bored": ["bored", "boring", "uninterested", "dull", "tedious", "nothing to do"],
            "confused": ["confused", "puzzled", "uncertain", "unsure", "unclear", "don't understand"],
            "proud": ["proud", "accomplished", "achieved", "success", "did it", "great job"],
            "ashamed": ["ashamed", "embarrassed", "humiliated", "guilty", "regret"],
            "jealous": ["jealous", "envious", "want what they have", "unfair"],
            "love": ["love", "adore", "cherish", "care about", "deep affection"]
        }
    
    def detect_from_text(self, text: str) -> Dict[str, float]:
        """Detect emotion from text"""
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in self.text_emotion_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            
            if score > 0:
                emotion_scores[emotion] = min(score / len(keywords), 1.0)
        
        # Normalize scores
        total_score = sum(emotion_scores.values())
        if total_score > 0:
            for emotion in emotion_scores:
                emotion_scores[emotion] /= total_score
        
        return emotion_scores
    
    def detect_from_audio(self, audio_features: Dict[str, Any]) -> Dict[str, float]:
        """Detect emotion from audio features"""
        emotion_scores = {}
        
        # Placeholder: In production, use actual audio analysis
        # This would analyze pitch, tone, tempo, etc.
        
        pitch = audio_features.get("pitch", 0.5)
        energy = audio_features.get("energy", 0.5)
        tempo = audio_features.get("tempo", 0.5)
        
        # High pitch + high energy = excited/happy
        if pitch > 0.7 and energy > 0.7:
            emotion_scores["excited"] = 0.8
            emotion_scores["happy"] = 0.6
        
        # Low pitch + low energy = sad
        elif pitch < 0.3 and energy < 0.3:
            emotion_scores["sad"] = 0.8
            emotion_scores["depressed"] = 0.6
        
        # High energy + variable pitch = angry
        elif energy > 0.8 and tempo > 0.7:
            emotion_scores["angry"] = 0.7
            emotion_scores["frustrated"] = 0.5
        
        return emotion_scores
    
    def detect_from_visual(self, visual_features: Dict[str, Any]) -> Dict[str, float]:
        """Detect emotion from visual features"""
        emotion_scores = {}
        
        # Placeholder: In production, use actual visual analysis
        # This would analyze facial expressions, body language, etc.
        
        smile_intensity = visual_features.get("smile", 0.0)
        frown_intensity = visual_features.get("frown", 0.0)
        eye_openness = visual_features.get("eye_openness", 0.5)
        
        # High smile = happy
        if smile_intensity > 0.7:
            emotion_scores["happy"] = 0.8
            emotion_scores["excited"] = 0.5
        
        # High frown = sad/angry
        if frown_intensity > 0.7:
            emotion_scores["sad"] = 0.6
            emotion_scores["angry"] = 0.4
        
        # Low eye openness = bored/sleepy
        if eye_openness < 0.3:
            emotion_scores["bored"] = 0.7
            emotion_scores["tired"] = 0.5
        
        return emotion_scores
    
    def combine_emotions(
        self,
        text_emotions: Dict[str, float],
        audio_emotions: Dict[str, float],
        visual_emotions: Dict[str, float]
    ) -> Dict[str, float]:
        """Combine emotions from multiple sources"""
        combined = {}
        
        all_emotions = set(text_emotions.keys()) | set(audio_emotions.keys()) | set(visual_emotions.keys())
        
        for emotion in all_emotions:
            text_score = text_emotions.get(emotion, 0.0)
            audio_score = audio_emotions.get(emotion, 0.0)
            visual_score = visual_emotions.get(emotion, 0.0)
            
            # Weighted combination
            combined[emotion] = (text_score * 0.4 + audio_score * 0.3 + visual_score * 0.3)
        
        return combined


# Emotion expression generator
class EmotionExpressionGenerator:
    """Generate expression parameters for emotions"""
    
    def __init__(self):
        self.expression_mappings = {
            "happy": {
                "facial_expression": {
                    "smile": 0.8,
                    "eyebrow_raise": 0.3,
                    "eye_openness": 0.7
                },
                "body_language": {
                    "posture": "upright",
                    "gesture_frequency": 0.6,
                    "energy": 0.7
                },
                "voice_tone": {
                    "pitch": 0.6,
                    "energy": 0.7,
                    "tempo": 0.6
                }
            },
            "sad": {
                "facial_expression": {
                    "smile": 0.1,
                    "eyebrow_raise": 0.1,
                    "eye_openness": 0.4
                },
                "body_language": {
                    "posture": "slumped",
                    "gesture_frequency": 0.2,
                    "energy": 0.3
                },
                "voice_tone": {
                    "pitch": 0.3,
                    "energy": 0.3,
                    "tempo": 0.4
                }
            },
            "angry": {
                "facial_expression": {
                    "smile": 0.0,
                    "eyebrow_raise": 0.8,
                    "eye_openness": 0.6
                },
                "body_language": {
                    "posture": "tense",
                    "gesture_frequency": 0.8,
                    "energy": 0.9
                },
                "voice_tone": {
                    "pitch": 0.7,
                    "energy": 0.9,
                    "tempo": 0.8
                }
            },
            "excited": {
                "facial_expression": {
                    "smile": 0.9,
                    "eyebrow_raise": 0.5,
                    "eye_openness": 0.8
                },
                "body_language": {
                    "posture": "upright",
                    "gesture_frequency": 0.9,
                    "energy": 0.9
                },
                "voice_tone": {
                    "pitch": 0.8,
                    "energy": 0.9,
                    "tempo": 0.8
                }
            },
            "neutral": {
                "facial_expression": {
                    "smile": 0.2,
                    "eyebrow_raise": 0.2,
                    "eye_openness": 0.5
                },
                "body_language": {
                    "posture": "relaxed",
                    "gesture_frequency": 0.3,
                    "energy": 0.5
                },
                "voice_tone": {
                    "pitch": 0.5,
                    "energy": 0.5,
                    "tempo": 0.5
                }
            }
        }
    
    def generate_expression(self, emotion: str, intensity: float) -> EmotionExpression:
        """Generate expression parameters for an emotion"""
        base_mapping = self.expression_mappings.get(emotion, self.expression_mappings["neutral"])
        
        # Apply intensity
        facial_expression = {
            key: value * intensity
            for key, value in base_mapping["facial_expression"].items()
        }
        
        body_language = {
            key: value * intensity if isinstance(value, float) else value
            for key, value in base_mapping["body_language"].items()
        }
        
        voice_tone = {
            key: value * intensity
            for key, value in base_mapping["voice_tone"].items()
        }
        
        return EmotionExpression(
            emotion=emotion,
            intensity=intensity,
            facial_expression=facial_expression,
            body_language=body_language,
            voice_tone=voice_tone
        )


# Global instances
emotion_detector = EmotionDetector()
expression_generator = EmotionExpressionGenerator()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Emotion Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Emotion Service")


# API endpoints
@app.post("/api/v1/emotion/detect")
async def detect_emotion(request: EmotionDetectRequest) -> EmotionDetectResponse:
    """
    Detect emotion from text, audio, and/or visual features
    """
    try:
        # Detect from each source
        text_emotions = {}
        audio_emotions = {}
        visual_emotions = {}
        
        if request.text:
            text_emotions = emotion_detector.detect_from_text(request.text)
        
        if request.audio_features:
            audio_emotions = emotion_detector.detect_from_audio(request.audio_features)
        
        if request.visual_features:
            visual_emotions = emotion_detector.detect_from_visual(request.visual_features)
        
        # Combine emotions
        combined_emotions = emotion_detector.combine_emotions(
            text_emotions,
            audio_emotions,
            visual_emotions
        )
        
        # Get dominant emotion
        if combined_emotions:
            dominant_emotion = max(combined_emotions, key=combined_emotions.get)
            confidence = combined_emotions[dominant_emotion]
        else:
            dominant_emotion = "neutral"
            confidence = 0.5
        
        # Calculate intensity
        intensity = confidence
        
        # Generate reasoning
        reasoning_parts = []
        if text_emotions:
            reasoning_parts.append("text analysis")
        if audio_emotions:
            reasoning_parts.append("audio features")
        if visual_emotions:
            reasoning_parts.append("visual features")
        
        reasoning = f"Detected from {', '.join(reasoning_parts) if reasoning_parts else 'context'}"
        
        logger.info(f"Detected emotion {dominant_emotion} for user {request.user_id}")
        
        return EmotionDetectResponse(
            emotion=dominant_emotion,
            confidence=confidence,
            all_emotions=combined_emotions,
            intensity=intensity,
            reasoning=reasoning
        )
        
    except Exception as e:
        logger.error(f"Failed to detect emotion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect emotion: {str(e)}"
        )


@app.get("/api/v1/emotion/state/{user_id}")
async def get_emotion_state(user_id: str) -> EmotionState:
    """
    Get current emotion state for a user
    """
    try:
        db = await get_mongodb()
        emotion_states = db["emotion_states"]
        
        state = await emotion_states.find_one({"user_id": user_id})
        
        if not state:
            # Create default state
            state = {
                "user_id": user_id,
                "current_emotion": "neutral",
                "emotion_intensity": 0.5,
                "mood": 0.5,
                "stress": 0.0,
                "energy": 0.5,
                "last_updated": datetime.utcnow().isoformat()
            }
            await emotion_states.insert_one(state)
        
        state.pop("_id", None)
        
        return EmotionState(**state)
        
    except Exception as e:
        logger.error(f"Failed to get emotion state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get emotion state: {str(e)}"
        )


@app.put("/api/v1/emotion/state")
async def update_emotion_state(request: EmotionUpdateRequest):
    """
    Update emotion state for a user
    """
    try:
        db = await get_mongodb()
        emotion_states = db["emotion_states"]
        
        update_data = {
            "current_emotion": request.emotion,
            "emotion_intensity": request.intensity,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        if request.reason:
            update_data["reason"] = request.reason
        
        result = await emotion_states.update_one(
            {"user_id": request.user_id},
            {"$set": update_data},
            upsert=True
        )
        
        logger.info(f"Updated emotion state for user {request.user_id}")
        
        return {
            "user_id": request.user_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update emotion state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update emotion state: {str(e)}"
        )


@app.post("/api/v1/emotion/memory", status_code=status.HTTP_201_CREATED)
async def store_emotion_memory(request: EmotionMemory):
    """
    Store an emotion memory
    """
    try:
        db = await get_mongodb()
        emotion_memories = db["emotion_memories"]
        
        await emotion_memories.insert_one(request.dict())
        
        logger.info(f"Stored emotion memory for user {request.user_id}")
        
        return {
            "status": "stored",
            "timestamp": request.timestamp
        }
        
    except Exception as e:
        logger.error(f"Failed to store emotion memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store emotion memory: {str(e)}"
        )


@app.get("/api/v1/emotion/memory/{user_id}")
async def get_emotion_memories(user_id: str, limit: int = 20):
    """
    Get emotion memories for a user
    """
    try:
        db = await get_mongodb()
        emotion_memories = db["emotion_memories"]
        
        cursor = emotion_memories.find({"user_id": user_id}) \
            .sort("timestamp", -1) \
            .limit(limit)
        
        memories = []
        async for memory in cursor:
            memory.pop("_id", None)
            memories.append(memory)
        
        return {
            "user_id": user_id,
            "memories": memories,
            "count": len(memories)
        }
        
    except Exception as e:
        logger.error(f"Failed to get emotion memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get emotion memories: {str(e)}"
        )


@app.post("/api/v1/emotion/express")
async def generate_emotion_expression(emotion: str, intensity: float = 0.5) -> EmotionExpression:
    """
    Generate expression parameters for an emotion
    """
    try:
        expression = expression_generator.generate_expression(emotion, intensity)
        return expression
    except Exception as e:
        logger.error(f"Failed to generate expression: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate expression: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "emotion-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
