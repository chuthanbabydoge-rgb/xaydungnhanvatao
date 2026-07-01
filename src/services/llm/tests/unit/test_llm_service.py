"""Unit tests for LLM Service"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.schemas import ChatRequest, ChatResponse, Message, ChatRole, ModelProvider
from app.services.openai_provider import OpenAIProvider
from app.services.anthropic_provider import AnthropicProvider
from app.services.model_router import ModelRouter, RoutingStrategy
from app.services.response_cache import ResponseCache
from app.services.llm_service import LLMService
from app.core.exceptions import ProviderError, RateLimitError


@pytest.fixture
def sample_chat_request():
    """Sample chat request"""
    return ChatRequest(
        model="gpt-4",
        messages=[
            Message(role=ChatRole.USER, content="Hello, how are you?")
        ],
        max_tokens=100,
        temperature=0.7
    )


@pytest.fixture
def openai_provider():
    """OpenAI provider fixture"""
    provider = OpenAIProvider(api_key="test-key")
    return provider


@pytest.fixture
def anthropic_provider():
    """Anthropic provider fixture"""
    provider = AnthropicProvider(api_key="test-key")
    return provider


@pytest.fixture
def model_router():
    """Model router fixture"""
    return ModelRouter()


@pytest.fixture
def response_cache():
    """Response cache fixture"""
    return ResponseCache()


@pytest.fixture
def llm_service():
    """LLM service fixture"""
    return LLMService()


class TestOpenAIProvider:
    """Tests for OpenAI provider"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, openai_provider):
        """Test provider initialization"""
        with patch.object(openai_provider, 'list_models', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []
            
            await openai_provider.initialize()
            
            assert openai_provider.is_initialized
            assert openai_provider.client is not None
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, openai_provider, sample_chat_request):
        """Test chat completion"""
        openai_provider._initialized = True
        
        with patch.object(openai_provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = Mock()
            mock_response.id = "test-id"
            mock_response.created = int(datetime.utcnow().timestamp())
            mock_response.model = "gpt-4"
            mock_response.choices = [
                Mock(
                    index=0,
                    message=Mock(
                        role="assistant",
                        content="Hello! I'm doing well, thank you.",
                        function_call=None
                    ),
                    finish_reason="stop"
                )
            ]
            mock_response.usage = Mock(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30
            )
            mock_create.return_value = mock_response
            
            response = await openai_provider.chat_completion(sample_chat_request, "test-request-id")
            
            assert response.model == "gpt-4"
            assert response.provider == ModelProvider.OPENAI
            assert len(response.choices) == 1
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream(self, openai_provider, sample_chat_request):
        """Test streaming chat completion"""
        openai_provider._initialized = True
        sample_chat_request.stream = True
        
        chunks = []
        
        async def mock_stream():
            for i in range(3):
                chunk = Mock()
                chunk.id = "test-id"
                chunk.created = int(datetime.utcnow().timestamp())
                chunk.model = "gpt-4"
                chunk.choices = [
                    Mock(
                        index=0,
                        delta=Mock(
                            role="assistant",
                            content=f"chunk {i}",
                            function_call=None
                        ),
                        finish_reason=None
                    )
                ]
                yield chunk
        
        with patch.object(openai_provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_stream()
            
            async for chunk in openai_provider.chat_completion_stream(sample_chat_request, "test-request-id"):
                chunks.append(chunk)
            
            assert len(chunks) == 3
    
    def test_calculate_cost(self, openai_provider):
        """Test cost calculation"""
        cost = openai_provider.calculate_cost(1000, 500, "gpt-4")
        
        # gpt-4: $0.03/1K input, $0.06/1K output
        expected = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
        assert abs(cost - expected) < 0.001
    
    def test_supports_function_calling(self, openai_provider):
        """Test function calling support"""
        assert openai_provider.supports_function_calling() is True
    
    def test_supports_streaming(self, openai_provider):
        """Test streaming support"""
        assert openai_provider.supports_streaming() is True
    
    def test_provider_type(self, openai_provider):
        """Test provider type"""
        assert openai_provider.provider_type == ModelProvider.OPENAI


class TestAnthropicProvider:
    """Tests for Anthropic provider"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, anthropic_provider):
        """Test provider initialization"""
        with patch.object(anthropic_provider, 'list_models', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []
            
            await anthropic_provider.initialize()
            
            assert anthropic_provider.is_initialized
            assert anthropic_provider.client is not None
    
    def test_calculate_cost(self, anthropic_provider):
        """Test cost calculation"""
        cost = anthropic_provider.calculate_cost(1000, 500, "claude-3-sonnet-20240229")
        
        # claude-3-sonnet: $0.003/1K input, $0.015/1K output
        expected = (1000 / 1000) * 0.003 + (500 / 1000) * 0.015
        assert abs(cost - expected) < 0.001
    
    def test_provider_type(self, anthropic_provider):
        """Test provider type"""
        assert anthropic_provider.provider_type == ModelProvider.ANTHROPIC


class TestModelRouter:
    """Tests for model router"""
    
    def test_register_provider(self, model_router, openai_provider):
        """Test provider registration"""
        model_router.register_provider(openai_provider)
        
        assert ModelProvider.OPENAI in model_router.providers
    
    def test_set_routing_strategy(self, model_router):
        """Test setting routing strategy"""
        model_router.set_routing_strategy(RoutingStrategy.QUALITY_OPTIMIZED)
        
        assert model_router.routing_strategy == RoutingStrategy.QUALITY_OPTIMIZED
    
    @pytest.mark.asyncio
    async def test_select_model_cost_optimized(self, model_router, sample_chat_request):
        """Test model selection with cost optimization"""
        model_router.set_routing_strategy(RoutingStrategy.COST_OPTIMIZED)
        
        # Mock available models
        mock_models = [
            {
                "id": "gpt-3.5-turbo",
                "provider": "openai",
                "input_cost_per_1k": 0.0015,
                "output_cost_per_1k": 0.002,
                "quality_score": 0.7,
                "priority": 5,
                "max_context_length": 4096,
                "supports_function_calling": True,
                "supports_streaming": True
            },
            {
                "id": "gpt-4",
                "provider": "openai",
                "input_cost_per_1k": 0.03,
                "output_cost_per_1k": 0.06,
                "quality_score": 0.9,
                "priority": 10,
                "max_context_length": 8192,
                "supports_function_calling": True,
                "supports_streaming": True
            }
        ]
        
        with patch.object(model_router, '_get_available_models', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_models
            
            with patch.object(model_router, '_get_provider_for_model') as mock_provider:
                mock_provider.return_value = openai_provider
                
                provider, model = await model_router.select_model(sample_chat_request)
                
                # Should select cheaper model
                assert model == "gpt-3.5-turbo"


class TestResponseCache:
    """Tests for response cache"""
    
    @pytest.mark.asyncio
    async def test_is_cacheable(self, response_cache, sample_chat_request):
        """Test cacheability check"""
        response_cache.cache_enabled_models = {"gpt-3.5-turbo"}
        
        # Cacheable request
        sample_chat_request.model = "gpt-3.5-turbo"
        sample_chat_request.enable_cache = True
        sample_chat_request.stream = False
        sample_chat_request.functions = None
        
        assert response_cache.is_cacheable(sample_chat_request) is True
        
        # Not cacheable - streaming
        sample_chat_request.stream = True
        assert response_cache.is_cacheable(sample_chat_request) is False
    
    def test_generate_cache_key(self, response_cache, sample_chat_request):
        """Test cache key generation"""
        key1 = response_cache.generate_cache_key(sample_chat_request)
        key2 = response_cache.generate_cache_key(sample_chat_request)
        
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hash length
    
    @pytest.mark.asyncio
    async def test_cache_get_set(self, response_cache, sample_chat_request):
        """Test cache get and set"""
        mock_response = ChatResponse(
            id="test-id",
            created=int(datetime.utcnow().timestamp()),
            model="gpt-3.5-turbo",
            choices=[{
                "index": 0,
                "message": {"role": "assistant", "content": "Test response"},
                "finish_reason": "stop"
            }],
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            processing_time_ms=100.0,
            cost=0.001,
            provider=ModelProvider.OPENAI,
            request_id="test-request-id"
        )
        
        with patch('app.services.response_cache.redis_manager') as mock_redis:
            mock_redis.get.return_value = None
            mock_redis.set.return_value = True
            
            # Set cache
            result = await response_cache.set(sample_chat_request, mock_response)
            assert result is True
            
            # Get cache (miss)
            cached = await response_cache.get(sample_chat_request)
            assert cached is None
            
            # Get cache (hit)
            mock_redis.get.return_value = mock_response.dict()
            cached = await response_cache.get(sample_chat_request)
            assert cached is not None


class TestLLMService:
    """Tests for LLM service"""
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, llm_service, sample_chat_request):
        """Test chat completion"""
        with patch.object(llm_service.router, 'select_model', new_callable=AsyncMock) as mock_select:
            mock_provider = Mock()
            mock_provider.chat_completion = AsyncMock()
            mock_response = ChatResponse(
                id="test-id",
                created=int(datetime.utcnow().timestamp()),
                model="gpt-4",
                choices=[{
                    "index": 0,
                    "message": {"role": "assistant", "content": "Test response"},
                    "finish_reason": "stop"
                }],
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                processing_time_ms=100.0,
                cost=0.001,
                provider=ModelProvider.OPENAI,
                request_id="test-request-id"
            )
            mock_provider.chat_completion.return_value = mock_response
            
            mock_select.return_value = (mock_provider, "gpt-4")
            
            with patch.object(llm_service.cache, 'get', new_callable=AsyncMock) as mock_cache_get:
                mock_cache_get.return_value = None
                
                with patch.object(llm_service.cache, 'set', new_callable=AsyncMock) as mock_cache_set:
                    mock_cache_set.return_value = True
                    
                    response = await llm_service.chat_completion(sample_chat_request)
                    
                    assert response.model == "gpt-4"
                    assert mock_provider.chat_completion.called
    
    @pytest.mark.asyncio
    async def test_rate_limit_check(self, llm_service):
        """Test rate limit checking"""
        with patch('app.services.llm_service.redis_manager') as mock_redis:
            mock_redis.get.return_value = None
            
            result = await llm_service._check_rate_limit("test-user")
            assert result is False
            
            # Exceed limit
            mock_redis.get.return_value = 100
            result = await llm_service._check_rate_limit("test-user")
            assert result is True
