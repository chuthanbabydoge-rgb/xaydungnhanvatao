"""
Avatar Service - Procedural Animation Management
Handles procedural animation systems for AI companion avatar including eye tracking, blink, 
micro expressions, head look, body IK, gestures, and emotion-driven animations
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import math
import random
import uuid

from shared.database.postgres import get_postgres
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Avatar Service",
    description="Procedural animation management for AI Companion",
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
class AvatarState(BaseModel):
    """Complete avatar state"""
    avatar_id: str = Field(..., description="Avatar ID")
    user_id: str = Field(..., description="User ID")
    eye_tracking: Dict[str, Any] = Field(default_factory=dict, description="Eye tracking state")
    blink_state: Dict[str, Any] = Field(default_factory=dict, description="Blink state")
    micro_expressions: List[Dict[str, Any]] = Field(default_factory=list, description="Active micro expressions")
    head_look: Dict[str, Any] = Field(default_factory=dict, description="Head look state")
    body_ik: Dict[str, Any] = Field(default_factory=dict, description="Body IK state")
    gestures: List[Dict[str, Any]] = Field(default_factory=list, description="Active gestures")
    breathing: Dict[str, Any] = Field(default_factory=dict, description="Breathing state")
    idle_variation: Dict[str, Any] = Field(default_factory=dict, description="Idle variation state")
    emotion_animation: Dict[str, Any] = Field(default_factory=dict, description="Emotion animation state")
    interaction_animation: Dict[str, Any] = Field(default_factory=dict, description="Interaction animation state")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="State timestamp")


class EyeTrackingConfig(BaseModel):
    """Eye tracking configuration"""
    avatar_id: str = Field(..., description="Avatar ID")
    enabled: bool = Field(default=True, description="Enable eye tracking")
    target_mode: str = Field(default="user", description="Target mode: user, object, random")
    movement_speed: float = Field(default=2.0, ge=0.1, le=10.0, description="Eye movement speed")
    saccade_interval: float = Field(default=3.0, ge=0.5, le=10.0, description="Saccade interval in seconds")
    gaze_duration: float = Field(default=1.5, ge=0.1, le=5.0, description="Gaze duration in seconds")
    convergence: float = Field(default=0.0, ge=-1.0, le=1.0, description="Eye convergence")
    pupil_dilation: float = Field(default=0.5, ge=0.0, le=1.0, description="Pupil dilation")


class BlinkConfig(BaseModel):
    """Blink configuration"""
    avatar_id: str = Field(..., description="Avatar ID")
    enabled: bool = Field(default=True, description="Enable blinking")
    blink_interval: float = Field(default=4.0, ge=1.0, le=10.0, description="Average blink interval in seconds")
    blink_duration: float = Field(default=0.15, ge=0.05, le=0.5, description="Blink duration in seconds")
    blink_variance: float = Field(default=0.3, ge=0.0, le=1.0, description="Blink timing variance")
    double_blink_probability: float = Field(default=0.1, ge=0.0, le=0.5, description="Double blink probability")
    partial_blink_probability: float = Field(default=0.2, ge=0.0, le=0.5, description="Partial blink probability")


class MicroExpressionConfig(BaseModel):
    """Micro expression configuration"""
    avatar_id: str = Field(..., description="Avatar ID")
    enabled: bool = Field(default=True, description="Enable micro expressions")
    expression_types: List[str] = Field(default_factory=list, description="Available expression types")
    intensity: float = Field(default=0.3, ge=0.0, le=1.0, description="Expression intensity")
    duration: float = Field(default=0.5, ge=0.1, le=2.0, description="Expression duration")
    frequency: float = Field(default=0.2, ge=0.0, le=1.0, description="Expression frequency per second")
    emotion_coupling: bool = Field(default=True, description="Couple with emotion state")


class HeadLookConfig(BaseModel):
    """Head look configuration"""
    avatar_id: str = Field(..., description="Avatar ID")
    enabled: bool = Field(default=True, description="Enable head looking")
    tracking_mode: str = Field(default="eyes_follow", description="Mode: eyes_follow, independent, user_focus")
    rotation_speed: float = Field(default=1.5, ge=0.1, le=5.0, description="Head rotation speed")
    max_pitch: float = Field(default=30.0, ge=0.0, le=90.0, description="Max pitch angle in degrees")
    max_yaw: float = Field(default=45.0, ge=0.0, le=90.0, description="Max yaw angle in degrees")
    return_to_center: bool = Field(default=True, description="Return to center position")
    return_speed: float = Field(default=0.5, ge=0.1, le=2.0, description="Return to center speed")


class GestureConfig(BaseModel):
    """Gesture configuration"""
    avatar_id: str = Field(..., description="Avatar ID")
    enabled: bool = Field(default=True, description="Enable gestures")
    gesture_library: List[str] = Field(default_factory=list, description="Available gestures")
    gesture_probability: float = Field(default=0.3, ge=0.0, le=1.0, description="Gesture probability")
    speech_coupling: bool = Field(default=True, description="Couple with speech")
    emotion_coupling: bool = Field(default=True, description="Couple with emotion")
    emphasis_gestures: bool = Field(default=True, description="Enable emphasis gestures")
    random_gestures: bool = Field(default=True, description="Enable random idle gestures")


class BreathingConfig(BaseModel):
    """Breathing configuration"""
    avatar_id: str = Field(..., description="Avatar ID")
    enabled: bool = Field(default=True, description="Enable breathing")
    breathing_rate: float = Field(default=12.0, ge=6.0, le=20.0, description="Breaths per minute")
    breath_depth: float = Field(default=0.5, ge=0.1, le=1.0, description="Breath depth")
    chest_movement: float = Field(default=0.3, ge=0.0, le=1.0, description="Chest movement amount")
    shoulder_movement: float = Field(default=0.2, ge=0.0, le=0.5, description="Shoulder movement amount")
    breathing_pattern: str = Field(default="natural", description="Pattern: natural, deep, shallow, irregular")


class ProceduralAnimationRequest(BaseModel):
    """Procedural animation request"""
    avatar_id: str = Field(..., description="Avatar ID")
    user_id: str = Field(..., description="User ID")
    target_position: Optional[Dict[str, float]] = Field(default=None, description="Target position for looking")
    emotion: Optional[str] = Field(default=None, description="Current emotion")
    speech_active: bool = Field(default=False, description="Whether speech is active")
    interaction_type: Optional[str] = Field(default=None, description="Interaction type")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class ProceduralAnimationResponse(BaseModel):
    """Procedural animation response"""
    avatar_id: str = Field(..., description="Avatar ID")
    eye_left_rotation: Dict[str, float] = Field(default_factory=dict, description="Left eye rotation")
    eye_right_rotation: Dict[str, float] = Field(default_factory=dict, description="Right eye rotation")
    head_rotation: Dict[str, float] = Field(default_factory=dict, description="Head rotation")
    blink_state: Dict[str, Any] = Field(default_factory=dict, description="Blink state")
    micro_expressions: List[Dict[str, Any]] = Field(default_factory=list, description="Active micro expressions")
    body_ik_pose: Dict[str, Any] = Field(default_factory=dict, description="Body IK pose")
    gesture_state: Dict[str, Any] = Field(default_factory=dict, description="Gesture state")
    breathing_state: Dict[str, Any] = Field(default_factory=dict, description="Breathing state")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# Procedural animation engine
class ProceduralAnimationEngine:
    """Procedural animation calculation engine"""
    
    def __init__(self):
        self.default_configs = {
            "eye_tracking": {
                "enabled": True,
                "target_mode": "user",
                "movement_speed": 2.0,
                "saccade_interval": 3.0,
                "gaze_duration": 1.5,
                "convergence": 0.0,
                "pupil_dilation": 0.5
            },
            "blink": {
                "enabled": True,
                "blink_interval": 4.0,
                "blink_duration": 0.15,
                "blink_variance": 0.3,
                "double_blink_probability": 0.1,
                "partial_blink_probability": 0.2
            },
            "micro_expressions": {
                "enabled": True,
                "expression_types": ["smile", "frown", "surprise", "confusion", "interest"],
                "intensity": 0.3,
                "duration": 0.5,
                "frequency": 0.2,
                "emotion_coupling": True
            },
            "head_look": {
                "enabled": True,
                "tracking_mode": "eyes_follow",
                "rotation_speed": 1.5,
                "max_pitch": 30.0,
                "max_yaw": 45.0,
                "return_to_center": True,
                "return_speed": 0.5
            },
            "gesture": {
                "enabled": True,
                "gesture_library": ["wave", "nod", "shake", "point", "thumbs_up"],
                "gesture_probability": 0.3,
                "speech_coupling": True,
                "emotion_coupling": True,
                "emphasis_gestures": True,
                "random_gestures": True
            },
            "breathing": {
                "enabled": True,
                "breathing_rate": 12.0,
                "breath_depth": 0.5,
                "chest_movement": 0.3,
                "shoulder_movement": 0.2,
                "breathing_pattern": "natural"
            }
        }
    
    def calculate_eye_tracking(self, config: EyeTrackingConfig, target_pos: Optional[Dict[str, float]] = None, time_delta: float = 0.016) -> Dict[str, Any]:
        """Calculate eye tracking state"""
        if not config.enabled:
            return {"enabled": False, "left_rotation": {"x": 0, "y": 0, "z": 0}, "right_rotation": {"x": 0, "y": 0, "z": 0}}
        
        # Calculate target angles based on target position
        if target_pos:
            # Calculate yaw and pitch to look at target
            dx = target_pos.get("x", 0)
            dy = target_pos.get("y", 0)
            dz = target_pos.get("z", 0)
            
            # Simple calculation - in production, use proper 3D math
            yaw = math.atan2(dx, dz) * (180 / math.pi)
            pitch = math.atan2(dy, math.sqrt(dx*dx + dz*dz)) * (180 / math.pi)
            
            # Clamp angles
            yaw = max(-45, min(45, yaw))
            pitch = max(-30, min(30, pitch))
        else:
            # Random saccade movement
            yaw = random.uniform(-10, 10)
            pitch = random.uniform(-5, 5)
        
        # Add convergence
        convergence_offset = config.convergence * 5.0
        
        left_rotation = {
            "x": pitch + convergence_offset,
            "y": yaw + convergence_offset,
            "z": 0
        }
        
        right_rotation = {
            "x": pitch - convergence_offset,
            "y": yaw - convergence_offset,
            "z": 0
        }
        
        return {
            "enabled": True,
            "left_rotation": left_rotation,
            "right_rotation": right_rotation,
            "convergence": config.convergence,
            "pupil_dilation": config.pupil_dilation
        }
    
    def calculate_blink(self, config: BlinkConfig, last_blink_time: float, current_time: float) -> Dict[str, Any]:
        """Calculate blink state"""
        if not config.enabled:
            return {"enabled": False, "is_blinking": False, "blink_progress": 0.0}
        
        time_since_blink = current_time - last_blink_time
        
        # Add variance to interval
        interval_with_variance = config.blink_interval * (1 + random.uniform(-config.blink_variance, config.blink_variance))
        
        if time_since_blink > interval_with_variance:
            # Trigger blink
            is_double = random.random() < config.double_blink_probability
            is_partial = random.random() < config.partial_blink_probability
            
            return {
                "enabled": True,
                "is_blinking": True,
                "blink_progress": 0.0,
                "blink_duration": config.blink_duration,
                "is_double_blink": is_double,
                "is_partial_blink": is_partial,
                "partial_amount": random.uniform(0.3, 0.7) if is_partial else 1.0
            }
        
        return {
            "enabled": True,
            "is_blinking": False,
            "blink_progress": 0.0,
            "time_until_next": interval_with_variance - time_since_blink
        }
    
    def calculate_micro_expressions(self, config: MicroExpressionConfig, emotion: Optional[str] = None) -> List[Dict[str, Any]]:
        """Calculate micro expressions"""
        if not config.enabled or not config.expression_types:
            return []
        
        # Generate expressions based on probability
        expressions = []
        
        if random.random() < config.frequency:
            # Select expression type
            if emotion and config.emotion_coupling:
                # Emotion-coupled expression
                emotion_expressions = {
                    "happy": ["smile", "raised_eyebrows"],
                    "sad": ["frown", "lowered_eyebrows"],
                    "angry": ["furrowed_brows", "tight_lips"],
                    "surprised": ["raised_eyebrows", "open_mouth"],
                    "neutral": ["slight_smile", "relaxed"]
                }
                available = emotion_expressions.get(emotion, config.expression_types)
            else:
                available = config.expression_types
            
            if available:
                expression_type = random.choice(available)
                expressions.append({
                    "type": expression_type,
                    "intensity": config.intensity * random.uniform(0.5, 1.5),
                    "duration": config.duration * random.uniform(0.8, 1.2),
                    "blend_shapes": self._get_expression_blend_shapes(expression_type)
                })
        
        return expressions
    
    def _get_expression_blend_shapes(self, expression_type: str) -> Dict[str, float]:
        """Get blend shapes for expression type"""
        blend_shapes = {
            "smile": {"mouth_smile": 0.7, "eye_smile": 0.3, "cheek_raise": 0.2},
            "frown": {"mouth_frown": 0.6, "brow_inner_down": 0.4, "lip_corner_down": 0.3},
            "surprise": {"brow_raise": 0.5, "eye_wide": 0.4, "mouth_open": 0.3},
            "confusion": {"brow_inner_up": 0.3, "brow_outer_down": 0.2, "head_tilt": 0.1},
            "interest": {"brow_raise": 0.2, "eye_wide": 0.2, "slight_smile": 0.3},
            "raised_eyebrows": {"brow_raise": 0.6, "forehead_wrinkle": 0.1},
            "lowered_eyebrows": {"brow_down": 0.5, "eye_narrow": 0.2},
            "furrowed_brows": {"brow_inner_down": 0.6, "nose_wrinkle": 0.3},
            "tight_lips": {"mouth_press": 0.7, "jaw_clench": 0.2},
            "open_mouth": {"jaw_open": 0.4, "lip_stretch": 0.2},
            "slight_smile": {"mouth_smile": 0.3, "eye_smile": 0.1},
            "relaxed": {"all_relax": 0.5}
        }
        return blend_shapes.get(expression_type, {})
    
    def calculate_head_look(self, config: HeadLookConfig, eye_rotation: Dict[str, float], target_pos: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Calculate head look state"""
        if not config.enabled:
            return {"enabled": False, "rotation": {"x": 0, "y": 0, "z": 0}}
        
        if config.tracking_mode == "eyes_follow":
            # Head follows eyes with delay
            pitch = eye_rotation.get("x", 0) * 0.7  # Head moves less than eyes
            yaw = eye_rotation.get("y", 0) * 0.7
        elif config.tracking_mode == "user_focus" and target_pos:
            # Direct focus on user
            dx = target_pos.get("x", 0)
            dy = target_pos.get("y", 0)
            dz = target_pos.get("z", 0)
            
            yaw = math.atan2(dx, dz) * (180 / math.pi)
            pitch = math.atan2(dy, math.sqrt(dx*dx + dz*dz)) * (180 / math.pi)
        else:
            # Independent movement
            yaw = random.uniform(-5, 5)
            pitch = random.uniform(-3, 3)
        
        # Clamp angles
        yaw = max(-config.max_yaw, min(config.max_yaw, yaw))
        pitch = max(-config.max_pitch, min(config.max_pitch, pitch))
        
        return {
            "enabled": True,
            "rotation": {"x": pitch, "y": yaw, "z": 0},
            "tracking_mode": config.tracking_mode
        }
    
    def calculate_body_ik(self, target_pos: Optional[Dict[str, float]] = None, posture: str = "standing") -> Dict[str, Any]:
        """Calculate body IK pose"""
        # Simplified IK calculation
        if posture == "standing":
            base_pose = {
                "spine_rotation": {"x": 0, "y": 0, "z": 0},
                "shoulder_left": {"x": 0, "y": 0, "z": 0},
                "shoulder_right": {"x": 0, "y": 0, "z": 0},
                "arm_left": {"x": 0, "y": 0, "z": 0},
                "arm_right": {"x": 0, "y": 0, "z": 0},
                "hand_left": {"x": 0, "y": 0, "z": 0},
                "hand_right": {"x": 0, "y": 0, "z": 0}
            }
        else:
            base_pose = {
                "spine_rotation": {"x": 0, "y": 0, "z": 0},
                "shoulder_left": {"x": 0, "y": 0, "z": 0},
                "shoulder_right": {"x": 0, "y": 0, "z": 0},
                "arm_left": {"x": 0, "y": 0, "z": 0},
                "arm_right": {"x": 0, "y": 0, "z": 0},
                "hand_left": {"x": 0, "y": 0, "z": 0},
                "hand_right": {"x": 0, "y": 0, "z": 0}
            }
        
        # Add subtle procedural movement
        base_pose["spine_rotation"]["x"] = math.sin(datetime.utcnow().timestamp()) * 2.0  # Breathing sway
        
        return {
            "pose": base_pose,
            "posture": posture,
            "ik_active": True
        }
    
    def calculate_gesture(self, config: GestureConfig, speech_active: bool, emotion: Optional[str] = None) -> Dict[str, Any]:
        """Calculate gesture state"""
        if not config.enabled or not config.gesture_library:
            return {"enabled": False, "active_gesture": None}
        
        # Determine if gesture should trigger
        should_gesture = False
        
        if speech_active and config.speech_coupling:
            should_gesture = random.random() < config.gesture_probability * 1.5
        elif config.random_gestures:
            should_gesture = random.random() < config.gesture_probability * 0.3
        
        if emotion and config.emotion_coupling:
            emotion_gestures = {
                "happy": ["wave", "thumbs_up"],
                "sad": ["head_down"],
                "angry": ["point", "shake"],
                "surprised": ["hands_up"]
            }
            if emotion in emotion_gestures:
                should_gesture = True
        
        if should_gesture:
            gesture = random.choice(config.gesture_library)
            return {
                "enabled": True,
                "active_gesture": gesture,
                "gesture_progress": 0.0,
                "gesture_duration": random.uniform(1.0, 2.0)
            }
        
        return {
            "enabled": True,
            "active_gesture": None
        }
    
    def calculate_breathing(self, config: BreathingConfig, time_delta: float = 0.016) -> Dict[str, Any]:
        """Calculate breathing state"""
        if not config.enabled:
            return {"enabled": False, "breath_phase": 0.0, "chest_expansion": 0.0}
        
        # Calculate breathing phase based on rate
        current_time = datetime.utcnow().timestamp()
        breath_period = 60.0 / config.breathing_rate
        breath_phase = (current_time % breath_period) / breath_period
        
        # Sine wave for natural breathing
        breath_value = math.sin(breath_phase * 2 * math.pi)
        
        # Calculate expansion
        chest_expansion = breath_value * config.breath_depth * config.chest_movement
        shoulder_expansion = breath_value * config.breath_depth * config.shoulder_movement
        
        return {
            "enabled": True,
            "breath_phase": breath_phase,
            "chest_expansion": chest_expansion,
            "shoulder_expansion": shoulder_expansion,
            "breathing_rate": config.breathing_rate,
            "breathing_pattern": config.breathing_pattern
        }
    
    def calculate_idle_variation(self, time_delta: float = 0.016) -> Dict[str, Any]:
        """Calculate idle variation state"""
        current_time = datetime.utcnow().timestamp()
        
        # Generate subtle procedural variations
        weight_shift = math.sin(current_time * 0.5) * 0.5
        subtle_rotation = math.sin(current_time * 0.3) * 2.0
        posture_adjustment = math.sin(current_time * 0.2) * 1.0
        
        return {
            "weight_shift": weight_shift,
            "subtle_rotation": subtle_rotation,
            "posture_adjustment": posture_adjustment,
            "fidget_probability": 0.1,
            "current_idle_time": current_time % 30.0  # Reset every 30 seconds
        }
    
    def calculate_emotion_animation(self, emotion: Optional[str] = None, intensity: float = 0.5) -> Dict[str, Any]:
        """Calculate emotion-driven animation"""
        if not emotion:
            return {"enabled": False, "emotion": None}
        
        emotion_animations = {
            "happy": {
                "body_posture": "upright",
                "shoulder_position": "relaxed",
                "head_tilt": "slight_up",
                "movement_energy": 0.7
            },
            "sad": {
                "body_posture": "slumped",
                "shoulder_position": "forward",
                "head_tilt": "down",
                "movement_energy": 0.2
            },
            "angry": {
                "body_posture": "tense",
                "shoulder_position": "raised",
                "head_tilt": "forward",
                "movement_energy": 0.9
            },
            "surprised": {
                "body_posture": "alert",
                "shoulder_position": "raised",
                "head_tilt": "back",
                "movement_energy": 0.8
            },
            "neutral": {
                "body_posture": "natural",
                "shoulder_position": "relaxed",
                "head_tilt": "center",
                "movement_energy": 0.3
            }
        }
        
        base_animation = emotion_animations.get(emotion, emotion_animations["neutral"])
        
        # Apply intensity
        movement_energy = base_animation["movement_energy"] * intensity
        
        return {
            "enabled": True,
            "emotion": emotion,
            "animation": base_animation,
            "intensity": intensity,
            "movement_energy": movement_energy
        }
    
    def calculate_interaction_animation(self, interaction_type: Optional[str] = None) -> Dict[str, Any]:
        """Calculate interaction animation"""
        if not interaction_type:
            return {"enabled": False, "interaction_type": None}
        
        interaction_animations = {
            "greeting": {
                "gesture": "wave",
                "head_movement": "nod",
                "body_approach": "slight_forward",
                "duration": 2.0
            },
            "farewell": {
                "gesture": "wave",
                "head_movement": "slight_bow",
                "body_approach": "slight_back",
                "duration": 2.0
            },
            "agreement": {
                "gesture": "nod",
                "head_movement": "nod",
                "body_approach": "slight_forward",
                "duration": 1.0
            },
            "disagreement": {
                "gesture": "shake",
                "head_movement": "shake",
                "body_approach": "slight_back",
                "duration": 1.0
            },
            "thinking": {
                "gesture": "hand_to_chin",
                "head_movement": "tilt",
                "body_approach": "still",
                "duration": 3.0
            },
            "listening": {
                "gesture": "nod_small",
                "head_movement": "slight_tilt",
                "body_approach": "slight_forward",
                "duration": 0.5
            }
        }
        
        animation = interaction_animations.get(interaction_type, interaction_animations["listening"])
        
        return {
            "enabled": True,
            "interaction_type": interaction_type,
            "animation": animation
        }


# Initialize engine
animation_engine = ProceduralAnimationEngine()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Avatar Service")
    
    try:
        # Create tables in PostgreSQL
        postgres = await get_postgres()
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS avatar_configs (
                avatar_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                eye_tracking_config JSONB DEFAULT '{}',
                blink_config JSONB DEFAULT '{}',
                micro_expression_config JSONB DEFAULT '{}',
                head_look_config JSONB DEFAULT '{}',
                gesture_config JSONB DEFAULT '{}',
                breathing_config JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS avatar_states (
                state_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                avatar_id UUID NOT NULL,
                user_id UUID NOT NULL,
                eye_tracking_state JSONB DEFAULT '{}',
                blink_state JSONB DEFAULT '{}',
                micro_expressions JSONB DEFAULT '[]',
                head_look_state JSONB DEFAULT '{}',
                body_ik_state JSONB DEFAULT '{}',
                gesture_state JSONB DEFAULT '{}',
                breathing_state JSONB DEFAULT '{}',
                idle_variation_state JSONB DEFAULT '{}',
                emotion_animation_state JSONB DEFAULT '{}',
                interaction_animation_state JSONB DEFAULT '{}',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_avatar_configs_user ON avatar_configs(user_id)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_avatar_states_avatar ON avatar_states(avatar_id)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_avatar_states_user ON avatar_states(user_id)")
        await postgres.execute("CREATE INDEX IF NOT EXISTS idx_avatar_states_timestamp ON avatar_states(timestamp)")
        
        logger.info("Avatar Service started successfully")
    except Exception as e:
        logger.warning(f"Avatar Service startup initialization skipped: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Avatar Service")


# API endpoints
@app.post("/api/v1/avatar/config", status_code=status.HTTP_201_CREATED)
async def create_avatar_config(user_id: str):
    """
    Create avatar configuration with default settings
    """
    try:
        postgres = await get_postgres()
        
        avatar_id = await postgres.fetchval("""
            INSERT INTO avatar_configs (user_id, eye_tracking_config, blink_config, micro_expression_config, 
                                     head_look_config, gesture_config, breathing_config)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING avatar_id
        """, user_id, animation_engine.default_configs["eye_tracking"],
            animation_engine.default_configs["blink"],
            animation_engine.default_configs["micro_expressions"],
            animation_engine.default_configs["head_look"],
            animation_engine.default_configs["gesture"],
            animation_engine.default_configs["breathing"])
        
        logger.info(f"Created avatar config {avatar_id} for user {user_id}")
        
        return {
            "avatar_id": str(avatar_id),
            "user_id": user_id,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create avatar config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create avatar config: {str(e)}"
        )


@app.get("/api/v1/avatar/config/{avatar_id}")
async def get_avatar_config(avatar_id: str):
    """
    Get avatar configuration
    """
    try:
        postgres = await get_postgres()
        
        config = await postgres.fetchrow(
            "SELECT * FROM avatar_configs WHERE avatar_id = $1",
            avatar_id
        )
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar config not found"
            )
        
        return {
            "avatar_id": str(config["avatar_id"]),
            "user_id": str(config["user_id"]),
            "eye_tracking_config": config["eye_tracking_config"],
            "blink_config": config["blink_config"],
            "micro_expression_config": config["micro_expression_config"],
            "head_look_config": config["head_look_config"],
            "gesture_config": config["gesture_config"],
            "breathing_config": config["breathing_config"],
            "created_at": config["created_at"],
            "updated_at": config["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get avatar config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get avatar config: {str(e)}"
        )


@app.put("/api/v1/avatar/config/{avatar_id}/eye-tracking")
async def update_eye_tracking_config(avatar_id: str, config: EyeTrackingConfig):
    """
    Update eye tracking configuration
    """
    try:
        postgres = await get_postgres()
        
        await postgres.execute("""
            UPDATE avatar_configs
            SET eye_tracking_config = $2, updated_at = CURRENT_TIMESTAMP
            WHERE avatar_id = $1
        """, avatar_id, config.dict())
        
        # Cache in Redis
        redis = await get_redis()
        await redis.setex(f"avatar_config:{avatar_id}:eye_tracking", 3600, config.json())
        
        logger.info(f"Updated eye tracking config for avatar {avatar_id}")
        
        return {
            "avatar_id": avatar_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update eye tracking config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update eye tracking config: {str(e)}"
        )


@app.put("/api/v1/avatar/config/{avatar_id}/blink")
async def update_blink_config(avatar_id: str, config: BlinkConfig):
    """
    Update blink configuration
    """
    try:
        postgres = await get_postgres()
        
        await postgres.execute("""
            UPDATE avatar_configs
            SET blink_config = $2, updated_at = CURRENT_TIMESTAMP
            WHERE avatar_id = $1
        """, avatar_id, config.dict())
        
        logger.info(f"Updated blink config for avatar {avatar_id}")
        
        return {
            "avatar_id": avatar_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update blink config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update blink config: {str(e)}"
        )


@app.put("/api/v1/avatar/config/{avatar_id}/micro-expressions")
async def update_micro_expression_config(avatar_id: str, config: MicroExpressionConfig):
    """
    Update micro expression configuration
    """
    try:
        postgres = await get_postgres()
        
        await postgres.execute("""
            UPDATE avatar_configs
            SET micro_expression_config = $2, updated_at = CURRENT_TIMESTAMP
            WHERE avatar_id = $1
        """, avatar_id, config.dict())
        
        logger.info(f"Updated micro expression config for avatar {avatar_id}")
        
        return {
            "avatar_id": avatar_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update micro expression config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update micro expression config: {str(e)}"
        )


@app.put("/api/v1/avatar/config/{avatar_id}/head-look")
async def update_head_look_config(avatar_id: str, config: HeadLookConfig):
    """
    Update head look configuration
    """
    try:
        postgres = await get_postgres()
        
        await postgres.execute("""
            UPDATE avatar_configs
            SET head_look_config = $2, updated_at = CURRENT_TIMESTAMP
            WHERE avatar_id = $1
        """, avatar_id, config.dict())
        
        logger.info(f"Updated head look config for avatar {avatar_id}")
        
        return {
            "avatar_id": avatar_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update head look config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update head look config: {str(e)}"
        )


@app.put("/api/v1/avatar/config/{avatar_id}/gesture")
async def update_gesture_config(avatar_id: str, config: GestureConfig):
    """
    Update gesture configuration
    """
    try:
        postgres = await get_postgres()
        
        await postgres.execute("""
            UPDATE avatar_configs
            SET gesture_config = $2, updated_at = CURRENT_TIMESTAMP
            WHERE avatar_id = $1
        """, avatar_id, config.dict())
        
        logger.info(f"Updated gesture config for avatar {avatar_id}")
        
        return {
            "avatar_id": avatar_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update gesture config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update gesture config: {str(e)}"
        )


@app.put("/api/v1/avatar/config/{avatar_id}/breathing")
async def update_breathing_config(avatar_id: str, config: BreathingConfig):
    """
    Update breathing configuration
    """
    try:
        postgres = await get_postgres()
        
        await postgres.execute("""
            UPDATE avatar_configs
            SET breathing_config = $2, updated_at = CURRENT_TIMESTAMP
            WHERE avatar_id = $1
        """, avatar_id, config.dict())
        
        logger.info(f"Updated breathing config for avatar {avatar_id}")
        
        return {
            "avatar_id": avatar_id,
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update breathing config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update breathing config: {str(e)}"
        )


@app.post("/api/v1/avatar/animate", response_model=ProceduralAnimationResponse)
async def calculate_procedural_animation(request: ProceduralAnimationRequest):
    """
    Calculate procedural animation state for avatar
    """
    try:
        postgres = await get_postgres()
        
        # Get avatar configuration
        config = await postgres.fetchrow(
            "SELECT * FROM avatar_configs WHERE avatar_id = $1",
            request.avatar_id
        )
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar config not found"
            )
        
        # Parse configurations
        eye_config = EyeTrackingConfig(**config["eye_tracking_config"])
        blink_config = BlinkConfig(**config["blink_config"])
        micro_expr_config = MicroExpressionConfig(**config["micro_expression_config"])
        head_look_config = HeadLookConfig(**config["head_look_config"])
        gesture_config = GestureConfig(**config["gesture_config"])
        breathing_config = BreathingConfig(**config["breathing_config"])
        
        # Calculate all animation components
        eye_tracking = animation_engine.calculate_eye_tracking(eye_config, request.target_position)
        blink_state = animation_engine.calculate_blink(blink_config, 0, datetime.utcnow().timestamp())
        micro_expressions = animation_engine.calculate_micro_expressions(micro_expr_config, request.emotion)
        head_look = animation_engine.calculate_head_look(head_look_config, eye_tracking["left_rotation"], request.target_position)
        body_ik = animation_engine.calculate_body_ik(request.target_position)
        gesture_state = animation_engine.calculate_gesture(gesture_config, request.speech_active, request.emotion)
        breathing_state = animation_engine.calculate_breathing(breathing_config)
        idle_variation = animation_engine.calculate_idle_variation()
        emotion_animation = animation_engine.calculate_emotion_animation(request.emotion)
        interaction_animation = animation_engine.calculate_interaction_animation(request.interaction_type)
        
        # Create response
        response = ProceduralAnimationResponse(
            avatar_id=request.avatar_id,
            eye_left_rotation=eye_tracking["left_rotation"],
            eye_right_rotation=eye_tracking["right_rotation"],
            head_rotation=head_look["rotation"],
            blink_state=blink_state,
            micro_expressions=micro_expressions,
            body_ik_pose=body_ik,
            gesture_state=gesture_state,
            breathing_state=breathing_state
        )
        
        # Cache state in Redis for real-time access
        redis = await get_redis()
        state = {
            "avatar_id": request.avatar_id,
            "user_id": request.user_id,
            "eye_tracking": eye_tracking,
            "blink_state": blink_state,
            "micro_expressions": micro_expressions,
            "head_look": head_look,
            "body_ik": body_ik,
            "gesture_state": gesture_state,
            "breathing": breathing_state,
            "idle_variation": idle_variation,
            "emotion_animation": emotion_animation,
            "interaction_animation": interaction_animation,
            "timestamp": datetime.utcnow().isoformat()
        }
        await redis.setex(f"avatar_state:{request.avatar_id}:{request.user_id}", 5, str(state))
        
        logger.info(f"Calculated procedural animation for avatar {request.avatar_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate procedural animation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate procedural animation: {str(e)}"
        )


@app.get("/api/v1/avatar/state/{avatar_id}/{user_id}")
async def get_avatar_state(avatar_id: str, user_id: str):
    """
    Get current avatar state from cache
    """
    try:
        redis = await get_redis()
        
        cached_state = await redis.get(f"avatar_state:{avatar_id}:{user_id}")
        
        if cached_state:
            import json
            return json.loads(cached_state)
        
        # Return default state if not cached
        return {
            "avatar_id": avatar_id,
            "user_id": user_id,
            "eye_tracking": {"enabled": True, "left_rotation": {"x": 0, "y": 0, "z": 0}, "right_rotation": {"x": 0, "y": 0, "z": 0}},
            "blink_state": {"enabled": True, "is_blinking": False},
            "micro_expressions": [],
            "head_look": {"enabled": True, "rotation": {"x": 0, "y": 0, "z": 0}},
            "body_ik": {"pose": {}, "ik_active": True},
            "gesture_state": {"enabled": True, "active_gesture": None},
            "breathing": {"enabled": True, "breath_phase": 0.0},
            "idle_variation": {},
            "emotion_animation": {"enabled": False},
            "interaction_animation": {"enabled": False},
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get avatar state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get avatar state: {str(e)}"
        )


@app.get("/api/v1/avatar/capabilities")
async def get_avatar_capabilities():
    """
    Get available avatar animation capabilities
    """
    return {
        "eye_tracking": {
            "modes": ["user", "object", "random"],
            "features": ["saccade", "convergence", "pupil_dilation", "smooth_pursuit"]
        },
        "blink": {
            "types": ["normal", "double", "partial"],
            "features": ["timing_variance", "emotion_coupling"]
        },
        "micro_expressions": {
            "types": ["smile", "frown", "surprise", "confusion", "interest", "raised_eyebrows", "lowered_eyebrows"],
            "features": ["intensity_control", "duration_control", "emotion_coupling"]
        },
        "head_look": {
            "modes": ["eyes_follow", "independent", "user_focus"],
            "features": ["smooth_tracking", "return_to_center", "angle_limits"]
        },
        "body_ik": {
            "postures": ["standing", "sitting", "walking"],
            "features": ["spine_ik", "arm_ik", "hand_ik", "procedural_adjustment"]
        },
        "gesture": {
            "library": ["wave", "nod", "shake", "point", "thumbs_up", "hands_up", "hand_to_chin"],
            "features": ["speech_coupling", "emotion_coupling", "emphasis_gestures", "random_gestures"]
        },
        "breathing": {
            "patterns": ["natural", "deep", "shallow", "irregular"],
            "features": ["rate_control", "depth_control", "chest_movement", "shoulder_movement"]
        },
        "emotion_animation": {
            "emotions": ["happy", "sad", "angry", "surprised", "neutral", "fear", "disgust"],
            "features": ["intensity_control", "posture_change", "movement_energy"]
        },
        "interaction_animation": {
            "types": ["greeting", "farewell", "agreement", "disagreement", "thinking", "listening"],
            "features": ["gesture_combination", "body_approach", "head_movement"]
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "avatar-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8023)
