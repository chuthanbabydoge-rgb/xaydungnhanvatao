"""
Camera Service - Real-time camera input capture and processing
Handles camera devices, frame extraction, and streaming for the AI pipeline
"""
import asyncio
import logging
import cv2
import numpy as np
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import threading
import queue
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import uvicorn
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from prometheus_client import Counter, Histogram, Gauge, start_http_server


class CameraStatus(Enum):
    """Camera status states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class Resolution(Enum):
    """Camera resolution presets"""
    HD_720 = (1280, 720)
    FHD_1080 = (1920, 1080)
    UHD_4K = (3840, 2160)
    VGA = (640, 480)
    CUSTOM = (0, 0)


@dataclass
class CameraConfig:
    """Camera configuration"""
    camera_id: int = 0
    resolution: Resolution = Resolution.HD_720
    fps: int = 30
    buffer_size: int = 10
    enable_hardware_acceleration: bool = True
    enable_auto_focus: bool = True
    enable_auto_exposure: bool = True
    width: int = 1280
    height: int = 720
    custom_resolution: tuple = (1280, 720)
    
    def __post_init__(self):
        if self.resolution != Resolution.CUSTOM:
            self.width, self.height = self.resolution.value
        else:
            self.width, self.height = self.custom_resolution


@dataclass
class Frame:
    """Represents a camera frame"""
    frame_id: str
    timestamp: datetime
    data: np.ndarray
    width: int
    height: int
    channels: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "width": self.width,
            "height": self.height,
            "channels": self.channels,
            "metadata": self.metadata
        }


class CameraService:
    """
    Camera Service - Handles camera capture and frame streaming
    Provides real-time camera input for the AI pipeline
    """
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.status = CameraStatus.INITIALIZING
        self.camera: Optional[cv2.VideoCapture] = None
        self.frame_queue: queue.Queue = queue.Queue(maxsize=config.buffer_size)
        self.capture_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.frame_count = 0
        self.error_count = 0
        
        # Metrics
        self.frames_captured = Counter('camera_frames_captured_total', 'Total frames captured')
        self.capture_errors = Counter('camera_capture_errors_total', 'Total capture errors')
        self.frame_rate = Gauge('camera_frame_rate', 'Current frame rate')
        self.queue_size = Gauge('camera_queue_size', 'Current frame queue size')
        
        # Tracing
        self.setup_tracing()
        self.tracer = trace.get_tracer(__name__)
        
        # Logger
        self.logger = logging.getLogger("camera_service")
        
        # Callbacks
        self.frame_callbacks: list[Callable] = []
    
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
        """Initialize camera device"""
        with self.tracer.start_as_current_span("initialize_camera") as span:
            span.set_attribute("camera_id", self.config.camera_id)
            span.set_attribute("resolution", f"{self.config.width}x{self.config.height}")
            
            try:
                self.camera = cv2.VideoCapture(self.config.camera_id)
                
                if not self.camera.isOpened():
                    raise Exception(f"Failed to open camera {self.config.camera_id}")
                
                # Set camera properties
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
                self.camera.set(cv2.CAP_PROP_FPS, self.config.fps)
                
                if self.config.enable_auto_focus:
                    self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                
                if self.config.enable_auto_exposure:
                    self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
                
                self.status = CameraStatus.ACTIVE
                self.logger.info(f"Camera {self.config.camera_id} initialized successfully")
                
                return True
                
            except Exception as e:
                self.status = CameraStatus.ERROR
                self.logger.error(f"Failed to initialize camera: {e}")
                span.record_exception(e)
                return False
    
    async def start_capture(self):
        """Start frame capture thread"""
        if self.status != CameraStatus.ACTIVE:
            await self.initialize()
        
        self.stop_event.clear()
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.logger.info("Frame capture started")
    
    def _capture_loop(self):
        """Frame capture loop (runs in separate thread)"""
        import time
        last_time = time.time()
        frame_times = []
        
        while not self.stop_event.is_set():
            try:
                ret, frame = self.camera.read()
                
                if not ret:
                    self.error_count += 1
                    self.capture_errors.inc()
                    self.logger.warning("Failed to capture frame")
                    continue
                
                # Generate frame ID
                frame_id = f"frame_{self.frame_count}_{datetime.utcnow().timestamp()}"
                
                # Create frame object
                camera_frame = Frame(
                    frame_id=frame_id,
                    timestamp=datetime.utcnow(),
                    data=frame,
                    width=frame.shape[1],
                    height=frame.shape[0],
                    channels=frame.shape[2] if len(frame.shape) > 2 else 1,
                    metadata={
                        "camera_id": self.config.camera_id,
                        "frame_number": self.frame_count,
                        "exposure_time": self.camera.get(cv2.CAP_PROP_EXPOSURE),
                        "gain": self.camera.get(cv2.CAP_PROP_GAIN)
                    }
                )
                
                # Add to queue (non-blocking)
                try:
                    self.frame_queue.put(camera_frame, block=False)
                except queue.Full:
                    # Drop oldest frame if queue is full
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(camera_frame, block=False)
                    except queue.Empty:
                        pass
                
                # Update metrics
                self.frame_count += 1
                self.frames_captured.inc()
                self.queue_size.set(self.frame_queue.qsize())
                
                # Calculate frame rate
                current_time = time.time()
                frame_times.append(current_time)
                if len(frame_times) > 30:
                    frame_times.pop(0)
                
                if len(frame_times) > 1:
                    fps = len(frame_times) / (frame_times[-1] - frame_times[0])
                    self.frame_rate.set(fps)
                
                # Call frame callbacks
                for callback in self.frame_callbacks:
                    try:
                        callback(camera_frame)
                    except Exception as e:
                        self.logger.error(f"Frame callback error: {e}")
                
                # Control frame rate
                elapsed = time.time() - last_time
                target_interval = 1.0 / self.config.fps
                if elapsed < target_interval:
                    time.sleep(target_interval - elapsed)
                
                last_time = time.time()
                
            except Exception as e:
                self.error_count += 1
                self.capture_errors.inc()
                self.logger.error(f"Capture loop error: {e}")
    
    async def get_frame(self, timeout: float = 1.0) -> Optional[Frame]:
        """Get the latest frame from the queue"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    async def get_frame_bytes(self, format: str = "jpg", quality: int = 90) -> Optional[bytes]:
        """Get frame as bytes for streaming"""
        frame = await self.get_frame()
        if frame is None:
            return None
        
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality] if format == "jpg" else []
        _, buffer = cv2.imencode(f".{format}", frame.data, encode_param)
        
        return buffer.tobytes()
    
    def add_frame_callback(self, callback: Callable):
        """Add a callback to be called for each frame"""
        self.frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable):
        """Remove a frame callback"""
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
    
    async def pause(self):
        """Pause frame capture"""
        self.status = CameraStatus.PAUSED
        self.logger.info("Camera capture paused")
    
    async def resume(self):
        """Resume frame capture"""
        if self.status == CameraStatus.PAUSED:
            self.status = CameraStatus.ACTIVE
            self.logger.info("Camera capture resumed")
    
    async def stop(self):
        """Stop camera capture"""
        self.stop_event.set()
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        
        if self.camera:
            self.camera.release()
        
        self.status = CameraStatus.STOPPED
        self.logger.info("Camera capture stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get camera status"""
        return {
            "status": self.status.value,
            "camera_id": self.config.camera_id,
            "resolution": f"{self.config.width}x{self.config.height}",
            "fps": self.config.fps,
            "frames_captured": self.frame_count,
            "errors": self.error_count,
            "queue_size": self.frame_queue.qsize(),
            "uptime": datetime.utcnow().isoformat()
        }


# FastAPI application
app = FastAPI(title="Camera Service")
camera_service: Optional[CameraService] = None


@app.on_event("startup")
async def startup_event():
    """Initialize camera service on startup"""
    global camera_service
    config = CameraConfig(
        camera_id=0,
        resolution=Resolution.HD_720,
        fps=30
    )
    camera_service = CameraService(config)
    await camera_service.initialize()
    await camera_service.start_capture()
    
    # Start metrics server
    start_http_server(8001)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup camera service on shutdown"""
    if camera_service:
        await camera_service.stop()


@app.get("/status")
async def get_status():
    """Get camera service status"""
    if camera_service:
        return camera_service.get_status()
    return {"status": "not_initialized"}


@app.get("/frame")
async def get_frame():
    """Get latest frame as JSON"""
    if camera_service:
        frame = await camera_service.get_frame()
        if frame:
            return frame.to_dict()
    return {"error": "No frame available"}


@app.get("/stream")
async def stream_frames():
    """Stream frames as MJPEG"""
    if not camera_service:
        return {"error": "Camera not initialized"}
    
    async def generate_frames():
        while True:
            frame_bytes = await camera_service.get_frame_bytes(format="jpg", quality=85)
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                break
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time frame streaming"""
    await websocket.accept()
    
    if not camera_service:
        await websocket.close(code=1000, reason="Camera not initialized")
        return
    
    try:
        while True:
            frame = await camera_service.get_frame(timeout=1.0)
            if frame:
                # Convert frame to base64 for WebSocket transmission
                import base64
                frame_bytes = await camera_service.get_frame_bytes(format="jpg", quality=85)
                if frame_bytes:
                    frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')
                    
                    await websocket.send_json({
                        "frame_id": frame.frame_id,
                        "timestamp": frame.timestamp.isoformat(),
                        "data": frame_base64,
                        "metadata": frame.metadata
                    })
    except WebSocketDisconnect:
        camera_service.logger.info("WebSocket disconnected")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
