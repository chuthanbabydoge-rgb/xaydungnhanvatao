"""
Emotion Agent - Emotional processing and state management
Processes emotional data, manages emotional states, and provides emotional insights
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import math

from ...core.agent_base import BaseAgent, AgentMessage, MessageType


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
    PRIDE = "shame"
    GRATITUDE = "gratitude"


class EmotionIntensity(Enum):
    """Emotion intensity levels"""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 1.0


@dataclass
class EmotionalState:
    """Represents an emotional state"""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""  # ID of the entity (user, character, etc.)
    emotions: Dict[EmotionType, float] = field(default_factory=dict)
    mood: float = 0.5  # Overall mood (-1.0 to 1.0)
    arousal: float = 0.5  # Arousal level (0.0 to 1.0)
    valence: float = 0.5  # Valence (0.0 negative to 1.0 positive)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.5
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "entity_id": self.entity_id,
            "emotions": {e.value: v for e, v in self.emotions.items()},
            "mood": self.mood,
            "arousal": self.arousal,
            "valence": self.valence,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "context": self.context
        }


@dataclass
class EmotionEvent:
    """Represents an emotion-related event"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    event_type: str = ""  # stimulus, response, transition, etc.
    trigger: str = ""
    emotional_impact: Dict[EmotionType, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "entity_id": self.entity_id,
            "event_type": self.event_type,
            "trigger": self.trigger,
            "emotional_impact": {e.value: v for e, v in self.emotional_impact.items()},
            "timestamp": self.timestamp.isoformat(),
            "duration": str(self.duration) if self.duration else None,
            "metadata": self.metadata
        }


class EmotionAgent(BaseAgent):
    """
    Emotion Agent - Processes emotional data and manages emotional states
    Analyzes emotions, tracks emotional changes, and provides emotional insights
    """
    
    def __init__(
        self,
        agent_id: str = "emotion-agent-1",
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        enable_tracing: bool = True,
        enable_metrics: bool = True
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="emotion",
            rabbitmq_url=rabbitmq_url,
            enable_tracing=enable_tracing,
            enable_metrics=enable_metrics
        )
        
        # Emotional state storage
        self.emotional_states: Dict[str, EmotionalState] = {}  # entity_id -> state
        self.emotion_history: Dict[str, List[EmotionalState]] = {}  # entity_id -> history
        self.emotion_events: List[EmotionEvent] = []
        
        # Emotion processing models
        self.emotion_models = self._load_emotion_models()
        
        # Capabilities
        self.capabilities = [
            "emotion_detection",
            "emotion_analysis",
            "emotion_tracking",
            "emotion_prediction",
            "emotion_regulation",
            "sentiment_analysis"
        ]
    
    def _load_emotion_models(self) -> Dict[str, Any]:
        """Load emotion processing models"""
        return {
            "emotion_keywords": {
                EmotionType.HAPPINESS: ["happy", "joy", "great", "wonderful", "love", "excited"],
                EmotionType.SADNESS: ["sad", "unhappy", "depressed", "sorry", "tragic", "disappointed"],
                EmotionType.ANGER: ["angry", "mad", "furious", "hate", "annoyed", "frustrated"],
                EmotionType.FEAR: ["scared", "afraid", "fear", "terrified", "worried", "anxious"],
                EmotionType.SURPRISE: ["surprised", "shocked", "amazed", "unexpected", "astonished"],
                EmotionType.CURIOSITY: ["curious", "wonder", "interested", "how", "why", "intrigued"],
                EmotionType.EXCITEMENT: ["excited", "thrilled", "eager", "can't wait", "enthusiastic"],
                EmotionType.BOREDOM: ["bored", "boring", "dull", "uninteresting", "tedious"],
                EmotionType.ANXIETY: ["anxious", "nervous", "worried", "stressed", "tense"],
                EmotionType.LOVE: ["love", "adore", "cherish", "care", "affection"],
                EmotionType.GRATITUDE: ["grateful", "thankful", "appreciate", "thanks"]
            },
            "emotion_combinations": {
                (EmotionType.HAPPINESS, EmotionType.SURPRISE): "delight",
                (EmotionType.FEAR, EmotionType.ANXIETY): "panic",
                (EmotionType.ANGER, EmotionType.DISGUST): "contempt",
                (EmotionType.SADNESS, EmotionType.FEAR): "despair"
            }
        }
    
    def register_handlers(self):
        """Register message handlers"""
        self.message_handlers[MessageType.TASK_REQUEST] = self.handle_task_request
        self.message_handlers[MessageType.QUERY] = self.handle_query
        self.message_handlers[MessageType.EVENT] = self.handle_event
    
    async def start(self):
        """Start the emotion agent"""
        await super().start()
        
        # Start background tasks
        await self.start_background_tasks()
        
        # Announce capabilities
        await self.announce_capabilities()
    
    async def start_background_tasks(self):
        """Start background emotion processing tasks"""
        # Emotion decay task
        decay_task = asyncio.create_task(self.emotion_decay_loop())
        self.background_tasks.append(decay_task)
    
    async def announce_capabilities(self):
        """Announce agent capabilities"""
        capabilities_message = AgentMessage(
            sender_id=self.agent_id,
            message_type=MessageType.EVENT,
            content={
                "event_type": "agent_capabilities",
                "agent_id": self.agent_id,
                "capabilities": self.capabilities
            }
        )
        
        await self.publish_message(
            capabilities_message,
            routing_key="planner.*"
        )
    
    async def handle_task_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming emotion task"""
        task_data = message.content
        task_type = task_data.get("task_type")
        
        if task_type == "detect_emotion":
            result = await self.detect_emotion(task_data)
        elif task_type == "analyze_emotion":
            result = await self.analyze_emotion(task_data)
        elif task_type == "update_emotional_state":
            result = await self.update_emotional_state(task_data)
        elif task_type == "predict_emotion":
            result = await self.predict_emotion(task_data)
        elif task_type == "regulate_emotion":
            result = await self.regulate_emotion(task_data)
        else:
            result = {"error": "Unknown task type"}
        
        return result
    
    async def handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle query messages"""
        query_type = message.content.get("query_type")
        
        if query_type == "emotional_state":
            entity_id = message.content.get("entity_id")
            if entity_id in self.emotional_states:
                return self.emotional_states[entity_id].to_dict()
            else:
                return {"error": "Emotional state not found"}
        
        elif query_type == "emotion_history":
            entity_id = message.content.get("entity_id")
            if entity_id in self.emotion_history:
                return [state.to_dict() for state in self.emotion_history[entity_id][-10:]]
            else:
                return {"error": "Emotion history not found"}
        
        elif query_type == "capabilities":
            return {"capabilities": self.capabilities}
        
        else:
            return {"error": "Unknown query type"}
    
    async def handle_event(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle event messages"""
        event_type = message.content.get("event_type")
        
        if event_type == "emotion_trigger":
            # Process emotion trigger event
            entity_id = message.content.get("entity_id")
            trigger = message.content.get("trigger")
            impact = message.content.get("impact", {})
            
            await self.process_emotion_trigger(entity_id, trigger, impact)
        
        return {"status": "acknowledged"}
    
    async def detect_emotion(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect emotions from text or other input"""
        with self.tracer.start_as_current_span("detect_emotion") as span:
            text = task_data.get("text", "")
            entity_id = task_data.get("entity_id", "unknown")
            
            # Detect emotions from text
            detected_emotions = await self.detect_emotions_from_text(text)
            
            # Calculate overall emotional metrics
            mood, arousal, valence = await self.calculate_emotional_metrics(detected_emotions)
            
            # Create emotional state
            emotional_state = EmotionalState(
                entity_id=entity_id,
                emotions=detected_emotions,
                mood=mood,
                arousal=arousal,
                valence=valence,
                confidence=await self.calculate_detection_confidence(detected_emotions)
            )
            
            # Store emotional state
            await self.store_emotional_state(emotional_state)
            
            span.set_attribute("entity_id", entity_id)
            span.set_attribute("detected_emotions", len(detected_emotions))
            
            return emotional_state.to_dict()
    
    async def detect_emotions_from_text(self, text: str) -> Dict[EmotionType, float]:
        """Detect emotions from text using keyword analysis"""
        detected_emotions = {}
        text_lower = text.lower()
        
        emotion_keywords = self.emotion_models["emotion_keywords"]
        
        for emotion_type, keywords in emotion_keywords.items():
            emotion_score = 0.0
            for keyword in keywords:
                if keyword in text_lower:
                    emotion_score += 0.3
            
            # Normalize score
            detected_emotions[emotion_type] = min(emotion_score, 1.0)
        
        return detected_emotions
    
    async def calculate_emotional_metrics(self, emotions: Dict[EmotionType, float]) -> tuple:
        """Calculate overall emotional metrics"""
        # Calculate mood (positive vs negative)
        positive_emotions = [EmotionType.HAPPINESS, EmotionType.EXCITEMENT, 
                           EmotionType.LOVE, EmotionType.PRIDE, EmotionType.CURIOSITY,
                           EmotionType.GRATITUDE]
        negative_emotions = [EmotionType.SADNESS, EmotionType.ANGER, 
                          EmotionType.FEAR, EmotionType.DISGUST, EmotionType.ANXIETY]
        
        positive_sum = sum(emotions.get(e, 0) for e in positive_emotions)
        negative_sum = sum(emotions.get(e, 0) for e in negative_emotions)
        
        total = positive_sum + negative_sum
        if total > 0:
            mood = (positive_sum - negative_sum) / total
        else:
            mood = 0.0
        
        # Calculate arousal (high vs low energy)
        high_arousal = [EmotionType.EXCITEMENT, EmotionType.ANGER, 
                        EmotionType.FEAR, EmotionType.SURPRISE, EmotionType.ANXIETY]
        low_arousal = [EmotionType.CALM, EmotionType.BOREDOM, EmotionType.SADNESS]
        
        high_arousal_sum = sum(emotions.get(e, 0) for e in high_arousal)
        low_arousal_sum = sum(emotions.get(e, 0) for e in low_arousal)
        
        total_arousal = high_arousal_sum + low_arousal_sum
        if total_arousal > 0:
            arousal = high_arousal_sum / total_arousal
        else:
            arousal = 0.5
        
        # Calculate valence (emotional positivity)
        valence = (mood + 1.0) / 2.0  # Convert from -1..1 to 0..1
        
        return mood, arousal, valence
    
    async def calculate_detection_confidence(self, emotions: Dict[EmotionType, float]) -> float:
        """Calculate confidence in emotion detection"""
        if not emotions:
            return 0.0
        
        # Confidence based on number of detected emotions and their intensity
        detected_count = sum(1 for v in emotions.values() if v > 0.3)
        avg_intensity = sum(emotions.values()) / len(emotions)
        
        confidence = (detected_count / len(emotions)) * 0.5 + avg_intensity * 0.5
        
        return min(confidence, 1.0)
    
    async def analyze_emotion(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze emotional patterns and trends"""
        entity_id = task_data.get("entity_id")
        
        if entity_id not in self.emotion_history:
            return {"error": "No emotion history found"}
        
        history = self.emotion_history[entity_id]
        
        # Analyze trends
        trends = await self.analyze_emotion_trends(history)
        
        # Identify patterns
        patterns = await self.identify_emotion_patterns(history)
        
        # Calculate statistics
        stats = await self.calculate_emotion_statistics(history)
        
        return {
            "entity_id": entity_id,
            "trends": trends,
            "patterns": patterns,
            "statistics": stats,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    async def analyze_emotion_trends(self, history: List[EmotionalState]) -> Dict[str, Any]:
        """Analyze emotional trends over time"""
        if len(history) < 2:
            return {"trend": "insufficient_data"}
        
        # Calculate trend for each emotion
        trends = {}
        for emotion_type in EmotionType:
            values = [state.emotions.get(emotion_type, 0) for state in history]
            if len(values) >= 2:
                # Simple linear trend
                change = values[-1] - values[0]
                if change > 0.1:
                    trend = "increasing"
                elif change < -0.1:
                    trend = "decreasing"
                else:
                    trend = "stable"
                
                trends[emotion_type.value] = {
                    "trend": trend,
                    "change": change,
                    "current_value": values[-1]
                }
        
        return trends
    
    async def identify_emotion_patterns(self, history: List[EmotionalState]) -> List[str]:
        """Identify emotional patterns"""
        patterns = []
        
        if len(history) < 3:
            return patterns
        
        # Check for cyclical patterns
        recent_moods = [state.mood for state in history[-10:]]
        if len(recent_moods) >= 6:
            # Simple pattern detection
            mood_variance = max(recent_moods) - min(recent_moods)
            if mood_variance > 0.5:
                patterns.append("high_mood_fluctuation")
        
        # Check for dominant emotions
        emotion_sums = {}
        for state in history:
            for emotion, value in state.emotions.items():
                emotion_sums[emotion] = emotion_sums.get(emotion, 0) + value
        
        if emotion_sums:
            dominant_emotion = max(emotion_sums.items(), key=lambda x: x[1])
            if dominant_emotion[1] > len(history) * 0.5:
                patterns.append(f"dominant_{dominant_emotion[0].value}")
        
        return patterns
    
    async def calculate_emotion_statistics(self, history: List[EmotionalState]) -> Dict[str, Any]:
        """Calculate emotion statistics"""
        if not history:
            return {}
        
        # Calculate averages
        avg_mood = sum(state.mood for state in history) / len(history)
        avg_arousal = sum(state.arousal for state in history) / len(history)
        avg_valence = sum(state.valence for state in history) / len(history)
        
        # Calculate emotion averages
        emotion_averages = {}
        for emotion_type in EmotionType:
            values = [state.emotions.get(emotion_type, 0) for state in history]
            emotion_averages[emotion_type.value] = sum(values) / len(values) if values else 0.0
        
        return {
            "average_mood": avg_mood,
            "average_arousal": avg_arousal,
            "average_valence": avg_valence,
            "emotion_averages": emotion_averages,
            "sample_size": len(history)
        }
    
    async def update_emotional_state(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update emotional state for an entity"""
        entity_id = task_data.get("entity_id")
        emotion_updates = task_data.get("emotions", {})
        
        # Convert string keys to EmotionType
        emotion_updates_converted = {}
        for emotion_str, value in emotion_updates.items():
            try:
                emotion_type = EmotionType(emotion_str)
                emotion_updates_converted[emotion_type] = value
            except ValueError:
                continue
        
        # Get or create emotional state
        if entity_id in self.emotional_states:
            state = self.emotional_states[entity_id]
            
            # Update emotions
            for emotion_type, value in emotion_updates_converted.items():
                state.emotions[emotion_type] = max(0.0, min(value, 1.0))
            
            # Recalculate metrics
            state.mood, state.arousal, state.valence = await self.calculate_emotional_metrics(state.emotions)
            state.timestamp = datetime.utcnow()
            
            # Store in history
            await self.store_emotional_state(state)
            
            return state.to_dict()
        else:
            return {"error": "Emotional state not found"}
    
    async def predict_emotion(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict future emotional states"""
        entity_id = task_data.get("entity_id")
        time_horizon = task_data.get("time_horizon", 3600)  # seconds
        
        if entity_id not in self.emotion_history:
            return {"error": "No emotion history for prediction"}
        
        history = self.emotion_history[entity_id]
        
        # Simple prediction based on trends
        if len(history) >= 2:
            last_state = history[-1]
            previous_state = history[-2]
            
            predicted_emotions = {}
            for emotion_type in EmotionType:
                current_value = last_state.emotions.get(emotion_type, 0)
                previous_value = previous_state.emotions.get(emotion_type, 0)
                
                # Extrapolate trend
                trend = current_value - previous_value
                predicted_value = max(0.0, min(current_value + trend, 1.0))
                predicted_emotions[emotion_type.value] = predicted_value
            
            predicted_mood, predicted_arousal, predicted_valence = await self.calculate_emotional_metrics(
                {EmotionType(k): v for k, v in predicted_emotions.items()}
            )
            
            return {
                "entity_id": entity_id,
                "predicted_emotions": predicted_emotions,
                "predicted_mood": predicted_mood,
                "predicted_arousal": predicted_arousal,
                "predicted_valence": predicted_valence,
                "prediction_horizon": time_horizon,
                "confidence": 0.6  # Moderate confidence for simple prediction
            }
        else:
            return {"error": "Insufficient history for prediction"}
    
    async def regulate_emotion(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest emotion regulation strategies"""
        entity_id = task_data.get("entity_id")
        target_emotion = task_data.get("target_emotion")
        
        if entity_id not in self.emotional_states:
            return {"error": "Emotional state not found"}
        
        current_state = self.emotional_states[entity_id]
        
        # Generate regulation strategies
        strategies = await self.generate_regulation_strategies(current_state, target_emotion)
        
        return {
            "entity_id": entity_id,
            "current_state": current_state.to_dict(),
            "target_emotion": target_emotion,
            "strategies": strategies
        }
    
    async def generate_regulation_strategies(self, current_state: EmotionalState, target_emotion: Optional[str]) -> List[str]:
        """Generate emotion regulation strategies"""
        strategies = []
        
        # Analyze current emotional state
        dominant_emotions = sorted(current_state.emotions.items(), key=lambda x: x[1], reverse=True)
        
        if not dominant_emotions:
            return strategies
        
        top_emotion, top_value = dominant_emotions[0]
        
        # Generate strategies based on dominant emotion
        if top_emotion == EmotionType.ANXIETY and top_value > 0.6:
            strategies.extend([
                "Practice deep breathing exercises",
                "Engage in progressive muscle relaxation",
                "Try mindfulness meditation",
                "Ground yourself in the present moment"
            ])
        
        elif top_emotion == EmotionType.SADNESS and top_value > 0.6:
            strategies.extend([
                "Engage in physical activity",
                "Connect with supportive friends",
                "Practice self-compassion",
                "Set small, achievable goals"
            ])
        
        elif top_emotion == EmotionType.ANGER and top_value > 0.6:
            strategies.extend([
                "Take a cooling-off period",
                "Practice cognitive reframing",
                "Express feelings constructively",
                "Use relaxation techniques"
            ])
        
        elif top_emotion == EmotionType.FEAR and top_value > 0.6:
            strategies.extend([
                "Challenge catastrophic thinking",
                "Gradually face fears (exposure)",
                "Seek social support",
                "Practice relaxation techniques"
            ])
        
        else:
            strategies.extend([
                "Maintain emotional awareness",
                "Practice regular self-care",
                "Engage in meaningful activities",
                "Cultivate positive relationships"
            ])
        
        return strategies
    
    async def process_emotion_trigger(self, entity_id: str, trigger: str, impact: Dict[str, float]):
        """Process an emotion trigger event"""
        # Create emotion event
        event = EmotionEvent(
            entity_id=entity_id,
            event_type="trigger",
            trigger=trigger,
            emotional_impact={EmotionType(k): v for k, v in impact.items()}
        )
        
        self.emotion_events.append(event)
        
        # Update emotional state if exists
        if entity_id in self.emotional_states:
            state = self.emotional_states[entity_id]
            
            # Apply emotional impact
            for emotion_type, value in event.emotional_impact.items():
                current_value = state.emotions.get(emotion_type, 0)
                state.emotions[emotion_type] = max(0.0, min(current_value + value, 1.0))
            
            # Recalculate metrics
            state.mood, state.arousal, state.valence = await self.calculate_emotional_metrics(state.emotions)
            state.timestamp = datetime.utcnow()
            
            # Store updated state
            await self.store_emotional_state(state)
    
    async def store_emotional_state(self, state: EmotionalState):
        """Store emotional state in history"""
        self.emotional_states[state.entity_id] = state
        
        if state.entity_id not in self.emotion_history:
            self.emotion_history[state.entity_id] = []
        
        self.emotion_history[state.entity_id].append(state)
        
        # Keep history limited
        if len(self.emotion_history[state.entity_id]) > 100:
            self.emotion_history[state.entity_id] = self.emotion_history[state.entity_id][-100:]
    
    async def emotion_decay_loop(self):
        """Apply emotion decay over time"""
        while self.status.value == "running":
            try:
                await asyncio.sleep(60)  # Every minute
                
                for entity_id, state in self.emotional_states.items():
                    # Decay emotions slightly
                    for emotion_type in list(state.emotions.keys()):
                        current_value = state.emotions[emotion_type]
                        decayed_value = current_value * 0.99  # 1% decay per minute
                        state.emotions[emotion_type] = max(0.0, decayed_value)
                    
                    # Recalculate metrics
                    state.mood, state.arousal, state.valence = await self.calculate_emotional_metrics(state.emotions)
                    state.timestamp = datetime.utcnow()
                    
                    # Store updated state
                    await self.store_emotional_state(state)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Emotion decay error: {e}")
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process an emotion task"""
        task_type = task.get("task_type")
        
        if task_type == "detect_emotion":
            return await self.detect_emotion(task)
        elif task_type == "analyze_emotion":
            return await self.analyze_emotion(task)
        else:
            return {"error": "Unknown task type"}


async def main():
    """Main entry point for the emotion agent"""
    agent = EmotionAgent()
    
    try:
        await agent.start()
        
        # Start consuming messages
        await agent.consume_messages()
        
    except KeyboardInterrupt:
        await agent.stop()
    except Exception as e:
        agent.logger.error(f"Agent error: {e}")
        await agent.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())