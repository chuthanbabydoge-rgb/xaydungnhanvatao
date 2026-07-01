# AITAONHANVATAO — AI Desktop Companion Platform

[//]: # "AI on the table" - An AR/VR AI Companion Platform

A cross-platform AR system that renders a 3D anime character on your desk with realistic physics, natural conversation, long-term memory, and evolving personality.

## Project Structure

```
AITAONHANVATAO/
├── src/                          # Source code
│   ├── services/                 # Backend microservices (22 services)
│   │   ├── brain/               # Core AI decision engine
│   │   ├── llm/                 # Multi-provider LLM router
│   │   ├── memory/              # Vector + graph memory
│   │   ├── vision/              # Computer vision (YOLOv8, MediaPipe)
│   │   ├── voice/               # Speech-to-text + Text-to-speech
│   │   ├── emotion/             # Emotion engine
│   │   ├── motivation/          # Goal/motivation system
│   │   ├── reflection/          # Self-reflection engine
│   │   ├── learning/            # Pattern learning
│   │   ├── conversation/        # Conversation orchestration
│   │   ├── character/           # Character state management
│   │   ├── animation/           # Animation engine
│   │   ├── avatar/              # Avatar management
│   │   ├── world/               # World graph + navigation
│   │   ├── physics/             # Physics simulation
│   │   ├── social/              # Social relationships
│   │   ├── auth/                # Authentication
│   │   ├── user/                # User profiles
│   │   ├── scheduler/           # Task scheduling
│   │   ├── plugin/              # Plugin SDK
│   │   └── multi-agent/         # Agent coordination
│   ├── pipeline/                 # Real-time AI pipeline
│   │   ├── camera/              # Camera capture
│   │   ├── vision/              # Scene understanding
│   │   ├── world-graph/         # Knowledge graph
│   │   ├── reasoning/           # Logical inference
│   │   ├── llm/                 # LLM integration
│   │   ├── animation/           # Procedural animation
│   │   ├── voice/               # Voice processing
│   │   ├── avatar/              # Character rendering
│   │   ├── unity-bridge/        # Unity integration
│   │   └── ar/                  # AR overlay
│   ├── agents/                   # Multi-agent system
│   │   ├── core/                # Shared agent framework
│   │   └── agents/              # Agent implementations
│   └── unity/                    # Unity 6 frontend
├── packages/                     # Shared libraries
│   ├── shared-python/           # Python shared utilities
│   └── shared-types/            # API type definitions
├── docs/                         # Documentation
│   ├── architecture/            # Architecture docs
│   ├── design/                  # Design documents
│   ├── api/                     # API docs
│   └── guides/                  # Developer guides
├── infra/                        # Infrastructure
│   ├── docker/                  # Dockerfiles
│   ├── k8s/                     # Kubernetes manifests
│   ├── terraform/               # Infrastructure as Code
│   ├── monitoring/              # Prometheus, Grafana
│   └── nginx/                   # API Gateway
├── scripts/                      # Dev/build/deploy scripts
├── tests/                        # Integration & performance tests
└── .github/workflows/            # CI/CD pipelines
```

## Quick Start

```bash
# Development environment
./scripts/dev.ps1

# Build all services
./scripts/build.ps1

# Deploy
./scripts/deploy.ps1
```

## Tech Stack

- **Frontend:** Unity 6 (HDRP/URP), AR Foundation, C# 12
- **Backend:** Python 3.12 + FastAPI, Go (Gin), Node.js (Express)
- **AI:** OpenAI GPT-4, Claude 3, Gemini, Whisper, ElevenLabs, OpenCV, YOLOv8, PyTorch
- **Databases:** PostgreSQL 15, MongoDB 7, Redis 7, Qdrant 1.7, Neo4j 5
- **Infra:** Docker, Kubernetes, Kafka, RabbitMQ, Prometheus, Grafana

## License

Proprietary
