"""
Unit tests for Memory Service
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.memory.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client"""
    with patch('services.memory_service.main.get_qdrant') as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver"""
    with patch('services.memory_service.main.get_neo4j') as mock:
        driver = AsyncMock()
        mock.return_value = driver
        yield driver


class TestMemoryService:
    """Test Memory Service endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "memory-service"
    
    @pytest.mark.asyncio
    async def test_store_memory(self, client, mock_qdrant_client, mock_neo4j_driver):
        """Test storing a memory"""
        request_data = {
            "user_id": "test_user",
            "content": "Test memory content",
            "embedding": [0.1] * 1536,
            "metadata": {"source": "test"},
            "memory_type": "episodic"
        }
        
        # Mock Qdrant operations
        mock_qdrant_client.upsert = AsyncMock()
        
        # Mock Neo4j operations
        mock_neo4j_driver.session = AsyncMock()
        mock_session = AsyncMock()
        mock_neo4j_driver.session.return_value.__aenter__.return_value = mock_session
        mock_session.run = AsyncMock()
        mock_session.run.return_value.__aenter__.return_value = AsyncMock()
        
        response = client.post("/api/v1/memory/store", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "memory_id" in data
        assert data["status"] == "stored"
    
    @pytest.mark.asyncio
    async def test_search_memory(self, client, mock_qdrant_client):
        """Test searching memories"""
        request_data = {
            "user_id": "test_user",
            "query_embedding": [0.1] * 1536,
            "limit": 10,
            "score_threshold": 0.7
        }
        
        # Mock Qdrant search
        mock_qdrant_client.search = AsyncMock(return_value=[
            {
                "id": "test_id",
                "score": 0.8,
                "payload": {
                    "user_id": "test_user",
                    "content": "Test content"
                }
            }
        ])
        
        response = client.post("/api/v1/memory/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["user_id"] == "test_user"
    
    @pytest.mark.asyncio
    async def test_create_entity(self, client, mock_neo4j_driver):
        """Test creating a knowledge graph entity"""
        request_data = {
            "entity_id": "test_entity",
            "entity_type": "person",
            "name": "Test Person",
            "properties": {"age": 30}
        }
        
        # Mock Neo4j operations
        mock_neo4j_driver.session = AsyncMock()
        mock_session = AsyncMock()
        mock_neo4j_driver.session.return_value.__aenter__.return_value = mock_session
        mock_session.run = AsyncMock()
        
        # First call: check if exists
        mock_session.run.return_value.__aenter__.return_value = AsyncMock(data=[])
        
        response = client.post("/api/v1/graph/entity", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["entity_id"] == "test_entity"
        assert data["status"] == "created"
    
    @pytest.mark.asyncio
    async def test_create_relationship(self, client, mock_neo4j_driver):
        """Test creating a knowledge graph relationship"""
        request_data = {
            "from_entity_id": "entity1",
            "to_entity_id": "entity2",
            "relationship_type": "KNOWS",
            "properties": {"since": "2020"}
        }
        
        # Mock Neo4j operations
        mock_neo4j_driver.session = AsyncMock()
        mock_session = AsyncMock()
        mock_neo4j_driver.session.return_value.__aenter__.return_value = mock_session
        mock_session.run = AsyncMock()
        
        response = client.post("/api/v1/graph/relationship", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "created"
        assert data["relationship_type"] == "KNOWS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
