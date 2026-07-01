"""
Locust stress test file for AI Pipeline services
Tests system performance under load
"""
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import random
import base64


class CameraServiceUser(HttpUser):
    """Stress test for Camera Service"""
    wait_time = between(1, 3)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get camera service status"""
        self.client.get("/status")
    
    @task(1)
    def get_frame(self):
        """Get latest frame"""
        self.client.get("/frame")


class VisionServiceUser(HttpUser):
    """Stress test for Vision Service"""
    wait_time = between(2, 5)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get vision service status"""
        self.client.get("/status")
    
    @task(1)
    def detect_objects(self):
        """Detect objects in image"""
        dummy_image = base64.b64encode(b"dummy_image_data").decode()
        self.client.post(
            "/detect_objects",
            json={
                "image_data": dummy_image,
                "detection_types": ["object_detection"]
            }
        )


class WorldGraphServiceUser(HttpUser):
    """Stress test for World Graph Service"""
    wait_time = between(1, 3)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get world graph service status"""
        self.client.get("/status")
    
    @task(1)
    def create_entity(self):
        """Create new entity"""
        self.client.post(
            "/entities",
            json={
                "entity_type": "object",
                "name": f"test_object_{random.randint(1, 1000)}",
                "description": "Stress test object"
            }
        )


class ReasoningServiceUser(HttpUser):
    """Stress test for Reasoning Service"""
    wait_time = between(2, 4)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get reasoning service status"""
        self.client.get("/status")
    
    @task(1)
    def deductive_reasoning(self):
        """Perform deductive reasoning"""
        self.client.post(
            "/reason",
            json={
                "reasoning_type": "deductive",
                "premises": [
                    "All AI systems are complex",
                    "This is an AI system"
                ]
            }
        )


class LLMServiceUser(HttpUser):
    """Stress test for LLM Service"""
    wait_time = between(3, 6)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get LLM service status"""
        self.client.get("/status")
    
    @task(1)
    def generate_text(self):
        """Generate text"""
        prompts = [
            "Hello, how are you?",
            "Tell me a story",
            "What is the weather like?",
            "Explain AI to me"
        ]
        self.client.post(
            "/generate",
            json={
                "prompt": random.choice(prompts),
                "task_type": "text_generation",
                "parameters": {"max_length": 50}
            }
        )


class AnimationServiceUser(HttpUser):
    """Stress test for Animation Service"""
    wait_time = between(1, 3)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get animation service status"""
        self.client.get("/status")
    
    @task(1)
    def play_animation(self):
        """Play animation"""
        animations = ["idle", "walk", "wave", "custom"]
        self.client.post(
            "/play",
            json={
                "animation_type": random.choice(animations),
                "blend_mode": "mix"
            }
        )


class VoiceServiceUser(HttpUser):
    """Stress test for Voice Service"""
    wait_time = between(2, 5)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get voice service status"""
        self.client.get("/status")
    
    @task(1)
    def text_to_speech(self):
        """Convert text to speech"""
        texts = [
            "Hello, world!",
            "This is a test",
            "AI pipeline is working"
        ]
        self.client.post(
            "/tts",
            json={
                "text": random.choice(texts),
                "quality": "medium"
            }
        )


class AvatarServiceUser(HttpUser):
    """Stress test for Avatar Service"""
    wait_time = between(1, 3)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get avatar service status"""
        self.client.get("/status")
    
    @task(1)
    def create_configuration(self):
        """Create avatar configuration"""
        self.client.post(
            "/configurations",
            json={
                "name": f"test_avatar_{random.randint(1, 1000)}",
                "base_model_id": "model_001",
                "quality_level": "medium"
            }
        )


class UnityServiceUser(HttpUser):
    """Stress test for Unity Service"""
    wait_time = between(1, 3)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get unity service status"""
        self.client.get("/status")
    
    @task(1)
    def create_scene(self):
        """Create scene"""
        self.client.post(
            "/scenes",
            json={
                "name": f"test_scene_{random.randint(1, 1000)}",
                "path": "/scenes/test.unity"
            }
        )


class ARServiceUser(HttpUser):
    """Stress test for AR Service"""
    wait_time = between(1, 3)
    host = "http://localhost:8000"
    
    @task(3)
    def get_status(self):
        """Get AR service status"""
        self.client.get("/status")
    
    @task(1)
    def create_session(self):
        """Create AR session"""
        self.client.post(
            "/sessions",
            json={
                "platform": "arcore",
                "tracking_mode": "world"
            }
        )


# Event handlers for test results
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Handle test stop event"""
    if not isinstance(environment.runner, MasterRunner):
        print("\nStress test completed")
        print(f"Total requests: {environment.stats.total.num_requests}")
        print(f"Failures: {environment.stats.total.num_failures}")
        print(f"RPS: {environment.stats.total.current_rps}")
