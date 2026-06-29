# AI Companion Platform - Backend

## Overview

This is the backend implementation for the AI Companion Platform, consisting of 22 microservices built with Python 3.12 and FastAPI.

## Architecture

The backend follows a microservices architecture with the following components:

### Core AI Services
- **LLM Service** (Port 8001): Multi-provider LLM integration with intelligent routing
- **Memory Service** (Port 8002): Vector memory and knowledge graph management
- **Conversation Service** (Port 8003): Conversation orchestration and management
- **Emotion Service** (Port 8004): Emotion detection and expression
- **Motivation Service** (Port 8005): Need detection and goal generation
- **Reflection Service** (Port 8006): Self-reflection and learning
- **Learning Service** (Port 8007): Preference and pattern learning
- **Plugin Service** (Port 8008): Plugin system and SDK
- **Scheduler Service** (Port 8009): AI-powered task scheduling
- **Vision Memory Service** (Port 8010): Visual memory and scene understanding

### User Management Services
- **Auth Service** (Port 8011): Authentication and authorization
- **User Service** (Port 8012): User profile and preferences

### 3D & Physics Services
- **Asset Service** (Port 8013): 3D asset management
- **World Service** (Port 8014): World graph and environment
- **Physics Service** (Port 8015): Physics simulation
- **Character Service** (Port 8016): Character state management
- **Animation Service** (Port 8017): Animation data management

### Vision & Speech Services
- **Vision Service** (Port 8018): Computer vision processing
- **STT Service** (Port 8019): Speech-to-text
- **TTS Service** (Port 8020): Text-to-speech

### Advanced AI Services
- **Social Service** (Port 8021): Social relationship management
- **Multi-Agent Service** (Port 8022): Multi-agent coordination

## Infrastructure

- **PostgreSQL** (Port 5432): Relational database
- **Redis** (Port 6379): Cache and message broker
- **MongoDB** (Port 27017): Document store
- **Qdrant** (Port 6333): Vector database
- **Neo4j** (Port 7474/7687): Knowledge graph
- **RabbitMQ** (Port 5672/15672): Message queue
- **Nginx** (Port 80/443): API Gateway

## Prerequisites

- Docker 24+
- Docker Compose
- Python 3.12 (for local development)
- Git

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd AI_Companion_Design/backend
```

2. Start all services:
```bash
docker-compose up -d
```

3. Check service status:
```bash
docker-compose ps
```

4. View logs:
```bash
docker-compose logs -f
```

5. Stop services:
```bash
docker-compose down
```

### Local Development

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start infrastructure services:
```bash
docker-compose up -d postgres redis mongodb qdrant neo4j rabbitmq
```

5. Run individual services:
```bash
# Example: Run LLM service
cd services/llm_service
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## API Documentation

Once services are running, access API documentation at:
- Swagger UI: http://localhost:8001/docs (for LLM service)
- ReDoc: http://localhost:8001/redoc

Replace port number for other services.

## Configuration

### Environment Variables

Each service uses the following environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `MONGODB_URL`: MongoDB connection string
- `QDRANT_URL`: Qdrant connection URL
- `NEO4J_URL`: Neo4j connection URL
- `RABBITMQ_URL`: RabbitMQ connection URL

See `config/settings.py` for detailed configuration options.

## Testing

### Run all tests:
```bash
pytest backend/tests/
```

### Run specific service tests:
```bash
pytest backend/services/llm_service/tests/
```

### Run with coverage:
```bash
pytest backend/tests/ --cov=backend --cov-report=html
```

## Development

### Code Style

We use:
- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking

Run code quality checks:
```bash
black backend/
flake8 backend/
mypy backend/
```

### Adding New Services

1. Create service directory: `services/new_service/`
2. Create `main.py` with FastAPI application
3. Create Dockerfile: `docker/Dockerfile.new_service`
4. Add service to `docker-compose.yml`
5. Add API routes to `nginx/nginx.conf`
6. Update this README

## Deployment

### Staging

Deployment to staging is automatic on push to `develop` branch.

### Production

Deployment to production is automatic on push to `main` branch.

Manual deployment:
```bash
# Build and push images
docker-compose build
docker-compose push

# Deploy to production
kubectl apply -f k8s/
```

## Monitoring

- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **ELK Stack**: Log aggregation

Access monitoring dashboards at configured endpoints.

## Troubleshooting

### Service won't start
- Check logs: `docker-compose logs <service_name>`
- Verify environment variables
- Check infrastructure services are running

### Database connection issues
- Verify database is running: `docker-compose ps postgres`
- Check connection string in environment variables
- Ensure network connectivity

### High memory usage
- Adjust container memory limits in docker-compose.yml
- Monitor with: `docker stats`

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests and linting
5. Submit pull request

## License

Proprietary - All rights reserved

## Support

For issues and questions, contact the development team.
