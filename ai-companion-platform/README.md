# AI Companion Platform

Production-ready AI Companion Platform with 40 modules across Unity 6 frontend and Python 3.12/FastAPI backend.

## Quick Start

### Prerequisites
- Unity 6.0 LTS
- Python 3.12
- Docker 24+
- Kubernetes 1.28+ (for production)

### Local Development

```bash
# Clone repository
git clone https://github.com/your-org/ai-companion-platform.git
cd ai-companion-platform

# Start infrastructure
docker-compose up -d

# Start backend services
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Start Unity frontend
# Open frontend/ directory in Unity 6
```

## Architecture

- **Frontend**: Unity 6 with HDRP, AR Foundation, XR Interaction Toolkit, Addressables
- **Backend**: Python 3.12 with FastAPI, 18 microservices
- **Databases**: PostgreSQL, MongoDB, Redis, Qdrant, Neo4j
- **Infrastructure**: Docker, Kubernetes, Terraform, Ansible

## Documentation

- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Development Roadmap](docs/architecture/ROADMAP.md)
- [Module Dependencies](docs/architecture/MODULE_DEPENDENCIES.md)
- [Source Tree](docs/architecture/SOURCE_TREE.md)
- [Tech Stack](docs/architecture/TECH_STACK_FINAL.md)

## Services

### Backend Services (18)
- Auth Service (Port 8000)
- User Service (Port 8001)
- LLM Service (Port 8002)
- Voice Service (Port 8003)
- Vision Service (Port 8004)
- Memory Service (Port 8005)
- Personality Service (Port 8006)
- Motivation Service (Port 8007)
- Reflection Service (Port 8008)
- Learning Service (Port 8009)
- Social Service (Port 8010)
- Fusion Service (Port 8011)
- World Service (Port 8012)
- Scheduler Service (Port 8013)
- Multi-Agent Service (Port 8014)
- Asset Service (Port 8015)
- Analytics Service (Port 8016)
- Security Service (Port 8017)
- Billing Service (Port 8018)

### Frontend Modules (22)
- Rendering Layer (4 modules)
- Character Layer (3 modules)
- Animation Layer (2 modules)
- AI Layer (8 modules)
- World Layer (3 modules)
- Communication Layer (3 modules)

## Development

See [Development Guide](docs/development/CODING_STANDARDS.md) for coding standards and practices.

## License

Proprietary - All rights reserved