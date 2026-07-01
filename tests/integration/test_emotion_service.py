"""
Unit tests for Emotion Service
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.emotion.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


class TestEmotionService:
    """Test Emotion Service endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "emotion-service"
    
    def test_detect_emotion_from_text(self, client):
        """Test emotion detection from text"""
        request_data = {
            "user_id": "test_user",
            "text": "I am so happy and excited today!"
        }
        
        response = client.post("/api/v1/emotion/detect", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "emotion" in data
        assert "confidence" in data
        assert "all_emotions" in data
        assert "intensity" in data
    
    def test_get_emotion_state(self, client):
        """Test getting emotion state"""
        response = client.get("/api/v1/emotion/state/test_user")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "current_emotion" in data
        assert "emotion_intensity" in data
    
    def test_update_emotion_state(self, client):
        """Test updating emotion state"""
        request_data = {
            "user_id": "test_user",
            "emotion": "happy",
            "intensity": 0.8,
            "reason": "User expressed happiness"
        }
        
        response = client.put("/api/v1/emotion/state", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user"
        assert data["status"] == "updated"
    
    def test_generate_emotion_expression(self, client):
        """Test generating emotion expression"""
        response = client.post("/api/v1/emotion/express?emotion=happy&intensity=0.7")
        
        assert response.status_code == 200
        data = response.json()
        assert "emotion" in data
        assert "intensity" in data
        assert "facial_expression" in data
        assert "body_language" in data
        assert "voice_tone" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
