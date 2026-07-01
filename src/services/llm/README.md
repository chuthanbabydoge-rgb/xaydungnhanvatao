# LLM Service

Multi-LLM support service with intelligent routing, caching, and rate limiting for the AI Companion Platform.

## Features

- **Multi-LLM Support**: OpenAI, Anthropic, Google, DeepSeek, and local models
- **Intelligent Routing**: Cost-optimized, quality-optimized, or balanced model selection
- **Response Caching**: Redis-based caching for faster responses and cost savings
- **Rate Limiting**: Per-user rate limiting for requests and tokens
- **Streaming**: Support for streaming responses
- **Function Calling**: Tool calling support for agents
- **Context Management**: Long context support with compression
- **Monitoring**: OpenTelemetry tracing and Prometheus metrics

## Architecture

```
LLM Service
├── Providers
│   ├── OpenAI Provider
│   ├── Anthropic Provider
│   ├── Google Provider (planned)
│   ├── DeepSeek Provider (planned)
│   └── Local LLM Provider (planned)
├── Model Router
│   ├── Cost Optimization
│   ├── Quality Optimization
│   └── Speed Optimization
├── Response Cache
│   ├── Redis Backend
│   └── Cache Invalidation
├── Rate Limiter
│   ├── Request Rate Limiting
│   └── Token Rate Limiting
└── Usage Tracker
    ├── Per-User Statistics
    └── Cost Tracking
```

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- OpenAI API Key or Anthropic API Key

### Installation

```bash
# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### Configuration

```bash
# .env file
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/llm_db
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_ORG_ID=your-org-id

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key

# Model Selection
DEFAULT_MODEL=gpt-4-turbo-preview
ENABLE_MODEL_ROUTING=true
ROUTING_STRATEGY=cost_optimized

# Caching
ENABLE_RESPONSE_CACHE=true
CACHE_TTL=3600
CACHE_ENABLED_MODELS=["gpt-3.5-turbo", "claude-3-haiku"]

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_TOKENS_PER_MINUTE=90000
```

### Running

```bash
# Development
poetry run python main.py

# Production
poetry run uvicorn main:app --host 0.0.0.0 --port 8002 --workers 4
```

### Docker

```bash
# Build
docker build -t llm-service:latest .

# Run
docker run -p 8002:8002 \
  -e DATABASE_URL=postgresql+asyncpg://user:password@db:5432/llm_db \
  -e REDIS_URL=redis://redis:6379/0 \
  -e OPENAI_API_KEY=your-api-key \
  llm-service:latest
```

## API Endpoints

### Chat Completion

```bash
POST /api/v1/llm/chat
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "max_tokens": 100,
  "temperature": 0.7,
  "enable_routing": true,
  "enable_cache": true
}
```

### Streaming Chat Completion

```bash
POST /api/v1/llm/chat/stream
Content-Type: application/json
Accept: text/event-stream

{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "stream": true
}
```

### List Models

```bash
GET /api/v1/llm/models
```

### Get Model Info

```bash
GET /api/v1/llm/models/{model_name}
```

### Usage Statistics

```bash
GET /api/v1/llm/usage?period=daily
Authorization: Bearer {token}
```

### Cache Management

```bash
# Get cache stats
GET /api/v1/llm/cache/stats

# Clear all cache
DELETE /api/v1/llm/cache

# Clear cache for specific model
DELETE /api/v1/llm/cache?model_name=gpt-3.5-turbo
```

### Health Check

```bash
GET /api/v1/llm/health
```

## Testing

```bash
# Unit tests
poetry run pytest tests/unit/ -v

# Integration tests
poetry run pytest tests/integration/ -v

# With coverage
poetry run pytest --cov=app tests/
```

## Model Routing Strategies

### Cost Optimized
Selects the cheapest model that meets requirements.

### Quality Optimized
Selects the highest quality model regardless of cost.

### Speed Optimized
Selects the fastest model (based on priority).

### Balanced
Balances cost and quality using a scoring algorithm.

## Caching Strategy

- Only caches requests without function calling
- Only caches specific models (configurable)
- Cache TTL: 1 hour (configurable)
- Cache key based on deterministic hash of request parameters
- Hit tracking and automatic expiration

## Rate Limiting

- Request rate limit: 60 requests/minute per user
- Token rate limit: 90,000 tokens/minute per user
- Configurable per user tier
- Redis-based counters with automatic expiration

## Monitoring

### Metrics

- Request count by model
- Token usage by model
- Cost tracking
- Response time (p50, p95, p99)
- Cache hit rate
- Error rate

### Tracing

- OpenTelemetry integration
- Distributed tracing with Jaeger
- Request-level tracing

### Logging

- Structured logging with structlog
- Request/response logging
- Error logging with stack traces

## Development

### Code Style

```bash
# Format code
poetry run black app/

# Lint code
poetry run ruff check app/

# Type check
poetry run mypy app/
```

### Adding a New Provider

1. Create a new provider class inheriting from `BaseLLMProvider`
2. Implement all required methods
3. Add pricing and capabilities
4. Register in `main.py` lifespan
5. Add tests

Example:

```python
from app.services.base_provider import BaseLLMProvider

class CustomProvider(BaseLLMProvider):
    async def initialize(self):
        # Initialize provider
        pass
    
    async def chat_completion(self, request, request_id):
        # Implement chat completion
        pass
    
    # Implement other required methods...
```

## Troubleshooting

### Provider Connection Issues

Check API keys and network connectivity:

```bash
curl -X GET https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Cache Not Working

Check Redis connection:

```bash
redis-cli ping
```

### Rate Limiting Too Aggressive

Adjust rate limits in `.env`:

```bash
RATE_LIMIT_REQUESTS_PER_MINUTE=120
RATE_LIMIT_TOKENS_PER_MINUTE=180000
```

## License

Proprietary - All rights reserved
