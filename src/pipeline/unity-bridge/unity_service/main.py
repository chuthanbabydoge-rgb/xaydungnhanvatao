"""
Unity Integration Service - Real-time rendering, physics simulation, and scene management
Handles Unity engine integration for the AI character pipeline
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from prometheus_client import Counter, Histogram, Gauge, start_http_server


class UnityEventType(Enum):
    """Types of Unity events"""
    SCENE_LOADED = "scene_loaded"
    OBJECT_CREATED = "object_created"
    OBJECT_DESTROYED = "object_destroyed"
    COLLISION = "collision"
    TRIGGER = "trigger"
    ANIMATION_EVENT = "animation_event"
    PHYSICS_EVENT = "physics_event"
    INPUT_EVENT = "input_event"


class RenderQuality(Enum):
    """Render quality presets"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CUSTOM = "custom"


@dataclass
class UnityScene:
    """Represents a Unity scene"""
    scene_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    path: str = ""
    objects: List[str] = field(default_factory=list)
    is_loaded: bool = False
    load_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "path": self.path,
            "objects": self.objects,
            "is_loaded": self.is_loaded,
            "load_time": self.load_time,
            "metadata": self.metadata
        }


@dataclass
class UnityObject:
    """Represents a Unity object"""
    object_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    prefab_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    components: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "name": self.name,
            "prefab_id": self.prefab_id,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "components": self.components,
            "parent_id": self.parent_id,
            "is_active": self.is_active,
            "metadata": self.metadata
        }


@dataclass
class UnityEvent:
    """Represents a Unity event"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: UnityEventType = UnityEventType.OBJECT_CREATED
    source_object_id: str = ""
    target_object_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_object_id": self.source_object_id,
            "target_object_id": self.target_object_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class RenderSettings:
    """Represents render settings"""
    settings_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    quality: RenderQuality = RenderQuality.MEDIUM
    resolution: Tuple[int, int] = (1920, 1080)
    target_fps: int = 60
    vsync_enabled: bool = True
    anti_aliasing: int = 4
    shadow_quality: str = "medium"
    texture_quality: str = "medium"
    post_processing: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "settings_id": self.settings_id,
            "quality": self.quality.value,
            "resolution": self.resolution,
            "target_fps": self.target_fps,
            "vsync_enabled": self.vsync_enabled,
            "anti_aliasing": self.anti_aliasing,
            "shadow_quality": self.shadow_quality,
            "texture_quality": self.texture_quality,
            "post_processing": self.post_processing
        }


class UnityService:
    """
    Unity Integration Service - Manages Unity engine connection
    Handles scene management, object manipulation, and rendering
    """
    
    def __init__(self):
        # Scene management
        self.scenes: Dict[str, UnityScene] = {}
        self.current_scene: Optional[UnityScene] = None
        
        # Object management
        self.objects: Dict[str, UnityObject] = {}
        
        # Event handling
        self.events: List[UnityEvent] = []
        self.event_handlers: Dict[UnityEventType, List[callable]] = {}
        
        # Render settings
        self.render_settings: RenderSettings = RenderSettings()
        
        # Connection status
        self.unity_connected: bool = False
        self.unity_version: str = "unknown"
        
        # Metrics
        self.scene_loads = Counter('unity_scene_loads_total', 'Total scene loads', ['status'])
        self.object_operations = Counter('unity_object_operations_total', 'Total object operations', ['operation'])
        self.events_processed = Counter('unity_events_processed_total', 'Total events processed', ['type'])
        self.render_time = Histogram('unity_render_seconds', 'Render time')
        self.fps = Gauge('unity_fps', 'Current FPS')
        self.active_objects = Gauge('unity_active_objects', 'Number of active objects')
        
        # Tracing
        self.setup_tracing()
        self.tracer = trace.get_tracer(__name__)
        
        # Logger
        self.logger = logging.getLogger("unity_service")
    
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
        """Initialize Unity service"""
        with self.tracer.start_as_current_span("initialize_unity") as span:
            try:
                # Setup event handlers
                self._setup_event_handlers()
                
                # Load default render settings
                self.render_settings = RenderSettings()
                
                self.logger.info("Unity service initialized successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize Unity service: {e}")
                span.record_exception(e)
                return False
    
    def _setup_event_handlers(self):
        """Setup event handlers for Unity events"""
        self.event_handlers = {
            UnityEventType.SCENE_LOADED: [],
            UnityEventType.OBJECT_CREATED: [],
            UnityEventType.OBJECT_DESTROYED: [],
            UnityEventType.COLLISION: [],
            UnityEventType.TRIGGER: [],
            UnityEventType.ANIMATION_EVENT: [],
            UnityEventType.PHYSICS_EVENT: [],
            UnityEventType.INPUT_EVENT: []
        }
    
    async def connect_to_unity(self, host: str = "localhost", port: int = 8080) -> bool:
        """Connect to Unity instance"""
        with self.tracer.start_as_current_span("connect_to_unity") as span:
            span.set_attribute("host", host)
            span.set_attribute("port", port)
            
            try:
                # Simulate Unity connection
                # In production, implement actual Unity WebSocket/HTTP connection
                
                await asyncio.sleep(0.5)  # Simulate connection time
                
                self.unity_connected = True
                self.unity_version = "2022.3.0f1"
                
                self.logger.info(f"Connected to Unity {self.unity_version}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to connect to Unity: {e}")
                span.record_exception(e)
                return False
    
    async def load_scene(self, scene_id: str) -> bool:
        """Load a Unity scene"""
        with self.tracer.start_as_current_span("load_scene") as span:
            import time
            start_time = time.time()
            
            span.set_attribute("scene_id", scene_id)
            
            if scene_id not in self.scenes:
                self.logger.error(f"Scene {scene_id} not found")
                self.scene_loads.labels(status="not_found").inc()
                return False
            
            scene = self.scenes[scene_id]
            
            try:
                # Simulate scene loading
                # In production, send load command to Unity
                
                await asyncio.sleep(1.0)  # Simulate load time
                
                scene.is_loaded = True
                scene.load_time = time.time() - start_time
                self.current_scene = scene
                
                # Unload previous scene
                if self.current_scene and self.current_scene.scene_id != scene_id:
                    self.current_scene.is_loaded = False
                
                # Generate scene loaded event
                event = UnityEvent(
                    event_type=UnityEventType.SCENE_LOADED,
                    source_object_id=scene_id,
                    data={"scene_name": scene.name}
                )
                await self._process_event(event)
                
                # Update metrics
                self.scene_loads.labels(status="success").inc()
                self.active_objects.set(len(self.objects))
                
                span.set_attribute("load_time", scene.load_time)
                
                self.logger.info(f"Loaded scene {scene.name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to load scene {scene_id}: {e}")
                scene.load_time = time.time() - start_time
                self.scene_loads.labels(status="error").inc()
                span.record_exception(e)
                return False
    
    async def create_object(self, object: UnityObject) -> str:
        """Create a Unity object"""
        with self.tracer.start_as_current_span("create_object") as span:
            span.set_attribute("object_id", object.object_id)
            span.set_attribute("object_name", object.name)
            
            try:
                # Add to object registry
                self.objects[object.object_id] = object
                
                # Generate object created event
                event = UnityEvent(
                    event_type=UnityEventType.OBJECT_CREATED,
                    source_object_id=object.object_id,
                    data={"object_name": object.name, "prefab_id": object.prefab_id}
                )
                await self._process_event(event)
                
                # Update metrics
                self.object_operations.labels(operation="create").inc()
                self.active_objects.set(len(self.objects))
                
                self.logger.info(f"Created object {object.name}")
                return object.object_id
                
            except Exception as e:
                self.logger.error(f"Failed to create object: {e}")
                span.record_exception(e)
                raise
    
    async def destroy_object(self, object_id: str) -> bool:
        """Destroy a Unity object"""
        with self.tracer.start_as_current_span("destroy_object") as span:
            span.set_attribute("object_id", object_id)
            
            if object_id not in self.objects:
                self.logger.error(f"Object {object_id} not found")
                return False
            
            try:
                object = self.objects[object_id]
                
                # Generate object destroyed event
                event = UnityEvent(
                    event_type=UnityEventType.OBJECT_DESTROYED,
                    source_object_id=object_id,
                    data={"object_name": object.name}
                )
                await self._process_event(event)
                
                # Remove from registry
                del self.objects[object_id]
                
                # Update metrics
                self.object_operations.labels(operation="destroy").inc()
                self.active_objects.set(len(self.objects))
                
                self.logger.info(f"Destroyed object {object.name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to destroy object {object_id}: {e}")
                span.record_exception(e)
                return False
    
    async def update_object_transform(self, object_id: str, position: Tuple[float, float, float] = None,
                                     rotation: Tuple[float, float, float, float] = None,
                                     scale: Tuple[float, float, float] = None) -> bool:
        """Update object transform"""
        if object_id not in self.objects:
            return False
        
        object = self.objects[object_id]
        
        if position:
            object.position = position
        if rotation:
            object.rotation = rotation
        if scale:
            object.scale = scale
        
        self.logger.info(f"Updated transform for object {object.name}")
        return True
    
    async def set_render_settings(self, settings: RenderSettings) -> bool:
        """Set render settings"""
        try:
            self.render_settings = settings
            
            # Apply settings to Unity (simulated)
            # In production, send settings to Unity
            
            self.logger.info(f"Updated render settings to {settings.quality.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set render settings: {e}")
            return False
    
    async def register_scene(self, scene: UnityScene) -> str:
        """Register a scene"""
        self.scenes[scene.scene_id] = scene
        
        self.logger.info(f"Registered scene {scene.name}")
        return scene.scene_id
    
    async def _process_event(self, event: UnityEvent):
        """Process a Unity event"""
        self.events.append(event)
        
        # Keep only recent events (last 1000)
        if len(self.events) > 1000:
            self.events = self.events[-1000]
        
        # Call event handlers
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                self.logger.error(f"Event handler error: {e}")
        
        # Update metrics
        self.events_processed.labels(type=event.event_type.value).inc()
    
    async def register_event_handler(self, event_type: UnityEventType, handler: callable):
        """Register an event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        
        self.logger.info(f"Registered handler for {event_type.value}")
    
    async def get_object_info(self, object_id: str) -> Optional[UnityObject]:
        """Get object information"""
        return self.objects.get(object_id)
    
    async def get_scene_info(self, scene_id: str) -> Optional[UnityScene]:
        """Get scene information"""
        return self.scenes.get(scene_id)
    
    async def get_recent_events(self, event_type: UnityEventType = None, limit: int = 10) -> List[UnityEvent]:
        """Get recent events"""
        if event_type:
            events = [e for e in self.events if e.event_type == event_type]
        else:
            events = self.events
        
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    async def update_performance_metrics(self, fps: float, render_time: float):
        """Update performance metrics"""
        self.fps.set(fps)
        self.render_time.observe(render_time)
        
        self.logger.info(f"Performance: {fps} FPS, {render_time:.3f}s render time")


# FastAPI application
app = FastAPI(title="Unity Integration Service")
unity_service: Optional[UnityService] = None


class SceneInput(BaseModel):
    """Input for scene registration"""
    name: str
    path: str
    objects: List[str] = []
    metadata: Dict[str, Any] = {}


class ObjectInput(BaseModel):
    """Input for object creation"""
    name: str
    prefab_id: str = ""
    position: List[float] = [0.0, 0.0, 0.0]
    rotation: List[float] = [0.0, 0.0, 0.0, 1.0]
    scale: List[float] = [1.0, 1.0, 1.0]
    components: List[str] = []
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class TransformInput(BaseModel):
    """Input for transform update"""
    position: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None


class RenderSettingsInput(BaseModel):
    """Input for render settings"""
    quality: str = "medium"
    resolution: List[int] = [1920, 1080]
    target_fps: int = 60
    vsync_enabled: bool = True
    anti_aliasing: int = 4
    shadow_quality: str = "medium"
    texture_quality: str = "medium"
    post_processing: bool = True


@app.on_event("startup")
async def startup_event():
    """Initialize Unity service on startup"""
    global unity_service
    unity_service = UnityService()
    await unity_service.initialize()
    
    # Start metrics server
    start_http_server(8009)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup Unity service on shutdown"""
    if unity_service:
        # Cleanup if needed
        pass


@app.get("/status")
async def get_status():
    """Get Unity service status"""
    return {
        "status": "running",
        "unity_connected": unity_service.unity_connected if unity_service else False,
        "unity_version": unity_service.unity_version if unity_service else "unknown",
        "current_scene": unity_service.current_scene.name if unity_service and unity_service.current_scene else None,
        "objects_count": len(unity_service.objects) if unity_service else 0,
        "scenes_count": len(unity_service.scenes) if unity_service else 0
    }


@app.post("/connect")
async def connect_to_unity_endpoint(host: str = "localhost", port: int = 8080):
    """Connect to Unity instance"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    success = await unity_service.connect_to_unity(host, port)
    
    return {"status": "connected" if success else "failed"}


@app.post("/scenes")
async def register_scene_endpoint(scene_input: SceneInput):
    """Register a scene"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    scene = UnityScene(
        name=scene_input.name,
        path=scene_input.path,
        objects=scene_input.objects,
        metadata=scene_input.metadata
    )
    
    scene_id = await unity_service.register_scene(scene)
    
    return {"scene_id": scene_id, "status": "registered"}


@app.post("/scenes/{scene_id}/load")
async def load_scene_endpoint(scene_id: str):
    """Load a scene"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    success = await unity_service.load_scene(scene_id)
    
    return {"status": "loaded" if success else "failed"}


@app.post("/objects")
async def create_object_endpoint(object_input: ObjectInput):
    """Create a Unity object"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    obj = UnityObject(
        name=object_input.name,
        prefab_id=object_input.prefab_id,
        position=tuple(object_input.position),
        rotation=tuple(object_input.rotation),
        scale=tuple(object_input.scale),
        components=object_input.components,
        parent_id=object_input.parent_id,
        metadata=object_input.metadata
    )
    
    object_id = await unity_service.create_object(obj)
    
    return {"object_id": object_id, "status": "created"}


@app.delete("/objects/{object_id}")
async def destroy_object_endpoint(object_id: str):
    """Destroy a Unity object"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    success = await unity_service.destroy_object(object_id)
    
    return {"status": "destroyed" if success else "failed"}


@app.put("/objects/{object_id}/transform")
async def update_transform_endpoint(object_id: str, transform_input: TransformInput):
    """Update object transform"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    position = tuple(transform_input.position) if transform_input.position else None
    rotation = tuple(transform_input.rotation) if transform_input.rotation else None
    scale = tuple(transform_input.scale) if transform_input.scale else None
    
    success = await unity_service.update_object_transform(object_id, position, rotation, scale)
    
    return {"status": "updated" if success else "failed"}


@app.get("/objects/{object_id}")
async def get_object_info_endpoint(object_id: str):
    """Get object information"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    obj = await unity_service.get_object_info(object_id)
    
    if obj:
        return obj.to_dict()
    else:
        raise HTTPException(status_code=404, detail="Object not found")


@app.put("/render_settings")
async def set_render_settings_endpoint(settings_input: RenderSettingsInput):
    """Set render settings"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    settings = RenderSettings(
        quality=RenderQuality(settings_input.quality),
        resolution=tuple(settings_input.resolution),
        target_fps=settings_input.target_fps,
        vsync_enabled=settings_input.vsync_enabled,
        anti_aliasing=settings_input.anti_aliasing,
        shadow_quality=settings_input.shadow_quality,
        texture_quality=settings_input.texture_quality,
        post_processing=settings_input.post_processing
    )
    
    success = await unity_service.set_render_settings(settings)
    
    return {"status": "updated" if success else "failed"}


@app.get("/events")
async def get_recent_events_endpoint(event_type: Optional[str] = None, limit: int = 10):
    """Get recent events"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    event_type_enum = UnityEventType(event_type) if event_type else None
    events = await unity_service.get_recent_events(event_type_enum, limit)
    
    return {"events": [event.to_dict() for event in events], "count": len(events)}


@app.post("/performance_metrics")
async def update_performance_metrics_endpoint(fps: float, render_time: float):
    """Update performance metrics"""
    if not unity_service:
        raise HTTPException(status_code=503, detail="Unity service not initialized")
    
    await unity_service.update_performance_metrics(fps, render_time)
    
    return {"status": "updated"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
