# AI Companion Platform - Backend

## Overview

This is the backend implementation for the AI Companion Platform, consisting of 22 microservices built with Python 3.12 and FastAPI.

**Recently Implemented Services:**
- ✅ Auth Service (8011) - JWT-based authentication with refresh tokens
- ✅ User Service (8012) - User profiles, preferences, and character settings
- ✅ STT Service (8019) - Multi-provider speech-to-text (Whisper, Deepgram, Google)
- ✅ TTS Service (8020) - Multi-provider text-to-speech (ElevenLabs, Azure, Google)
- ✅ Vision Service (8018) - Computer vision with YOLOv8 and MediaPipe
- ✅ Social Service (8021) - Social relationship management with Neo4j integration
- ✅ Character Service (8016) - Character state management and configuration
- ✅ Animation Service (8017) - Animation clips, states, and graph management
- ✅ Asset Service (8013) - 3D asset management with versioning
- ✅ World Service (8014) - World graph and environment with navigation
- ✅ Physics Service (8015) - Physics simulation and collision detection
- ✅ Multi-Agent Service (8022) - Multi-agent coordination and task distribution

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
- **Auth Service** (Port 8011): ✅ JWT-based authentication with refresh tokens, password management, and role-based access control
- **User Service** (Port 8012): ✅ User profiles, preferences, character settings, and usage statistics

### 3D & Physics Services
- **Asset Service** (Port 8013): ✅ 3D asset management with versioning, metadata, and bundle support
- **World Service** (Port 8014): ✅ World graph and environment with A* navigation and Neo4j integration
- **Physics Service** (Port 8015): ✅ Physics simulation with collision detection, raycasting, and force application
- **Character Service** (Port 8016): ✅ Character state management, configuration, and snapshots
- **Animation Service** (Port 8017): ✅ Animation clips, states, graphs, and blend shape management

### Vision & Speech Services
- **Vision Service** (Port 8018): ✅ Computer vision with object detection (YOLOv8), pose estimation, face detection, and hand tracking (MediaPipe)
- **STT Service** (Port 8019): ✅ Multi-provider speech-to-text with Whisper, Deepgram, and Google support
- **TTS Service** (Port 8020): ✅ Multi-provider text-to-speech with ElevenLabs, Azure, and Google support

### Advanced AI Services
- **Social Service** (Port 8021): ✅ Social relationship management with Neo4j graph integration and analytics
- **Multi-Agent Service** (Port 8022): ✅ Multi-agent coordination with task distribution and message passing

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

## New Services Implementation Details

### Auth Service (Port 8011)
**Features:**
- JWT-based authentication with access and refresh tokens
- Password hashing with bcrypt
- Token refresh mechanism with automatic rotation
- Password change functionality
- Token verification endpoint
- Role-based access control (RBAC)
- Token blacklist for logout
- User registration with email validation

**API Endpoints:**
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout and revoke tokens
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/change-password` - Change password
- `POST /api/v1/auth/verify-token` - Verify token validity

### User Service (Port 8012)
**Features:**
- User profile management (username, bio, avatar, location)
- User preferences (theme, notifications, privacy settings)
- Character preferences (personality traits, voice settings, appearance)
- User statistics tracking (conversations, messages, interaction time)
- Support for PostgreSQL and MongoDB storage
- Comprehensive user data management

**API Endpoints:**
- `GET /api/v1/users/{user_id}/profile` - Get user profile
- `PUT /api/v1/users/{user_id}/profile` - Update user profile
- `GET /api/v1/users/{user_id}/preferences` - Get user preferences
- `PUT /api/v1/users/{user_id}/preferences` - Update user preferences
- `GET /api/v1/users/{user_id}/character` - Get character preferences
- `PUT /api/v1/users/{user_id}/character` - Update character preferences
- `GET /api/v1/users/{user_id}/stats` - Get user statistics
- `POST /api/v1/users/{user_id}/stats/increment` - Increment user stats
- `DELETE /api/v1/users/{user_id}` - Delete user account

### STT Service (Port 8019)
**Features:**
- Multi-provider support (Whisper, Deepgram, Google)
- Real-time and batch transcription
- Multiple audio formats (WAV, MP3, OGG, FLAC)
- Multi-language support (English, Vietnamese, Spanish, etc.)
- Word-level timestamps
- Voice activity detection (VAD)
- File upload and base64 audio support

**API Endpoints:**
- `POST /api/v1/stt/transcribe` - Transcribe audio from base64
- `POST /api/v1/stt/transcribe/file` - Transcribe audio file
- `GET /api/v1/stt/providers` - Get available providers
- `GET /api/v1/stt/languages` - Get supported languages

### TTS Service (Port 8020)
**Features:**
- Multi-provider support (ElevenLabs, Azure, Google)
- High-quality voice synthesis
- Multiple output formats (MP3, WAV, OGG)
- Voice selection and customization
- Speed and pitch adjustment
- Emotion support (where available)
- Streaming response support

**API Endpoints:**
- `POST /api/v1/tts/synthesize` - Synthesize speech from text
- `GET /api/v1/tts/voices/{provider}` - Get available voices
- `GET /api/v1/tts/providers` - Get available providers
- `GET /api/v1/tts/languages` - Get supported languages

### Vision Service (Port 8018)
**Features:**
- Object detection using YOLOv8 (80 classes)
- Human pose estimation (33 landmarks)
- Face detection with landmarks
- Hand tracking (21 landmarks)
- Multi-hand support with handedness detection
- Confidence threshold filtering
- File upload and base64 image support
- Mock detection when libraries not installed

**API Endpoints:**
- `POST /api/v1/vision/detect` - Detect objects/poses/faces/hands
- `POST /api/v1/vision/detect/file` - Detect from uploaded file
- `GET /api/v1/vision/capabilities` - Get service capabilities

### Social Service (Port 8021)
**Features:**
- Relationship management between users and characters
- Affinity and trust scoring
- Interaction logging and analytics
- Social graph integration with Neo4j
- Relationship recommendations
- Topic distribution analysis
- Relationship stage progression

**API Endpoints:**
- `POST /api/v1/social/relationships` - Create relationship
- `GET /api/v1/social/relationships/{relationship_id}` - Get relationship
- `GET /api/v1/social/users/{user_id}/relationships` - Get user relationships
- `PUT /api/v1/social/relationships/{relationship_id}` - Update relationship
- `POST /api/v1/social/interactions` - Log interaction
- `GET /api/v1/social/relationships/{relationship_id}/interactions` - Get interactions
- `POST /api/v1/social/recommendations` - Get recommendations
- `GET /api/v1/social/relationships/{relationship_id}/analytics` - Get analytics

### Character Service (Port 8016)
**Features:**
- Character configuration management
- Character state tracking (emotion, activity, position)
- Personality traits storage
- Appearance and voice settings
- Character snapshots for persistence
- Health and energy level tracking
- Animation state management

**API Endpoints:**
- `POST /api/v1/characters` - Create character
- `GET /api/v1/characters/{character_id}` - Get character
- `GET /api/v1/characters` - List characters
- `PUT /api/v1/characters/{character_id}` - Update character
- `DELETE /api/v1/characters/{character_id}` - Delete character
- `POST /api/v1/characters/{character_id}/state` - Set character state
- `GET /api/v1/characters/{character_id}/state/{user_id}` - Get character state
- `POST /api/v1/characters/{character_id}/snapshot` - Create snapshot
- `GET /api/v1/characters/{character_id}/snapshots/{user_id}` - Get snapshots

### Animation Service (Port 8017)
**Features:**
- Animation clip management
- Animation state system
- Animation graph support
- Blend shape management
- Animation playback requests
- Category and tag filtering
- Transition management

**API Endpoints:**
- `POST /api/v1/animations/clips` - Create animation clip
- `GET /api/v1/animations/clips/{clip_id}` - Get animation clip
- `GET /api/v1/animations/clips` - List animation clips
- `POST /api/v1/animations/states` - Create animation state
- `POST /api/v1/animations/graphs` - Create animation graph
- `GET /api/v1/animations/graphs/character/{character_id}` - Get character graph
- `POST /api/v1/animations/play` - Play animation
- `POST /api/v1/animations/blend-shapes` - Create blend shape
- `GET /api/v1/animations/blend-shapes` - List blend shapes

### Asset Service (Port 8013)
**Features:**
- 3D asset management
- Asset versioning with changelog
- Asset bundling for distribution
- Metadata and tag support
- Public/private asset access
- Platform-specific bundles
- File size tracking

**API Endpoints:**
- `POST /api/v1/assets` - Create asset
- `GET /api/v1/assets/{asset_id}` - Get asset
- `GET /api/v1/assets` - List assets
- `POST /api/v1/assets/{asset_id}/versions` - Create version
- `GET /api/v1/assets/{asset_id}/versions` - Get versions
- `POST /api/v1/assets/bundles` - Create bundle
- `GET /api/v1/assets/bundles/{bundle_id}` - Get bundle
- `PUT /api/v1/assets/{asset_id}` - Update asset
- `DELETE /api/v1/assets/{asset_id}` - Delete asset

### World Service (Port 8014)
**Features:**
- Environment management
- World object placement
- Object relationships with Neo4j
- Navigation node system
- A* pathfinding algorithm
- Spatial bounds management
- Spawn point configuration

**API Endpoints:**
- `POST /api/v1/world/environments` - Create environment
- `GET /api/v1/world/environments/{environment_id}` - Get environment
- `GET /api/v1/world/environments` - List environments
- `POST /api/v1/world/objects` - Create world object
- `GET /api/v1/world/objects/{object_id}` - Get world object
- `GET /api/v1/world/environments/{environment_id}/objects` - Get environment objects
- `POST /api/v1/world/objects/relationship` - Create object relationship
- `POST /api/v1/world/navigation/nodes` - Create navigation node
- `POST /api/v1/world/navigation/path` - Find path
- `DELETE /api/v1/world/objects/{object_id}` - Delete object

### Physics Service (Port 8015)
**Features:**
- Physics body management
- Force application
- Velocity and position updates
- Raycast queries
- Collision event logging
- Physics simulation stepping
- Redis caching for real-time state
- Multiple collision shapes

**API Endpoints:**
- `POST /api/v1/physics/bodies` - Create physics body
- `GET /api/v1/physics/bodies/{body_id}` - Get physics body
- `PUT /api/v1/physics/bodies/{body_id}/state` - Update physics state
- `POST /api/v1/physics/apply-force` - Apply force
- `POST /api/v1/physics/raycast` - Perform raycast
- `POST /api/v1/physics/simulations` - Create simulation
- `POST /api/v1/physics/simulations/{simulation_id}/step` - Step simulation
- `DELETE /api/v1/physics/bodies/{body_id}` - Delete body

### Multi-Agent Service (Port 8022)
**Features:**
- Agent management and registration
- Task creation and assignment
- Automatic task assignment based on capabilities
- Agent-to-agent messaging with Redis
- Agent coordination and collaboration
- Workload and performance tracking
- Agent status management

**API Endpoints:**
- `POST /api/v1/agents` - Create agent
- `GET /api/v1/agents/{agent_id}` - Get agent
- `GET /api/v1/agents` - List agents
- `POST /api/v1/agents/tasks` - Create task
- `POST /api/v1/agents/tasks/{task_id}/assign` - Assign task
- `POST /api/v1/agents/tasks/{task_id}/complete` - Complete task
- `POST /api/v1/agents/messages` - Send message
- `GET /api/v1/agents/{agent_id}/messages` - Get messages
- `POST /api/v1/agents/coordinations` - Create coordination
- `POST /api/v1/agents/auto-assign` - Auto-assign task
- `DELETE /api/v1/agents/{agent_id}` - Delete agent

## Implementation Status

All 22 backend microservices have been successfully implemented! The AI Companion Platform now has complete backend coverage including:

**Core AI Services (10 services):**
- ✅ LLM Service (8001)
- ✅ Memory Service (8002)
- ✅ Conversation Service (8003)
- ✅ Emotion Service (8004)
- ✅ Motivation Service (8005)
- ✅ Reflection Service (8006)
- ✅ Learning Service (8007)
- ✅ Plugin Service (8008)
- ✅ Scheduler Service (8009)
- ✅ Vision Memory Service (8010)

**User Management Services (2 services):**
- ✅ Auth Service (8011)
- ✅ User Service (8012)

**3D & Physics Services (5 services):**
- ✅ Asset Service (8013)
- ✅ World Service (8014)
- ✅ Physics Service (8015)
- ✅ Character Service (8016)
- ✅ Animation Service (8017)

**Vision & Speech Services (3 services):**
- ✅ Vision Service (8018)
- ✅ STT Service (8019)
- ✅ TTS Service (8020)

**Advanced AI Services (2 services):**
- ✅ Social Service (8021)
- ✅ Multi-Agent Service (8022)

Total: **22 fully implemented microservices** with comprehensive API coverage, database integration, and production-ready features.
