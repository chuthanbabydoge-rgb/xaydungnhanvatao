"""
Vision Agent - Visual processing and analysis
Processes images, performs object detection, facial recognition, and scene understanding
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid
import base64

from ...core.agent_base import BaseAgent, AgentMessage, MessageType


class VisionTaskType(Enum):
    """Types of vision tasks"""
    OBJECT_DETECTION = "object_detection"
    FACE_RECOGNITION = "face_recognition"
    SCENE_UNDERSTANDING = "scene_understanding"
    TEXT_RECOGNITION = "text_recognition"
    IMAGE_CLASSIFICATION = "image_classification"
    IMAGE_SEGMENTATION = "image_segmentation"
    MOTION_DETECTION = "motion_detection"
    QUALITY_ASSESSMENT = "quality_assessment"


class ImageFormat(Enum):
    """Supported image formats"""
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    BMP = "bmp"
    BASE64 = "base64"


@dataclass
class VisionTask:
    """Represents a vision processing task"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: VisionTaskType = VisionTaskType.OBJECT_DETECTION
    image_data: str = ""  # Base64 encoded image data
    image_format: ImageFormat = ImageFormat.BASE64
    image_url: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence_threshold: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "image_format": self.image_format.value,
            "image_url": self.image_url,
            "parameters": self.parameters,
            "confidence_threshold": self.confidence_threshold,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class DetectionResult:
    """Represents a detection result"""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    detected_objects: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "task_id": self.task_id,
            "detected_objects": self.detected_objects,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "metadata": self.metadata
        }


class VisionAgent(BaseAgent):
    """
    Vision Agent - Visual processing and analysis
    Processes images, performs object detection, facial recognition, and scene understanding
    """
    
    def __init__(
        self,
        agent_id: str = "vision-agent-1",
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        enable_tracing: bool = True,
        enable_metrics: bool = True
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="vision",
            rabbitmq_url=rabbitmq_url,
            enable_tracing=enable_tracing,
            enable_metrics=enable_metrics
        )
        
        # Task storage
        self.tasks: Dict[str, VisionTask] = {}
        self.results: Dict[str, DetectionResult] = {}
        
        # Vision models (simulated - in production, use real ML models)
        self.vision_models = self._load_vision_models()
        
        # Capabilities
        self.capabilities = [
            "object_detection",
            "face_recognition",
            "scene_understanding",
            "text_recognition",
            "image_classification",
            "image_segmentation",
            "motion_detection",
            "quality_assessment"
        ]
    
    def _load_vision_models(self) -> Dict[str, Any]:
        """Load vision processing models"""
        return {
            "object_classes": [
                "person", "car", "dog", "cat", "bird", "horse", "sheep", "cow",
                "elephant", "bear", "zebra", "giraffe", "truck", "bus", "motorcycle",
                "bicycle", "boat", "airplane", "train", "cell phone", "laptop"
            ],
            "face_features": [
                "eyes", "nose", "mouth", "ears", "jawline", "cheeks", "forehead"
            ],
            "scene_categories": [
                "indoor", "outdoor", "urban", "nature", "beach", "mountain",
                "forest", "desert", "office", "home", "street", "restaurant"
            ]
        }
    
    def register_handlers(self):
        """Register message handlers"""
        self.message_handlers[MessageType.TASK_REQUEST] = self.handle_task_request
        self.message_handlers[MessageType.QUERY] = self.handle_query
        self.message_handlers[MessageType.EVENT] = self.handle_event
    
    async def start(self):
        """Start the vision agent"""
        await super().start()
        
        # Announce capabilities
        await self.announce_capabilities()
    
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
        """Handle incoming vision task"""
        task_data = message.content
        
        # Create vision task
        task = VisionTask(
            task_type=VisionTaskType(task_data.get("task_type", "object_detection")),
            image_data=task_data.get("image_data", ""),
            image_format=ImageFormat(task_data.get("image_format", "base64")),
            image_url=task_data.get("image_url"),
            parameters=task_data.get("parameters", {}),
            confidence_threshold=task_data.get("confidence_threshold", 0.5),
            metadata=task_data.get("metadata", {})
        )
        
        self.tasks[task.task_id] = task
        
        # Execute vision task
        result = await self.execute_vision_task(task)
        
        return {
            "task_id": task.task_id,
            "result_id": result.result_id,
            "detected_count": len(result.detected_objects),
            "confidence": result.confidence
        }
    
    async def handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle query messages"""
        query_type = message.content.get("query_type")
        
        if query_type == "task_status":
            task_id = message.content.get("task_id")
            if task_id in self.tasks:
                return self.tasks[task_id].to_dict()
            else:
                return {"error": "Task not found"}
        
        elif query_type == "result_status":
            result_id = message.content.get("result_id")
            if result_id in self.results:
                return self.results[result_id].to_dict()
            else:
                return {"error": "Result not found"}
        
        elif query_type == "capabilities":
            return {"capabilities": self.capabilities}
        
        else:
            return {"error": "Unknown query type"}
    
    async def handle_event(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle event messages"""
        return {"status": "acknowledged"}
    
    async def execute_vision_task(self, task: VisionTask) -> DetectionResult:
        """Execute a vision processing task"""
        with self.tracer.start_as_current_span("execute_vision_task") as span:
            span.set_attribute("task_id", task.task_id)
            span.set_attribute("task_type", task.task_type.value)
            
            start_time = datetime.utcnow()
            result = DetectionResult(task_id=task.task_id)
            
            try:
                if task.task_type == VisionTaskType.OBJECT_DETECTION:
                    result = await self.detect_objects(task)
                elif task.task_type == VisionTaskType.FACE_RECOGNITION:
                    result = await self.recognize_faces(task)
                elif task.task_type == VisionTaskType.SCENE_UNDERSTANDING:
                    result = await self.understand_scene(task)
                elif task.task_type == VisionTaskType.TEXT_RECOGNITION:
                    result = await self.recognize_text(task)
                elif task.task_type == VisionTaskType.IMAGE_CLASSIFICATION:
                    result = await self.classify_image(task)
                elif task.task_type == VisionTaskType.IMAGE_SEGMENTATION:
                    result = await self.segment_image(task)
                elif task.task_type == VisionTaskType.MOTION_DETECTION:
                    result = await self.detect_motion(task)
                elif task.task_type == VisionTaskType.QUALITY_ASSESSMENT:
                    result = await self.assess_quality(task)
                
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                result.processing_time = processing_time
                
                self.results[result.result_id] = result
                
            except Exception as e:
                self.logger.error(f"Vision task error: {e}")
                result.detected_objects = []
                result.confidence = 0.0
            
            return result
    
    async def detect_objects(self, task: VisionTask) -> DetectionResult:
        """Detect objects in image"""
        result = DetectionResult(task_id=task.task_id)
        
        # Simulate object detection (in production, use real ML models)
        object_classes = self.vision_models["object_classes"]
        
        # Randomly select some objects to "detect"
        import random
        num_objects = random.randint(1, 5)
        selected_objects = random.sample(object_classes, min(num_objects, len(object_classes)))
        
        detected_objects = []
        for obj_class in selected_objects:
            confidence = random.uniform(0.6, 0.95)
            
            if confidence >= task.confidence_threshold:
                detected_objects.append({
                    "class": obj_class,
                    "confidence": confidence,
                    "bounding_box": {
                        "x": random.randint(0, 100),
                        "y": random.randint(0, 100),
                        "width": random.randint(50, 200),
                        "height": random.randint(50, 200)
                    }
                })
        
        result.detected_objects = detected_objects
        result.confidence = sum(obj["confidence"] for obj in detected_objects) / len(detected_objects) if detected_objects else 0.0
        
        return result
    
    async def recognize_faces(self, task: VisionTask) -> DetectionResult:
        """Recognize faces in image"""
        result = DetectionResult(task_id=task.task_id)
        
        # Simulate face recognition
        import random
        num_faces = random.randint(0, 3)
        
        detected_objects = []
        for i in range(num_faces):
            confidence = random.uniform(0.7, 0.95)
            
            if confidence >= task.confidence_threshold:
                detected_objects.append({
                    "class": "face",
                    "confidence": confidence,
                    "face_id": f"face_{i}",
                    "bounding_box": {
                        "x": random.randint(0, 100),
                        "y": random.randint(0, 100),
                        "width": random.randint(50, 150),
                        "height": random.randint(50, 150)
                    },
                    "features": {
                        "eyes": random.choice(["open", "closed"]),
                        "mouth": random.choice(["smile", "neutral", "frown"]),
                        "gaze_direction": random.choice(["left", "right", "center"])
                    }
                })
        
        result.detected_objects = detected_objects
        result.confidence = sum(obj["confidence"] for obj in detected_objects) / len(detected_objects) if detected_objects else 0.0
        
        return result
    
    async def understand_scene(self, task: VisionTask) -> DetectionResult:
        """Understand scene context"""
        result = DetectionResult(task_id=task.task_id)
        
        # Simulate scene understanding
        import random
        scene_categories = self.vision_models["scene_categories"]
        
        detected_objects = []
        num_scenes = random.randint(1, 2)
        selected_scenes = random.sample(scene_categories, min(num_scenes, len(scene_categories)))
        
        for scene in selected_scenes:
            confidence = random.uniform(0.6, 0.9)
            
            if confidence >= task.confidence_threshold:
                detected_objects.append({
                    "class": "scene",
                    "scene_type": scene,
                    "confidence": confidence,
                    "attributes": {
                        "lighting": random.choice(["bright", "normal", "dim"]),
                        "weather": random.choice(["sunny", "cloudy", "rainy"]) if scene == "outdoor" else "indoor",
                        "time_of_day": random.choice(["morning", "afternoon", "evening", "night"])
                    }
                })
        
        result.detected_objects = detected_objects
        result.confidence = sum(obj["confidence"] for obj in detected_objects) / len(detected_objects) if detected_objects else 0.0
        
        return result
    
    async def recognize_text(self, task: VisionTask) -> DetectionResult:
        """Recognize text in image (OCR)"""
        result = DetectionResult(task_id=task.task_id)
        
        # Simulate text recognition
        import random
        num_text_regions = random.randint(0, 3)
        
        detected_objects = []
        sample_texts = ["Hello World", "Sample Text", "12345", "Label", "Warning"]
        
        for i in range(num_text_regions):
            confidence = random.uniform(0.7, 0.95)
            
            if confidence >= task.confidence_threshold:
                detected_objects.append({
                    "class": "text",
                    "confidence": confidence,
                    "text": random.choice(sample_texts),
                    "bounding_box": {
                        "x": random.randint(0, 100),
                        "y": random.randint(0, 100),
                        "width": random.randint(50, 150),
                        "height": random.randint(20, 50)
                    },
                    "language": "en"
                })
        
        result.detected_objects = detected_objects
        result.confidence = sum(obj["confidence"] for obj in detected_objects) / len(detected_objects) if detected_objects else 0.0
        
        return result
    
    async def classify_image(self, task: VisionTask) -> DetectionResult:
        """Classify image content"""
        result = DetectionResult(task_id=task.task_id)
        
        # Simulate image classification
        import random
        categories = ["nature", "urban", "people", "animals", "vehicles", "food", "art"]
        
        detected_objects = []
        for category in random.sample(categories, 3):
            confidence = random.uniform(0.5, 0.9)
            
            if confidence >= task.confidence_threshold:
                detected_objects.append({
                    "class": "category",
                    "category": category,
                    "confidence": confidence
                })
        
        result.detected_objects = detected_objects
        result.confidence = max(obj["confidence"] for obj in detected_objects) if detected_objects else 0.0
        
        return result
    
    async def segment_image(self, task: VisionTask) -> DetectionResult:
        """Segment image into regions"""
        result = DetectionResult(task_id=task.task_id)
        
        # Simulate image segmentation
        import random
        num_segments = random.randint(2, 5)
        
        detected_objects = []
        for i in range(num_segments):
            confidence = random.uniform(0.6, 0.9)
            
            if confidence >= task.confidence_threshold:
                detected_objects.append({
                    "class": "segment",
                    "segment_id": f"segment_{i}",
                    "confidence": confidence,
                    "region": {
                        "x": random.randint(0, 100),
                        "y": random.randint(0, 100),
                        "width": random.randint(50, 200),
                        "height": random.randint(50, 200)
                    },
                    "label": random.choice(["background", "foreground", "object", "person"])
                })
        
        result.detected_objects = detected_objects
        result.confidence = sum(obj["confidence"] for obj in detected_objects) / len(detected_objects) if detected_objects else 0.0
        
        return result
    
    async def detect_motion(self, task: VisionTask) -> DetectionResult:
        """Detect motion in image/video"""
        result = DetectionResult(task_id=task.task_id)
        
        # Simulate motion detection
        import random
        has_motion = random.choice([True, False])
        
        if has_motion:
            detected_objects = [{
                "class": "motion",
                "confidence": random.uniform(0.7, 0.95),
                "motion_regions": [
                    {
                        "x": random.randint(0, 100),
                        "y": random.randint(0, 100),
                        "width": random.randint(30, 100),
                        "height": random.randint(30, 100),
                        "intensity": random.uniform(0.5, 1.0)
                    }
                ]
            }]
            result.confidence = detected_objects[0]["confidence"]
        else:
            detected_objects = [{
                "class": "motion",
                "confidence": 0.9,
                "motion_detected": False
            }]
            result.confidence = 0.9
        
        result.detected_objects = detected_objects
        
        return result
    
    async def assess_quality(self, task: VisionTask) -> DetectionResult:
        """Assess image quality"""
        result = DetectionResult(task_id=task.task_id)
        
        # Simulate quality assessment
        import random
        
        quality_metrics = {
            "sharpness": random.uniform(0.5, 1.0),
            "brightness": random.uniform(0.4, 0.9),
            "contrast": random.uniform(0.5, 1.0),
            "noise_level": random.uniform(0.0, 0.3),
            "color_balance": random.uniform(0.6, 1.0)
        }
        
        overall_quality = sum(quality_metrics.values()) / len(quality_metrics)
        
        detected_objects = [{
            "class": "quality",
            "overall_quality": overall_quality,
            "metrics": quality_metrics,
            "quality_rating": "high" if overall_quality > 0.8 else "medium" if overall_quality > 0.6 else "low"
        }]
        
        result.detected_objects = detected_objects
        result.confidence = overall_quality
        
        return result
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a vision task"""
        vision_task = VisionTask(
            task_type=VisionTaskType(task.get("task_type", "object_detection")),
            image_data=task.get("image_data", ""),
            image_format=ImageFormat(task.get("image_format", "base64")),
            confidence_threshold=task.get("confidence_threshold", 0.5)
        )
        
        result = await self.execute_vision_task(vision_task)
        
        return result.to_dict()


async def main():
    """Main entry point for the vision agent"""
    agent = VisionAgent()
    
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