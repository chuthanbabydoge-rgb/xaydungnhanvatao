"""
Unit tests for LLM Service
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.llm_service.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


class TestLLMService:
    """Test LLM Service endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "llm-service"
    
    def test_list_models(self, client):
        """Test listing available models"""
        response = client.get("/api/v1/llm/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "count" in data
        assert len(data["models"]) > 0
    
    def test_route_llm(self, client):
        """Test LLM routing"""
        request_data = {
            "prompt": "Test prompt",
            "system_prompt": "You are a helpful assistant",
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        response = client.post("/api/v1/llm/route", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "model" in data
        assert "reasoning" in data
        assert "estimated_cost" in data
        assert "estimated_latency" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
