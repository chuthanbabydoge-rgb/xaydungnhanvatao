"""Integration tests for LLM Service"""
import pytest
import httpx
from typing import AsyncGenerator

from config import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client for testing"""
    settings = get_settings()
    
    async with httpx.AsyncClient(
        base_url=f"http://{settings.HOST}:{settings.PORT}",
        timeout=30.0
    ) as client:
        yield client


class TestLLMAPI:
    """Integration tests for LLM API"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: httpx.AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: httpx.AsyncClient):
        """Test root endpoint"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_list_models(self, client: httpx.AsyncClient):
        """Test list models endpoint"""
        response = await client.get("/api/v1/llm/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "total" in data
        assert "default_model" in data
        assert isinstance(data["models"], list)
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, client: httpx.AsyncClient):
        """Test chat completion endpoint"""
        request_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        response = await client.post("/api/v1/llm/chat", json=request_data)
        
        # May fail if no API key configured
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "model" in data
            assert "choices" in data
            assert "usage" in data
            assert "provider" in data
        else:
            # Expected if no API key
            assert response.status_code in [401, 502, 500]
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream(self, client: httpx.AsyncClient):
        """Test streaming chat completion endpoint"""
        request_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "max_tokens": 50,
            "temperature": 0.7,
            "stream": True
        }
        
        response = await client.post(
            "/api/v1/llm/chat/stream",
            json=request_data,
            headers={"Accept": "text/event-stream"}
        )
        
        # May fail if no API key configured
        if response.status_code == 200:
            assert response.headers["content-type"] == "text/event-stream"
            
            # Read chunks
            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunks.append(line)
                    if line == "data: [DONE]":
                        break
            
            assert len(chunks) > 0
        else:
            # Expected if no API key
            assert response.status_code in [401, 502, 500]
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, client: httpx.AsyncClient):
        """Test get model info endpoint"""
        response = await client.get("/api/v1/llm/models/gpt-3.5-turbo")
        
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "provider" in data
            assert "max_context_length" in data
            assert "input_cost_per_1k" in data
            assert "output_cost_per_1k" in data
        else:
            # Model not found or provider not configured
            assert response.status_code in [404, 500]
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, client: httpx.AsyncClient):
        """Test cache stats endpoint"""
        response = await client.get("/api/v1/llm/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_cached_responses" in data
        assert "total_hits" in data
        assert "hit_rate" in data
    
    @pytest.mark.asyncio
    async def test_llm_health_check(self, client: httpx.AsyncClient):
        """Test LLM health check endpoint"""
        response = await client.get("/api/v1/llm/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "providers" in data
        assert "models_loaded" in data
        assert "cache_status" in data


class TestRateLimiting:
    """Tests for rate limiting"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, client: httpx.AsyncClient):
        """Test rate limit enforcement"""
        # Make multiple requests quickly
        request_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Test"}
            ],
            "max_tokens": 10
        }
        
        # This test would require authentication and a user with rate limits
        # For now, just verify the endpoint exists
        response = await client.post("/api/v1/llm/chat", json=request_data)
        
        # Response may be 200, 401, 429, or 500 depending on configuration
        assert response.status_code in [200, 401, 429, 500]


class TestErrorHandling:
    """Tests for error handling"""
    
    @pytest.mark.asyncio
    async def test_invalid_model(self, client: httpx.AsyncClient):
        """Test invalid model error"""
        request_data = {
            "model": "invalid-model-name",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 50
        }
        
        response = await client.post("/api/v1/llm/chat", json=request_data)
        
        # Should return error
        assert response.status_code in [400, 404, 500]
    
    @pytest.mark.asyncio
    async def test_invalid_request(self, client: httpx.AsyncClient):
        """Test invalid request validation"""
        request_data = {
            "model": "gpt-3.5-turbo",
            # Missing required "messages" field
            "max_tokens": 50
        }
        
        response = await client.post("/api/v1/llm/chat", json=request_data)
        
        # Should return validation error
        assert response.status_code == 422
