"""
Animation Service - Procedural animation generation and motion blending
Handles character animation, facial animation, gesture generation, and physics integration
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from prometheus_client import Counter, Histogram, Gauge, start_http_server


class AnimationType(Enum):
    """Types of animations"""
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    JUMP = "jump"
    SIT = "sit"
    WAVE = "wave"
    POINT = "point"
    GESTURE = "gesture"
    FACIAL_EXPRESSION = "facial_expression"
    LIP_SYNC = "lip_sync"
    CUSTOM = "custom"


class BlendMode(Enum):
    """Animation blend modes"""
    ADDITIVE = "additive"
    OVERRIDE = "override"
    MIX = "mix"
    LAYER = "layer"


@dataclass
class AnimationClip:
    """Represents an animation clip"""
    clip_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    animation_type: AnimationType = AnimationType.CUSTOM
    duration: float = 1.0
    frames: List[Dict[str, Any]] = field(default_factory=list)
    bone_transforms: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "animation_type": self.animation_type.value,
            "duration": self.duration,
            "frame_count": len(self.frames),
            "bone_count": len(self.bone_transforms),
            "metadata": self.metadata
        }


@dataclass
class AnimationState:
    """Represents current animation state"""
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    active_clips: List[str] = field(default_factory=list)
    blend_weights: Dict[str, float] = field(default_factory=dict)
    blend_mode: BlendMode = BlendMode.MIX
    playback_speed: float = 1.0
    loop: bool = True
    transition_time: float = 0.3
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "active_clips": self.active_clips,
            "blend_weights": self.blend_weights,
            "blend_mode": self.blend_mode.value,
            "playback_speed": self.playback_speed,
            "loop": self.loop,
            "transition_time": self.transition_time,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class FacialExpression:
    """Represents a facial expression"""
    expression_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    blend_shapes: Dict[str, float] = field(default_factory=dict)
    eye_gaze: Tuple[float, float] = (0.0, 0.0)
    mouth_open: float = 0.0
    eyebrow_position: float = 0.0
    intensity: float = 1.0
    duration: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "expression_id": self.expression_id,
            "name": self.name,
            "blend_shapes": self.blend_shapes,
            "eye_gaze": self.eye_gaze,
            "mouth_open": self.mouth_open,
            "eyebrow_position": self.eyebrow_position,
            "intensity": self.intensity,
            "duration": self.duration
        }


@dataclass
class Gesture:
    """Represents a gesture"""
    gesture_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    hand_type: str = "right"  # left, right, both
    start_pose: Dict[str, Any] = field(default_factory=dict)
    end_pose: Dict[str, Any] = field(default_factory=dict)
    trajectory: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 1.0
    intensity: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "gesture_id": self.gesture_id,
            "name": self.name,
            "hand_type": self.hand_type,
            "duration": self.duration,
            "intensity": self.intensity,
            "waypoint_count": len(self.trajectory)
        }


class AnimationService:
    """
    Animation Service - Procedural animation generation
    Handles motion blending, facial animation, and gesture generation
    """
    
    def __init__(self):
        # Animation library
        self.clips: Dict[str, AnimationClip] = {}
        self.animation_states: Dict[str, AnimationState] = {}
        
        # Facial expressions
        self.expressions: Dict[str, FacialExpression] = {}
        self.current_expression: Optional[FacialExpression] = None
        
        # Gestures
        self.gestures: Dict[str, Gesture] = {}
        self.active_gestures: List[str] = []
        
        # Animation parameters
        self.skeleton: Dict[str, Dict[str, Any]] = {}
        self.physics_enabled: bool = True
        
        # Metrics
        self.animations_played = Counter('animation_played_total', 'Total animations played', ['type'])
        self.blend_operations = Counter('animation_blend_operations_total', 'Total blend operations')
        self.animation_time = Histogram('animation_processing_seconds', 'Animation processing time', ['operation'])
        self.active_animations = Gauge('animation_active_count', 'Number of active animations')
        
        # Tracing
        self.setup_tracing()
        self.tracer = trace.get_tracer(__name__)
        
        # Logger
        self.logger = logging.getLogger("animation_service")
    
    def setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()
        
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        tracer_provider.add_span_processor(span_processor)
    
    async def initialize(self):
        """Initialize animation service with default animations"""
        with self.tracer.start_as_current_span("initialize_animation") as span:
            try:
                # Load default animation clips
                await self._load_default_clips()
                
                # Load default facial expressions
                await self._load_default_expressions()
                
                # Load default gestures
                await self._load_default_gestures()
                
                # Initialize skeleton
                await self._initialize_skeleton()
                
                self.logger.info("Animation service initialized successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize animation service: {e}")
                span.record_exception(e)
                return False
    
    async def _load_default_clips(self):
        """Load default animation clips"""
        default_clips = [
            AnimationClip(
                name="idle",
                animation_type=AnimationType.IDLE,
                duration=2.0,
                bone_transforms=self._generate_idle_transforms()
            ),
            AnimationClip(
                name="walk",
                animation_type=AnimationType.WALK,
                duration=1.0,
                bone_transforms=self._generate_walk_transforms()
            ),
            AnimationClip(
                name="wave",
                animation_type=AnimationType.WAVE,
                duration=1.5,
                bone_transforms=self._generate_wave_transforms()
            )
        ]
        
        for clip in default_clips:
            self.clips[clip.clip_id] = clip
    
    async def _load_default_expressions(self):
        """Load default facial expressions"""
        default_expressions = [
            FacialExpression(
                name="neutral",
                blend_shapes={"mouth_smile": 0.0, "eyes_open": 1.0, "brows_neutral": 1.0},
                intensity=1.0
            ),
            FacialExpression(
                name="happy",
                blend_shapes={"mouth_smile": 0.8, "eyes_open": 0.9, "brows_raised": 0.3},
                intensity=1.0
            ),
            FacialExpression(
                name="sad",
                blend_shapes={"mouth_smile": -0.3, "eyes_open": 0.7, "brows_lowered": 0.5},
                intensity=1.0
            ),
            FacialExpression(
                name="surprised",
                blend_shapes={"mouth_open": 0.6, "eyes_open": 1.0, "brows_raised": 0.8},
                intensity=1.0
            )
        ]
        
        for expression in default_expressions:
            self.expressions[expression.expression_id] = expression
    
    async def _load_default_gestures(self):
        """Load default gestures"""
        default_gestures = [
            Gesture(
                name="wave_hand",
                hand_type="right",
                duration=1.0,
                intensity=1.0
            ),
            Gesture(
                name="point",
                hand_type="right",
                duration=0.5,
                intensity=1.0
            ),
            Gesture(
                name="thumbs_up",
                hand_type="right",
                duration=0.8,
                intensity=1.0
            )
        ]
        
        for gesture in default_gestures:
            self.gestures[gesture.gesture_id] = gesture
    
    async def _initialize_skeleton(self):
        """Initialize character skeleton"""
        # Simplified skeleton structure
        self.skeleton = {
            "root": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
            "spine": {"position": [0, 1, 0], "rotation": [0, 0, 0]},
            "head": {"position": [0, 1.7, 0], "rotation": [0, 0, 0]},
            "left_arm": {"position": [-0.3, 1.4, 0], "rotation": [0, 0, 0]},
            "right_arm": {"position": [0.3, 1.4, 0], "rotation": [0, 0, 0]},
            "left_leg": {"position": [-0.2, 0, 0], "rotation": [0, 0, 0]},
            "right_leg": {"position": [0.2, 0, 0], "rotation": [0, 0, 0]}
        }
    
    def _generate_idle_transforms(self) -> Dict[str, Dict[str, Any]]:
        """Generate idle animation transforms"""
        return {
            "root": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
            "spine": {"position": [0, 1, 0], "rotation": [0, 0, 0]},
            "head": {"position": [0, 1.7, 0], "rotation": [0, 0, 0]}
        }
    
    def _generate_walk_transforms(self) -> Dict[str, Dict[str, Any]]:
        """Generate walk animation transforms"""
        return {
            "root": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
            "left_leg": {"position": [-0.2, 0, 0], "rotation": [0, 0, 0]},
            "right_leg": {"position": [0.2, 0, 0], "rotation": [0, 0, 0]}
        }
    
    def _generate_wave_transforms(self) -> Dict[str, Dict[str, Any]]:
        """Generate wave animation transforms"""
        return {
            "right_arm": {"position": [0.3, 1.4, 0], "rotation": [0, 0, 1.5]},
            "right_forearm": {"position": [0.5, 1.2, 0], "rotation": [0, 0, -0.5]}
        }
    
    async def play_animation(self, clip_id: str, blend_mode: BlendMode = BlendMode.MIX, 
                           transition_time: float = 0.3) -> str:
        """Play an animation clip"""
        with self.tracer.start_as_current_span("play_animation") as span:
            import time
            start_time = time.time()
            
            span.set_attribute("clip_id", clip_id)
            span.set_attribute("blend_mode", blend_mode.value)
            
            if clip_id not in self.clips:
                self.logger.error(f"Animation clip {clip_id} not found")
                raise ValueError(f"Animation clip {clip_id} not found")
            
            clip = self.clips[clip_id]
            
            # Create animation state
            state = AnimationState(
                active_clips=[clip_id],
                blend_mode=blend_mode,
                transition_time=transition_time
            )
            
            self.animation_states[state.state_id] = state
            
            # Update metrics
            self.animations_played.labels(type=clip.animation_type.value).inc()
            self.active_animations.set(len(self.animation_states))
            self.animation_time.labels(operation="play").observe(time.time() - start_time)
            
            self.logger.info(f"Playing animation {clip.name}")
            return state.state_id
    
    async def blend_animations(self, clip_ids: List[str], weights: List[float]) -> str:
        """Blend multiple animations"""
        with self.tracer.start_as_current_span("blend_animations") as span:
            import time
            start_time = time.time()
            
            span.set_attribute("clip_count", len(clip_ids))
            
            # Validate inputs
            if len(clip_ids) != len(weights):
                raise ValueError("Number of clips must match number of weights")
            
            if not all(clip_id in self.clips for clip_id in clip_ids):
                raise ValueError("One or more animation clips not found")
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
            
            # Create blended state
            state = AnimationState(
                active_clips=clip_ids,
                blend_weights=dict(zip(clip_ids, weights)),
                blend_mode=BlendMode.MIX
            )
            
            self.animation_states[state.state_id] = state
            
            # Update metrics
            self.blend_operations.inc()
            self.active_animations.set(len(self.animation_states))
            self.animation_time.labels(operation="blend").observe(time.time() - start_time)
            
            self.logger.info(f"Blended {len(clip_ids)} animations")
            return state.state_id
    
    async def set_facial_expression(self, expression_id: str, intensity: float = 1.0) -> bool:
        """Set facial expression"""
        with self.tracer.start_as_current_span("set_facial_expression") as span:
            span.set_attribute("expression_id", expression_id)
            span.set_attribute("intensity", intensity)
            
            if expression_id not in self.expressions:
                self.logger.error(f"Expression {expression_id} not found")
                return False
            
            expression = self.expressions[expression_id]
            expression.intensity = intensity
            self.current_expression = expression
            
            self.logger.info(f"Set facial expression to {expression.name}")
            return True
    
    async def blend_expressions(self, expression_ids: List[str], weights: List[float]) -> bool:
        """Blend multiple facial expressions"""
        if len(expression_ids) != len(weights):
            raise ValueError("Number of expressions must match number of weights")
        
        if not all(expr_id in self.expressions for expr_id in expression_ids):
            raise ValueError("One or more expressions not found")
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # Create blended expression
        blended_blend_shapes = {}
        for expr_id, weight in zip(expression_ids, weights):
            expression = self.expressions[expr_id]
            for shape, value in expression.blend_shapes.items():
                blended_blend_shapes[shape] = blended_blend_shapes.get(shape, 0) + (value * weight)
        
        # Create temporary blended expression
        blended_expression = FacialExpression(
            name="blended",
            blend_shapes=blended_blend_shapes,
            intensity=1.0
        )
        
        self.current_expression = blended_expression
        
        self.logger.info(f"Blended {len(expression_ids)} expressions")
        return True
    
    async def play_gesture(self, gesture_id: str, intensity: float = 1.0) -> bool:
        """Play a gesture"""
        with self.tracer.start_as_current_span("play_gesture") as span:
            span.set_attribute("gesture_id", gesture_id)
            span.set_attribute("intensity", intensity)
            
            if gesture_id not in self.gestures:
                self.logger.error(f"Gesture {gesture_id} not found")
                return False
            
            gesture = self.gestures[gesture_id]
            gesture.intensity = intensity
            self.active_gestures.append(gesture_id)
            
            self.logger.info(f"Playing gesture {gesture.name}")
            return True
    
    async def stop_gesture(self, gesture_id: str) -> bool:
        """Stop a gesture"""
        if gesture_id in self.active_gestures:
            self.active_gestures.remove(gesture_id)
            self.logger.info(f"Stopped gesture {gesture_id}")
            return True
        return False
    
    async def generate_procedural_animation(self, animation_type: AnimationType, 
                                          parameters: Dict[str, Any]) -> str:
        """Generate procedural animation"""
        with self.tracer.start_as_current_span("generate_procedural_animation") as span:
            import time
            start_time = time.time()
            
            span.set_attribute("animation_type", animation_type.value)
            
            # Generate procedural animation based on type
            if animation_type == AnimationType.GESTURE:
                clip = await self._generate_procedural_gesture(parameters)
            elif animation_type == AnimationType.FACIAL_EXPRESSION:
                clip = await self._generate_procedural_expression(parameters)
            else:
                clip = await self._generate_procedural_motion(animation_type, parameters)
            
            self.clips[clip.clip_id] = clip
            
            # Update metrics
            self.animations_played.labels(type="procedural").inc()
            self.animation_time.labels(operation="generate").observe(time.time() - start_time)
            
            self.logger.info(f"Generated procedural animation {clip.name}")
            return clip.clip_id
    
    async def _generate_procedural_gesture(self, parameters: Dict[str, Any]) -> AnimationClip:
        """Generate procedural gesture"""
        gesture_type = parameters.get("gesture_type", "wave")
        hand = parameters.get("hand", "right")
        duration = parameters.get("duration", 1.0)
        
        transforms = {}
        if hand == "right":
            transforms["right_arm"] = {"position": [0.3, 1.4, 0], "rotation": [0, 0, 1.5]}
        else:
            transforms["left_arm"] = {"position": [-0.3, 1.4, 0], "rotation": [0, 0, -1.5]}
        
        return AnimationClip(
            name=f"procedural_{gesture_type}",
            animation_type=AnimationType.GESTURE,
            duration=duration,
            bone_transforms=transforms
        )
    
    async def _generate_procedural_expression(self, parameters: Dict[str, Any]) -> AnimationClip:
        """Generate procedural facial expression"""
        emotion = parameters.get("emotion", "neutral")
        intensity = parameters.get("intensity", 1.0)
        
        blend_shapes = {}
        if emotion == "happy":
            blend_shapes = {"mouth_smile": 0.8 * intensity, "eyes_open": 0.9 * intensity}
        elif emotion == "sad":
            blend_shapes = {"mouth_smile": -0.3 * intensity, "eyes_open": 0.7 * intensity}
        elif emotion == "angry":
            blend_shapes = {"brows_lowered": 0.5 * intensity, "mouth_open": 0.2 * intensity}
        
        return AnimationClip(
            name=f"procedural_{emotion}",
            animation_type=AnimationType.FACIAL_EXPRESSION,
            duration=1.0,
            bone_transforms={"face": {"blend_shapes": blend_shapes}}
        )
    
    async def _generate_procedural_motion(self, animation_type: AnimationType, 
                                         parameters: Dict[str, Any]) -> AnimationClip:
        """Generate procedural motion animation"""
        duration = parameters.get("duration", 1.0)
        speed = parameters.get("speed", 1.0)
        
        transforms = {}
        if animation_type == AnimationType.WALK:
            transforms = {
                "left_leg": {"position": [-0.2, 0, 0], "rotation": [0, 0, 0.5 * speed]},
                "right_leg": {"position": [0.2, 0, 0], "rotation": [0, 0, -0.5 * speed]}
            }
        elif animation_type == AnimationType.RUN:
            transforms = {
                "left_leg": {"position": [-0.2, 0, 0], "rotation": [0, 0, 1.0 * speed]},
                "right_leg": {"position": [0.2, 0, 0], "rotation": [0, 0, -1.0 * speed]}
            }
        
        return AnimationClip(
            name=f"procedural_{animation_type.value}",
            animation_type=animation_type,
            duration=duration,
            bone_transforms=transforms
        )
    
    async def get_animation_state(self, state_id: str) -> Optional[AnimationState]:
        """Get animation state by ID"""
        return self.animation_states.get(state_id)
    
    async def update_animation_state(self, state_id: str, updates: Dict[str, Any]) -> bool:
        """Update animation state"""
        if state_id not in self.animation_states:
            return False
        
        state = self.animation_states[state_id]
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        return True
    
    async def get_current_bone_transforms(self, state_id: str) -> Dict[str, Dict[str, Any]]:
        """Get current bone transforms for an animation state"""
        if state_id not in self.animation_states:
            return {}
        
        state = self.animation_states[state_id]
        transforms = {}
        
        # Blend transforms from active clips
        for clip_id in state.active_clips:
            if clip_id in self.clips:
                clip = self.clips[clip_id]
                weight = state.blend_weights.get(clip_id, 1.0)
                
                for bone, bone_transform in clip.bone_transforms.items():
                    if bone not in transforms:
                        transforms[bone] = {}
                    
                    for key, value in bone_transform.items():
                        transforms[bone][key] = transforms[bone].get(key, 0) + (value * weight)
        
        return transforms


# FastAPI application
app = FastAPI(title="Animation Service")
animation_service: Optional[AnimationService] = None


class AnimationInput(BaseModel):
    """Input for animation operations"""
    clip_id: Optional[str] = None
    animation_type: str = "custom"
    blend_mode: str = "mix"
    transition_time: float = 0.3
    parameters: Dict[str, Any] = {}


class ExpressionInput(BaseModel):
    """Input for facial expression"""
    expression_id: Optional[str] = None
    intensity: float = 1.0
    emotion: Optional[str] = None


class GestureInput(BaseModel):
    """Input for gesture"""
    gesture_id: Optional[str] = None
    gesture_type: Optional[str] = None
    hand: str = "right"
    intensity: float = 1.0
    duration: float = 1.0


@app.on_event("startup")
async def startup_event():
    """Initialize animation service on startup"""
    global animation_service
    animation_service = AnimationService()
    await animation_service.initialize()
    
    # Start metrics server
    start_http_server(8006)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup animation service on shutdown"""
    if animation_service:
        # Cleanup if needed
        pass


@app.get("/status")
async def get_status():
    """Get animation service status"""
    return {
        "status": "running",
        "clips_count": len(animation_service.clips) if animation_service else 0,
        "expressions_count": len(animation_service.expressions) if animation_service else 0,
        "gestures_count": len(animation_service.gestures) if animation_service else 0,
        "active_animations": len(animation_service.animation_states) if animation_service else 0,
        "current_expression": animation_service.current_expression.name if animation_service and animation_service.current_expression else None
    }


@app.post("/play")
async def play_animation_endpoint(animation_input: AnimationInput):
    """Play an animation"""
    if not animation_service:
        raise HTTPException(status_code=503, detail="Animation service not initialized")
    
    if animation_input.clip_id:
        state_id = await animation_service.play_animation(
            animation_input.clip_id,
            BlendMode(animation_input.blend_mode),
            animation_input.transition_time
        )
    else:
        # Generate procedural animation
        state_id = await animation_service.generate_procedural_animation(
            AnimationType(animation_input.animation_type),
            animation_input.parameters
        )
        state_id = await animation_service.play_animation(state_id)
    
    return {"state_id": state_id, "status": "playing"}


@app.post("/blend")
async def blend_animations_endpoint(clip_ids: List[str], weights: List[float]):
    """Blend multiple animations"""
    if not animation_service:
        raise HTTPException(status_code=503, detail="Animation service not initialized")
    
    state_id = await animation_service.blend_animations(clip_ids, weights)
    
    return {"state_id": state_id, "status": "blended"}


@app.post("/expression")
async def set_expression_endpoint(expression_input: ExpressionInput):
    """Set facial expression"""
    if not animation_service:
        raise HTTPException(status_code=503, detail="Animation service not initialized")
    
    if expression_input.expression_id:
        success = await animation_service.set_facial_expression(
            expression_input.expression_id,
            expression_input.intensity
        )
    else:
        # Generate procedural expression
        parameters = {"emotion": expression_input.emotion, "intensity": expression_input.intensity}
        clip_id = await animation_service.generate_procedural_animation(
            AnimationType.FACIAL_EXPRESSION,
            parameters
        )
        success = True
    
    return {"status": "success" if success else "failed"}


@app.post("/gesture")
async def play_gesture_endpoint(gesture_input: GestureInput):
    """Play a gesture"""
    if not animation_service:
        raise HTTPException(status_code=503, detail="Animation service not initialized")
    
    if gesture_input.gesture_id:
        success = await animation_service.play_gesture(
            gesture_input.gesture_id,
            gesture_input.intensity
        )
    else:
        # Generate procedural gesture
        parameters = {
            "gesture_type": gesture_input.gesture_type,
            "hand": gesture_input.hand,
            "duration": gesture_input.duration
        }
        clip_id = await animation_service.generate_procedural_animation(
            AnimationType.GESTURE,
            parameters
        )
        success = True
    
    return {"status": "success" if success else "failed"}


@app.get("/state/{state_id}")
async def get_animation_state_endpoint(state_id: str):
    """Get animation state"""
    if not animation_service:
        raise HTTPException(status_code=503, detail="Animation service not initialized")
    
    state = await animation_service.get_animation_state(state_id)
    
    if state:
        return state.to_dict()
    else:
        raise HTTPException(status_code=404, detail="Animation state not found")


@app.get("/transforms/{state_id}")
async def get_bone_transforms_endpoint(state_id: str):
    """Get current bone transforms"""
    if not animation_service:
        raise HTTPException(status_code=503, detail="Animation service not initialized")
    
    transforms = await animation_service.get_current_bone_transforms(state_id)
    
    return {"transforms": transforms}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
