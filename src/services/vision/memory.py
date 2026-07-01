"""
Vision Memory Service - Visual observation, visual memory storage, and visual recognition
"""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
import base64

from shared.database.mongodb import get_mongodb
from shared.database.redis import get_redis
from shared.database.qdrant import get_qdrant
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Vision Memory Service",
    description="Visual observation, visual memory storage, and visual recognition for AI Companion",
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
class VisualObservation(BaseModel):
    """Visual observation model"""
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID")
    image_data: str = Field(..., description="Base64 encoded image data")
    position: Optional[Dict[str, float]] = Field(default=None, description="3D position coordinates")
    rotation: Optional[Dict[str, float]] = Field(default=None, description="Rotation coordinates")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class VisualFeatures(BaseModel):
    """Visual features model"""
    objects: List[str] = Field(..., description="Detected objects")
    colors: List[Dict[str, Any]] = Field(..., description="Detected colors")
    layout: str = Field(..., description="Scene layout description")
    features: Dict[str, Any] = Field(default_factory=dict, description="Additional features")


class VisualMemoryEntry(BaseModel):
    """Visual memory entry model"""
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID")
    observation_id: str = Field(..., description="Related observation ID")
    features: VisualFeatures = Field(..., description="Visual features")
    embedding: Optional[List[float]] = Field(default=None, description="Visual embedding vector")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = Field(default=0, description="Number of times accessed")


class VisualRecognitionRequest(BaseModel):
    """Visual recognition request"""
    user_id: str = Field(..., description="User ID")
    image_data: str = Field(..., description="Base64 encoded image data")
    recognition_type: str = Field(..., description="Type of recognition: objects, person, location")


class VisualRecognitionResponse(BaseModel):
    """Visual recognition response"""
    recognition_type: str = Field(..., description="Type of recognition")
    results: List[Dict[str, Any]] = Field(..., description="Recognition results")
    confidence: float = Field(..., description="Overall confidence score")


class VisualRecallRequest(BaseModel):
    """Visual recall request"""
    user_id: str = Field(..., description="User ID")
    object_name: str = Field(..., description="Object name to recall")
    time_threshold: Optional[int] = Field(default=86400, description="Time threshold in seconds (default 24 hours)")


class VisualRecallResponse(BaseModel):
    """Visual recall response"""
    object_name: str = Field(..., description="Object name")
    recall_text: Optional[str] = Field(default=None, description="Natural language recall")
    memories: List[VisualMemoryEntry] = Field(..., description="Related visual memories")
    found: bool = Field(..., description="Whether object was found in memory")


# Visual observation system
class VisualObservationSystem:
    """Records and processes visual observations"""
    
    async def record_observation(self, observation: VisualObservation) -> str:
        """Record a visual observation"""
        db = await get_mongodb()
        observations = db["visual_observations"]
        
        # Store observation
        await observations.insert_one(observation.dict())
        
        logger.info(f"Recorded visual observation {observation.observation_id}")
        
        return observation.observation_id
    
    async def extract_features(self, image_data: str) -> VisualFeatures:
        """Extract visual features from image"""
        # Placeholder: In production, this would use computer vision models
        # For now, return placeholder features
        
        # Decode image to analyze (placeholder)
        # In production, use OpenCV, MediaPipe, YOLOv8, etc.
        
        objects = self._detect_objects_placeholder(image_data)
        colors = self._detect_colors_placeholder(image_data)
        layout = self._detect_layout_placeholder(image_data)
        
        return VisualFeatures(
            objects=objects,
            colors=colors,
            layout=layout,
            features={
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def _detect_objects_placeholder(self, image_data: str) -> List[str]:
        """Placeholder object detection"""
        # In production, use YOLOv8 or similar
        return ["desk", "laptop", "keyboard", "mouse", "coffee_cup"]
    
    def _detect_colors_placeholder(self, image_data: str) -> List[Dict[str, Any]]:
        """Placeholder color detection"""
        # In production, use color analysis
        return [
            {"color": "white", "hex": "#FFFFFF", "dominance": 0.4},
            {"color": "black", "hex": "#000000", "dominance": 0.3},
            {"color": "gray", "hex": "#808080", "dominance": 0.2}
        ]
    
    def _detect_layout_placeholder(self, image_data: str) -> str:
        """Placeholder layout detection"""
        # In production, use scene analysis
        return "office_desk_setup"


# Visual memory system
class VisualMemorySystem:
    """Stores and retrieves visual memories"""
    
    async def store_memory(
        self,
        user_id: str,
        observation_id: str,
        features: VisualFeatures,
        embedding: Optional[List[float]] = None
    ) -> str:
        """Store a visual memory"""
        db = await get_mongodb()
        memories = db["visual_memories"]
        
        # Create memory entry
        memory = VisualMemoryEntry(
            user_id=user_id,
            observation_id=observation_id,
            features=features,
            embedding=embedding
        )
        
        # Store in MongoDB
        await memories.insert_one(memory.dict())
        
        # Store in Qdrant if embedding provided
        if embedding:
            from qdrant_client.models import PointStruct
            
            client = await get_qdrant()
            
            point = PointStruct(
                id=memory.memory_id,
                vector=embedding,
                payload={
                    "user_id": user_id,
                    "observation_id": observation_id,
                    "objects": features.objects,
                    "timestamp": memory.timestamp
                }
            )
            
            # Insert into visual memories collection
            try:
                from shared.database.qdrant import insert_points
                await insert_points("visual_memories", [point])
            except Exception as e:
                logger.warning(f"Failed to store in Qdrant: {e}")
        
        logger.info(f"Stored visual memory {memory.memory_id}")
        
        return memory.memory_id
    
    async def retrieve_by_object(self, user_id: str, object_name: str) -> List[VisualMemoryEntry]:
        """Retrieve visual memories by object name"""
        db = await get_mongodb()
        memories = db["visual_memories"]
        
        cursor = memories.find({
            "user_id": user_id,
            "features.objects": object_name
        }).sort("timestamp", -1).limit(20)
        
        result = []
        async for memory_doc in cursor:
            memory_doc.pop("_id", None)
            result.append(VisualMemoryEntry(**memory_doc))
        
        # Update access count
        for memory in result:
            await memories.update_one(
                {"memory_id": memory.memory_id},
                {
                    "$inc": {"access_count": 1},
                    "$set": {"last_accessed": datetime.utcnow().isoformat()}
                }
            )
        
        return result
    
    async def retrieve_similar(
        self,
        user_id: str,
        query_embedding: List[float],
        limit: int = 10
    ) -> List[VisualMemoryEntry]:
        """Retrieve similar visual memories using vector search"""
        from shared.database.qdrant import search_points
        
        # Search in Qdrant
        results = await search_points(
            "visual_memories",
            query_embedding,
            limit=limit,
            score_threshold=0.7
        )
        
        # Filter by user_id
        filtered_results = [
            result for result in results
            if result["payload"].get("user_id") == user_id
        ]
        
        # Get full memory entries from MongoDB
        db = await get_mongodb()
        memories = db["visual_memories"]
        
        memory_entries = []
        for result in filtered_results:
            memory_doc = await memories.find_one({"memory_id": result["id"]})
            if memory_doc:
                memory_doc.pop("_id", None)
                memory_entries.append(VisualMemoryEntry(**memory_doc))
        
        return memory_entries
    
    async def recall_visual(self, user_id: str, object_name: str, time_threshold: int = 86400) -> str:
        """Generate natural language recall of visual memory"""
        memories = await self.retrieve_by_object(user_id, object_name)
        
        if not memories:
            return None
        
        # Check if any memory is within time threshold
        current_time = datetime.utcnow()
        
        for memory in memories:
            memory_time = datetime.fromisoformat(memory.timestamp)
            time_diff = (current_time - memory_time).total_seconds()
            
            if time_diff < time_threshold:
                # Generate recall text
                hours_ago = int(time_diff / 3600)
                
                if hours_ago < 1:
                    return f"Anh vẫn dùng chiếc {object_name} vừa rồi."
                elif hours_ago < 24:
                    return f"Anh vẫn dùng chiếc {object_name} hôm qua."
                else:
                    days_ago = int(hours_ago / 24)
                    return f"Anh đã dùng chiếc {object_name} {days_ago} ngày trước."
        
        return None


# Visual recognition system
class VisualRecognitionSystem:
    """Recognizes objects, people, and locations from images"""
    
    async def recognize_objects(self, image_data: str) -> List[Dict[str, Any]]:
        """Recognize objects in image"""
        # Placeholder: In production, use YOLOv8 or similar
        detected_objects = [
            {"object": "laptop", "confidence": 0.95, "bbox": [100, 100, 300, 200]},
            {"object": "keyboard", "confidence": 0.92, "bbox": [50, 250, 400, 300]},
            {"object": "mouse", "confidence": 0.88, "bbox": [350, 280, 400, 320]},
            {"object": "coffee_cup", "confidence": 0.85, "bbox": [420, 150, 450, 200]}
        ]
        
        return detected_objects
    
    async def recognize_person(self, image_data: str) -> bool:
        """Recognize if person is in image"""
        # Placeholder: In production, use face detection/recognition
        return True
    
    async def recognize_location(self, image_data: str) -> str:
        """Recognize location from image"""
        # Placeholder: In production, use scene classification
        return "office_desk"
    
    async def recognize(self, request: VisualRecognitionRequest) -> VisualRecognitionResponse:
        """Perform visual recognition based on type"""
        if request.recognition_type == "objects":
            results = await self.recognize_objects(request.image_data)
            confidence = sum(r["confidence"] for r in results) / len(results) if results else 0.0
        elif request.recognition_type == "person":
            is_person = await self.recognize_person(request.image_data)
            results = [{"person_detected": is_person}]
            confidence = 0.9 if is_person else 0.1
        elif request.recognition_type == "location":
            location = await self.recognize_location(request.image_data)
            results = [{"location": location}]
            confidence = 0.8
        else:
            results = []
            confidence = 0.0
        
        return VisualRecognitionResponse(
            recognition_type=request.recognition_type,
            results=results,
            confidence=confidence
        )


# Global instances
visual_observation = VisualObservationSystem()
visual_memory = VisualMemorySystem()
visual_recognition = VisualRecognitionSystem()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Vision Memory Service")
    
    # Create Qdrant collection for visual memories
    from shared.database.qdrant import create_collection
    await create_collection("visual_memories", vector_size=512)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Vision Memory Service")


# API endpoints
@app.post("/api/v1/vision/observe", status_code=status.HTTP_201_CREATED)
async def record_observation(request: VisualObservation):
    """
    Record a visual observation
    """
    try:
        observation_id = await visual_observation.record_observation(request)
        
        # Extract features
        features = await visual_observation.extract_features(request.image_data)
        
        # Generate embedding (placeholder)
        # In production, use actual visual embedding model
        embedding = [0.0] * 512  # Placeholder
        
        # Store memory
        memory_id = await visual_memory.store_memory(
            request.user_id,
            observation_id,
            features,
            embedding
        )
        
        return {
            "observation_id": observation_id,
            "memory_id": memory_id,
            "features": features.dict(),
            "status": "recorded"
        }
        
    except Exception as e:
        logger.error(f"Failed to record observation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record observation: {str(e)}"
        )


@app.post("/api/v1/vision/recognize")
async def recognize_visual(request: VisualRecognitionRequest):
    """
    Perform visual recognition
    """
    try:
        response = await visual_recognition.recognize(request)
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Failed to recognize visual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recognize visual: {str(e)}"
        )


@app.post("/api/v1/vision/recall")
async def recall_visual(request: VisualRecallRequest):
    """
    Recall visual memory
    """
    try:
        recall_text = await visual_memory.recall_visual(
            request.user_id,
            request.object_name,
            request.time_threshold
        )
        
        memories = await visual_memory.retrieve_by_object(
            request.user_id,
            request.object_name
        )
        
        return VisualRecallResponse(
            object_name=request.object_name,
            recall_text=recall_text,
            memories=memories,
            found=recall_text is not None
        )
        
    except Exception as e:
        logger.error(f"Failed to recall visual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recall visual: {str(e)}"
        )


@app.get("/api/v1/vision/memories/{user_id}")
async def get_visual_memories(user_id: str, limit: int = 20):
    """
    Get visual memories for a user
    """
    try:
        db = await get_mongodb()
        memories = db["visual_memories"]
        
        cursor = memories.find({"user_id": user_id}) \
            .sort("timestamp", -1) \
            .limit(limit)
        
        result = []
        async for memory_doc in cursor:
            memory_doc.pop("_id", None)
            result.append(VisualMemoryEntry(**memory_doc))
        
        return {
            "user_id": user_id,
            "memories": [memory.dict() for memory in result],
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Failed to get visual memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get visual memories: {str(e)}"
        )


@app.get("/api/v1/vision/memories/{user_id}/objects/{object_name}")
async def get_memories_by_object(user_id: str, object_name: str):
    """
    Get visual memories by object name
    """
    try:
        memories = await visual_memory.retrieve_by_object(user_id, object_name)
        
        return {
            "user_id": user_id,
            "object_name": object_name,
            "memories": [memory.dict() for memory in memories],
            "count": len(memories)
        }
        
    except Exception as e:
        logger.error(f"Failed to get memories by object: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memories by object: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "vision-memory-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8014)
