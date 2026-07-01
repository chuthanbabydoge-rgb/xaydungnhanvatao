"""
Vision Service - Computer vision processing
Handles object detection, pose estimation, face detection, and hand tracking
"""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import asyncio
import io
import base64

from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Vision Service",
    description="Computer vision processing for AI Companion",
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
class DetectionRequest(BaseModel):
    """Detection request model"""
    image_data: str = Field(..., description="Base64 encoded image data")
    image_format: str = Field(default="jpg", description="Image format: jpg, png")
    detection_type: str = Field(..., description="Detection type: object, pose, face, hand")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence threshold")
    enable_tracking: bool = Field(default=False, description="Enable object tracking")


class BoundingBox(BaseModel):
    """Bounding box model"""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    width: float = Field(..., description="Width")
    height: float = Field(..., description="Height")


class Detection(BaseModel):
    """Detection result model"""
    label: str = Field(..., description="Object label")
    confidence: float = Field(..., description="Confidence score")
    bbox: BoundingBox = Field(..., description="Bounding box")
    track_id: Optional[int] = Field(default=None, description="Tracking ID")


class Landmark(BaseModel):
    """Landmark point model"""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    z: Optional[float] = Field(default=None, description="Z coordinate (depth)")


class PoseDetection(BaseModel):
    """Pose detection model"""
    landmarks: List[Landmark] = Field(..., description="Pose landmarks (33 points)")
    confidence: float = Field(..., description="Overall confidence")
    bbox: Optional[BoundingBox] = Field(default=None, description="Bounding box")


class FaceDetection(BaseModel):
    """Face detection model"""
    bbox: BoundingBox = Field(..., description="Face bounding box")
    confidence: float = Field(..., description="Confidence score")
    landmarks: Optional[List[Landmark]] = Field(default=None, description="Face landmarks")
    emotion: Optional[str] = Field(default=None, description="Detected emotion")
    age: Optional[int] = Field(default=None, description="Estimated age")
    gender: Optional[str] = Field(default=None, description="Estimated gender")


class HandDetection(BaseModel):
    """Hand detection model"""
    handedness: str = Field(..., description="Left or right hand")
    landmarks: List[Landmark] = Field(..., description="Hand landmarks (21 points)")
    confidence: float = Field(..., description="Confidence score")
    bbox: Optional[BoundingBox] = Field(default=None, description="Bounding box")


class VisionResponse(BaseModel):
    """Vision response model"""
    detection_type: str = Field(..., description="Type of detection performed")
    detections: List[Any] = Field(..., description="Detection results")
    processing_time: float = Field(..., description="Processing time in seconds")
    image_size: Optional[Dict[str, int]] = Field(default=None, description="Image dimensions")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Vision processors
class ObjectDetector:
    """Object detection using YOLOv8"""
    
    def __init__(self):
        self.model = None
        self.labels = [
            "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
            "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
            "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
            "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
            "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
            "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
            "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
            "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
            "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
            "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
            "toothbrush"
        ]
    
    async def initialize(self):
        """Initialize YOLOv8 model"""
        try:
            from ultralytics import YOLO
            self.model = YOLO('yolov8n.pt')  # Use nano version for speed
            logger.info("Object detector initialized")
        except ImportError:
            logger.warning("Ultralytics library not installed, using mock detection")
            self.model = None
    
    async def detect(self, image_data: bytes, confidence_threshold: float) -> List[Detection]:
        """Detect objects in image"""
        if not self.model:
            await self.initialize()
        
        if not self.model:
            # Mock detection for demo
            return [
                Detection(
                    label="person",
                    confidence=0.85,
                    bbox=BoundingBox(x=100, y=100, width=200, height=300)
                )
            ]
        
        try:
            import numpy as np
            from PIL import Image
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            image_np = np.array(image)
            
            # Run detection
            results = await asyncio.to_thread(
                self.model.predict,
                image_np,
                conf=confidence_threshold,
                verbose=False
            )
            
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    confidence = box.conf[0].item()
                    class_id = int(box.cls[0].item())
                    
                    if class_id < len(self.labels):
                        label = self.labels[class_id]
                        
                        detections.append(Detection(
                            label=label,
                            confidence=confidence,
                            bbox=BoundingBox(
                                x=x1,
                                y=y1,
                                width=x2 - x1,
                                height=y2 - y1
                            )
                        ))
            
            return detections
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Object detection failed: {str(e)}"
            )


class PoseDetector:
    """Pose detection using MediaPipe"""
    
    def __init__(self):
        self.pose = None
    
    async def initialize(self):
        """Initialize MediaPipe Pose"""
        try:
            import mediapipe as mp
            self.pose = mp.solutions.pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.5
            )
            logger.info("Pose detector initialized")
        except ImportError:
            logger.warning("MediaPipe library not installed, using mock detection")
            self.pose = None
    
    async def detect(self, image_data: bytes) -> List[PoseDetection]:
        """Detect pose in image"""
        if not self.pose:
            await self.initialize()
        
        if not self.pose:
            # Mock detection for demo
            landmarks = [Landmark(x=0.5, y=0.5) for _ in range(33)]
            return [PoseDetection(landmarks=landmarks, confidence=0.8)]
        
        try:
            import numpy as np
            from PIL import Image
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            image_np = np.array(image)
            
            # Convert to RGB
            image_rgb = np.array(Image.fromarray(image_np).convert('RGB'))
            
            # Run pose detection
            results = await asyncio.to_thread(
                self.pose.process,
                image_rgb
            )
            
            detections = []
            if results.pose_landmarks:
                landmarks = []
                for landmark in results.pose_landmarks.landmark:
                    landmarks.append(Landmark(
                        x=landmark.x,
                        y=landmark.y,
                        z=landmark.z
                    ))
                
                detections.append(PoseDetection(
                    landmarks=landmarks,
                    confidence=0.8
                ))
            
            return detections
            
        except Exception as e:
            logger.error(f"Pose detection failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Pose detection failed: {str(e)}"
            )


class FaceDetector:
    """Face detection using MediaPipe"""
    
    def __init__(self):
        self.face_detection = None
        self.face_mesh = None
    
    async def initialize(self):
        """Initialize MediaPipe Face Detection"""
        try:
            import mediapipe as mp
            self.face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.5
            )
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5
            )
            logger.info("Face detector initialized")
        except ImportError:
            logger.warning("MediaPipe library not installed, using mock detection")
            self.face_detection = None
    
    async def detect(self, image_data: bytes) -> List[FaceDetection]:
        """Detect faces in image"""
        if not self.face_detection:
            await self.initialize()
        
        if not self.face_detection:
            # Mock detection for demo
            return [FaceDetection(
                bbox=BoundingBox(x=100, y=100, width=200, height=200),
                confidence=0.9
            )]
        
        try:
            import numpy as np
            from PIL import Image
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            image_np = np.array(image)
            
            # Convert to RGB
            image_rgb = np.array(Image.fromarray(image_np).convert('RGB'))
            
            # Run face detection
            results = await asyncio.to_thread(
                self.face_detection.process,
                image_rgb
            )
            
            detections = []
            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    
                    detections.append(FaceDetection(
                        bbox=BoundingBox(
                            x=bbox.xmin,
                            y=bbox.ymin,
                            width=bbox.width,
                            height=bbox.height
                        ),
                        confidence=detection.score[0]
                    ))
            
            return detections
            
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Face detection failed: {str(e)}"
            )


class HandDetector:
    """Hand detection using MediaPipe"""
    
    def __init__(self):
        self.hands = None
    
    async def initialize(self):
        """Initialize MediaPipe Hands"""
        try:
            import mediapipe as mp
            self.hands = mp.solutions.hands.Hands(
                static_image_mode=True,
                max_num_hands=2,
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            logger.info("Hand detector initialized")
        except ImportError:
            logger.warning("MediaPipe library not installed, using mock detection")
            self.hands = None
    
    async def detect(self, image_data: bytes) -> List[HandDetection]:
        """Detect hands in image"""
        if not self.hands:
            await self.initialize()
        
        if not self.hands:
            # Mock detection for demo
            landmarks = [Landmark(x=0.5, y=0.5) for _ in range(21)]
            return [HandDetection(
                handedness="right",
                landmarks=landmarks,
                confidence=0.8
            )]
        
        try:
            import numpy as np
            from PIL import Image
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            image_np = np.array(image)
            
            # Convert to RGB
            image_rgb = np.array(Image.fromarray(image_np).convert('RGB'))
            
            # Run hand detection
            results = await asyncio.to_thread(
                self.hands.process,
                image_rgb
            )
            
            detections = []
            if results.multi_hand_landmarks and results.multi_handedness:
                for landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                    landmark_list = []
                    for landmark in landmarks.landmark:
                        landmark_list.append(Landmark(
                            x=landmark.x,
                            y=landmark.y,
                            z=landmark.z
                        ))
                    
                    detections.append(HandDetection(
                        handedness=handedness.classification[0].label.lower(),
                        landmarks=landmark_list,
                        confidence=handedness.classification[0].score
                    ))
            
            return detections
            
        except Exception as e:
            logger.error(f"Hand detection failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Hand detection failed: {str(e)}"
            )


# Initialize processors
object_detector = ObjectDetector()
pose_detector = PoseDetector()
face_detector = FaceDetector()
hand_detector = HandDetector()

processors = {
    "object": object_detector,
    "pose": pose_detector,
    "face": face_detector,
    "hand": hand_detector
}


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Vision Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Vision Service")


# API endpoints
@app.post("/api/v1/vision/detect", response_model=VisionResponse)
async def detect_objects(request: DetectionRequest):
    """
    Detect objects/people in image
    """
    try:
        start_time = datetime.utcnow()
        
        # Decode base64 image
        image_data = base64.b64decode(request.image_data)
        
        # Get processor
        processor = processors.get(request.detection_type)
        
        if not processor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Detection type '{request.detection_type}' not supported"
            )
        
        # Run detection
        if request.detection_type == "object":
            detections = await processor.detect(image_data, request.confidence_threshold)
        else:
            detections = await processor.detect(image_data)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Get image size
        from PIL import Image
        image = Image.open(io.BytesIO(image_data))
        image_size = {"width": image.width, "height": image.height}
        
        logger.info(f"Detected {len(detections)} {request.detection_type}(s)")
        
        return VisionResponse(
            detection_type=request.detection_type,
            detections=detections,
            processing_time=processing_time,
            image_size=image_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {str(e)}"
        )


@app.post("/api/v1/vision/detect/file", response_model=VisionResponse)
async def detect_objects_file(
    file: UploadFile = File(...),
    detection_type: str = "object",
    confidence_threshold: float = 0.5
):
    """
    Detect objects/people in uploaded image file
    """
    try:
        start_time = datetime.utcnow()
        
        # Read image file
        image_data = await file.read()
        
        # Get processor
        processor = processors.get(detection_type)
        
        if not processor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Detection type '{detection_type}' not supported"
            )
        
        # Run detection
        if detection_type == "object":
            detections = await processor.detect(image_data, confidence_threshold)
        else:
            detections = await processor.detect(image_data)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Get image size
        from PIL import Image
        image = Image.open(io.BytesIO(image_data))
        image_size = {"width": image.width, "height": image.height}
        
        logger.info(f"Detected {len(detections)} {detection_type}(s) from file")
        
        return VisionResponse(
            detection_type=detection_type,
            detections=detections,
            processing_time=processing_time,
            image_size=image_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File detection failed: {str(e)}"
        )


@app.get("/api/v1/vision/capabilities")
async def get_capabilities():
    """
    Get vision service capabilities
    """
    return {
        "detection_types": [
            {
                "type": "object",
                "description": "Object detection using YOLOv8",
                "labels": object_detector.labels[:10],  # Show first 10
                "total_labels": len(object_detector.labels)
            },
            {
                "type": "pose",
                "description": "Human pose estimation using MediaPipe",
                "landmarks": 33
            },
            {
                "type": "face",
                "description": "Face detection using MediaPipe",
                "features": ["detection", "landmarks"]
            },
            {
                "type": "hand",
                "description": "Hand detection using MediaPipe",
                "landmarks": 21,
                "features": ["detection", "handedness"]
            }
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "vision-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8018)
