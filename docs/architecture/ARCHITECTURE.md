# AI Companion System - Total Architecture Design

## Table of Contents
1. [System Overview](#system-overview)
2. [Microservice Architecture](#microservice-architecture)
3. [Technology Stack](#technology-stack)
4. [Service Communication](#service-communication)
5. [Data Flow](#data-flow)
6. [Deployment Architecture](#deployment-architecture)
7. [Security Architecture](#security-architecture)
8. [Scalability Strategy](#scalability-strategy)

---

## 1. System Overview

### 1.1 System Purpose
Hệ thống AI Companion là một nền tảng AR/VR cho phép nhân vật ảo xuất hiện trong thế giới thực với khả năng:
- Hiển thị 3D chất lượng AAA trên mặt bàn thông qua AR
- Nhận thức không gian và tránh vật cản
- Đối thoại tự nhiên với AI
- Biểu cảm cảm xúc và lip sync
- Trí nhớ dài hạn
- Tương tác với môi trường và người dùng

### 1.2 System Requirements

#### Functional Requirements
- **FR-001**: Nhân vật 3D xuất hiện trên bàn làm việc thông qua camera/AR
- **FR-002**: Nhân vật có khả năng di chuyển, đi bộ, nhảy, leo, quay đầu
- **FR-003**: Nhân vật tránh vật cản và không xuyên qua vật thể
- **FR-004**: Nhân vật đổ bóng và phản chiếu đúng theo ánh sáng môi trường
- **FR-005**: Nhân vật nhìn vào người đang nói
- **FR-006**: Nhân vật có khả năng nghe, suy nghĩ và trả lời tự nhiên
- **FR-007**: Nhân vật có biểu cảm khuôn mặt và cảm xúc
- **FR-008**: Nhân vật có lip sync đồng bộ với giọng nói
- **FR-009**: Nhân vật có trí nhớ dài hạn về người dùng
- **FR-010**: Nhân vật có thể tương tác với các ứng dụng trên máy tính

#### Non-Functional Requirements
- **NFR-001**: Latency < 100ms cho phản hồi thực-time
- **NFR-002**: 99.9% uptime cho production
- **NFR-003**: Hỗ trợ 10,000 concurrent users
- **NFR-004**: Frame rate ≥ 60 FPS cho AR rendering
- **NFR-005**: Memory usage < 2GB cho client application
- **NFR-006**: Bandwidth optimization cho streaming
- **NFR-007**: Security compliance (GDPR, SOC2)
- **NFR-008**: Scalable architecture

---

## 2. Microservice Architecture

### 2.1 Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        UnityClient[Unity Client]
        WebClient[Web Dashboard]
        MobileClient[Mobile App]
    end
    
    subgraph "API Gateway"
        APIGateway[API Gateway<br/>Kong/Envoy]
        LoadBalancer[Load Balancer<br/>Nginx]
    end
    
    subgraph "Core Services"
        AuthService[Auth Service]
        UserService[User Service]
        SessionService[Session Service]
    end
    
    subgraph "AI Services"
        LLMService[LLM Service]
        VoiceService[Voice Service]
        VisionService[Vision Service]
        MemoryService[Memory Service]
        EmotionService[Emotion Service]
        AnimationService[Animation Service]
        AIService[AI Agent Service]
    end
    
    subgraph "AR Services"
        ARService[AR Service]
        PhysicsService[Physics Service]
        AssetService[Asset Service]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL)]
        MongoDB[(MongoDB)]
        Redis[(Redis)]
        Qdrant[(Qdrant<br/>Vector DB)]
        Neo4j[(Neo4j<br/>Graph DB)]
        S3[(AWS S3)]
    end
    
    subgraph "Infrastructure"
        Kafka[Apache Kafka]
        RabbitMQ[RabbitMQ]
        Prometheus[Prometheus]
        Grafana[Grafana]
        ELK[ELK Stack]
    end
    
    subgraph "External APIs"
        OpenAI[OpenAI API]
        ElevenLabs[ElevenLabs]
        Deepgram[Deepgram]
    end
    
    UnityClient --> APIGateway
    WebClient --> APIGateway
    MobileClient --> APIGateway
    
    APIGateway --> LoadBalancer
    LoadBalancer --> AuthService
    LoadBalancer --> UserService
    LoadBalancer --> SessionService
    
    LoadBalancer --> LLMService
    LoadBalancer --> VoiceService
    LoadBalancer --> VisionService
    LoadBalancer --> MemoryService
    LoadBalancer --> EmotionService
    LoadBalancer --> AnimationService
    LoadBalancer --> AIService
    LoadBalancer --> ARService
    LoadBalancer --> PhysicsService
    LoadBalancer --> AssetService
    
    AuthService --> PostgreSQL
    UserService --> PostgreSQL
    SessionService --> Redis
    
    LLMService --> Redis
    VoiceService --> S3
    VisionService --> Redis
    MemoryService --> Qdrant
    MemoryService --> Neo4j
    EmotionService --> PostgreSQL
    AnimationService --> S3
    AIService --> PostgreSQL
    ARService --> MongoDB
    PhysicsService --> Redis
    AssetService --> S3
    
    LLMService --> OpenAI
    VoiceService --> ElevenLabs
    VoiceService --> Deepgram
    
    LLMService --> Kafka
    VoiceService --> Kafka
    VisionService --> Kafka
    MemoryService --> Kafka
    EmotionService --> Kafka
    AnimationService --> Kafka
    AIService --> Kafka
    
    Kafka --> RabbitMQ
    
    Prometheus --> Grafana
    ELK --> Grafana
```

### 2.2 Service Catalog

#### 2.2.1 Client Layer
| Service | Description | Technology |
|---------|-------------|------------|
| Unity Client | Desktop AR application | Unity 2023, AR Foundation |
| Web Dashboard | Admin dashboard | React, Next.js |
| Mobile App | Mobile companion | React Native |

#### 2.2.2 API Gateway
| Service | Description | Technology |
|---------|-------------|------------|
| API Gateway | Route management, auth, rate limiting | Kong/Envoy |
| Load Balancer | Traffic distribution | Nginx |

#### 2.2.3 Core Services
| Service | Description | Technology | Port |
|---------|-------------|------------|------|
| Auth Service | Authentication, authorization | Node.js, JWT | 3001 |
| User Service | User profile management | Python, FastAPI | 3002 |
| Session Service | Session management | Go, Gin | 3003 |

#### 2.2.4 AI Services
| Service | Description | Technology | Port |
|---------|-------------|------------|------|
| LLM Service | LLM integration, routing | Python, FastAPI | 4001 |
| Voice Service | STT, TTS, voice clone | Python, FastAPI | 4002 |
| Vision Service | Computer vision pipeline | Python, FastAPI | 4003 |
| Memory Service | Vector search, knowledge graph | Python, FastAPI | 4004 |
| Emotion Service | Emotion engine | Python, FastAPI | 4005 |
| Animation Service | Animation blending | C#, Unity | 4006 |
| AI Agent Service | Tool calling, MCP | Python, FastAPI | 4007 |

#### 2.2.5 AR Services
| Service | Description | Technology | Port |
|---------|-------------|------------|------|
| AR Service | AR tracking, rendering | C#, Unity | 5001 |
| Physics Service | Physics simulation | C#, Unity | 5002 |
| Asset Service | Asset management | Node.js | 5003 |

#### 2.2.6 Data Layer
| Database | Purpose | Technology |
|----------|---------|------------|
| PostgreSQL | Relational data, user info | PostgreSQL 15 |
| MongoDB | Document storage, session data | MongoDB 7 |
| Redis | Cache, session, pub/sub | Redis 7 |
| Qdrant | Vector embeddings | Qdrant 1.7 |
| Neo4j | Knowledge graph | Neo4j 5 |
| S3 | Asset storage | AWS S3/MinIO |

#### 2.2.7 Infrastructure
| Component | Purpose | Technology |
|-----------|---------|------------|
| Kafka | Event streaming | Apache Kafka 3.6 |
| RabbitMQ | Message queue | RabbitMQ 3.12 |
| Prometheus | Metrics collection | Prometheus |
| Grafana | Monitoring dashboard | Grafana |
| ELK Stack | Logging | Elasticsearch, Logstash, Kibana |

### 2.3 Service Communication Patterns

#### 2.3.1 Synchronous Communication
- **REST API**: Client ↔ Services
- **gRPC**: Service ↔ Service (high performance)
- **WebSocket**: Real-time communication (Unity ↔ Backend)

#### 2.3.2 Asynchronous Communication
- **Kafka**: Event streaming between services
- **RabbitMQ**: Task queue for async operations
- **Redis Pub/Sub**: Real-time notifications

---

## 3. Technology Stack

### 3.1 Frontend
```yaml
Unity:
  version: "2023.2 LTS"
  packages:
    - AR Foundation
    - ARCore XR Plugin
    - ARKit XR Plugin
    - OpenXR Plugin
    - Unity ML-Agents
    -DOTS (Data-Oriented Technology Stack)

Web Dashboard:
  framework: "Next.js 14"
  language: "TypeScript"
  ui_library: "React 18"
  styling: "Tailwind CSS"
  state_management: "Zustand"

Mobile App:
  framework: "React Native 0.73"
  language: "TypeScript"
  navigation: "React Navigation"
```

### 3.2 Backend
```yaml
API Services:
  primary_language: "Python 3.11"
  framework: "FastAPI 0.104"
  async_runtime: "asyncio"
  
Microservices:
  python:
    - FastAPI
    - Pydantic
    - SQLAlchemy
    - Alembic
  go:
    - Gin
    - GORM
  nodejs:
    - Express
    - TypeScript
    - Prisma
```

### 3.3 AI/ML
```yaml
LLM:
  providers:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude 3)
    - Google (Gemini Pro)
    - DeepSeek
    - Local: Llama 2, Qwen
  orchestration: "LangChain"
  
Computer Vision:
  libraries:
    - OpenCV 4.8
    - MediaPipe
    - PyTorch 2.1
    - ONNX Runtime
  models:
    - YOLOv8 (object detection)
    - SAM2 (segmentation)
    - DepthAnything (depth estimation)
    - ORB-SLAM3 (SLAM)
    
Voice:
  stt:
    - Whisper (OpenAI)
    - Deepgram
  tts:
    - ElevenLabs
    - XTTS
    - Fish Speech
  voice_clone:
    - ElevenLabs
    - XTTS
    
Vector Database:
  primary: "Qdrant"
  alternative: "Milvus"
  embedding_model: "text-embedding-ada-002"
  
Graph Database:
  primary: "Neo4j"
  driver: "neo4j-python"
```

### 3.4 Infrastructure
```yaml
Container:
  runtime: "Docker 24"
  orchestration: "Kubernetes 1.28"
  
Cloud:
  provider: "AWS"
  services:
    - EC2 (compute)
    - S3 (storage)
    - RDS (database)
    - ElastiCache (Redis)
    - Lambda (serverless)
    - CloudFront (CDN)
    
CI/CD:
  platform: "GitHub Actions"
  tools:
    - Docker Build
    - Kubernetes Deploy
    - Helm Charts
    - ArgoCD (GitOps)
    
Monitoring:
  metrics: "Prometheus"
  logging: "ELK Stack"
  tracing: "Jaeger"
  dashboard: "Grafana"
```

---

## 4. Service Communication

### 4.1 API Design

#### 4.1.1 REST API Endpoints

```yaml
Auth Service:
  POST   /api/v1/auth/register
  POST   /api/v1/auth/login
  POST   /api/v1/auth/logout
  POST   /api/v1/auth/refresh
  POST   /api/v1/auth/verify
  POST   /api/v1/auth/forgot-password
  POST   /api/v1/auth/reset-password

User Service:
  GET    /api/v1/users/{id}
  PUT    /api/v1/users/{id}
  DELETE /api/v1/users/{id}
  GET    /api/v1/users/{id}/profile
  PUT    /api/v1/users/{id}/profile
  GET    /api/v1/users/{id}/preferences
  PUT    /api/v1/users/{id}/preferences

Session Service:
  POST   /api/v1/sessions
  GET    /api/v1/sessions/{id}
  PUT    /api/v1/sessions/{id}
  DELETE /api/v1/sessions/{id}
  GET    /api/v1/sessions/{id}/state

LLM Service:
  POST   /api/v1/llm/chat
  POST   /api/v1/llm/stream
  POST   /api/v1/llm/function-call
  GET    /api/v1/llm/models
  POST   /api/v1/llm/route

Voice Service:
  POST   /api/v1/voice/stt
  POST   /api/v1/voice/tts
  POST   /api/v1/voice/clone
  POST   /api/v1/voice/emotion
  GET    /api/v1/voice/voices

Vision Service:
  POST   /api/v1/vision/detect
  POST   /api/v1/vision/segment
  POST   /api/v1/vision/depth
  POST   /api/v1/vision/pose
  POST   /api/v1/vision/track

Memory Service:
  POST   /api/v1/memory/store
  GET    /api/v1/memory/search
  GET    /api/v1/memory/retrieve
  DELETE /api/v1/memory/{id}
  POST   /api/v1/memory/consolidate

Emotion Service:
  POST   /api/v1/emotion/detect
  GET    /api/v1/emotion/state
  PUT    /api/v1/emotion/state
  POST   /api/v1/emotion/update

Animation Service:
  POST   /api/v1/animation/play
  POST   /api/v1/animation/blend
  POST   /api/v1/animation/lipsync
  GET    /api/v1/animation/list

AI Agent Service:
  POST   /api/v1/agent/execute
  POST   /api/v1/agent/tool
  POST   /api/v1/agent/mcp
  GET    /api/v1/agent/tools

AR Service:
  POST   /api/v1/ar/track
  POST   /api/v1/ar/anchor
  GET    /api/v1/ar/scene
  POST   /api/v1/ar/render

Physics Service:
  POST   /api/v1/physics/simulate
  POST   /api/v1/physics/collision
  GET    /api/v1/physics/state

Asset Service:
  GET    /api/v1/assets/{id}
  POST   /api/v1/assets/upload
  DELETE /api/v1/assets/{id}
  GET    /api/v1/assets/list
```

#### 4.1.2 WebSocket Events

```yaml
Unity Client Connection:
  connect:
    event: "connection:established"
    data:
      session_id: string
      user_id: string
      timestamp: datetime
  
  message:
    event: "message:send"
    data:
      text: string
      emotion: string
      metadata: object
  
  response:
    event: "message:response"
    data:
      text: string
      audio_url: string
      animation: object
      emotion: string
  
  animation:
    event: "animation:trigger"
    data:
      animation_name: string
      blend_weight: float
      duration: float
  
  emotion:
    event: "emotion:update"
    data:
      mood: string
      intensity: float
      expression: string
  
  vision:
    event: "vision:frame"
    data:
      frame_id: string
      timestamp: datetime
      detection_results: object
```

### 4.2 Message Queue Topics

```yaml
Kafka Topics:
  - user.events
  - session.events
  - chat.events
  - voice.events
  - vision.events
  - memory.events
  - emotion.events
  - animation.events
  - agent.events
  - ar.events
  - physics.events
  
RabbitMQ Queues:
  - llm.requests
  - llm.responses
  - voice.stt.requests
  - voice.tts.requests
  - vision.processing
  - memory.indexing
  - animation.rendering
  - email.notifications
  - background.tasks
```

---

## 5. Data Flow

### 5.1 User Interaction Flow

```mermaid
sequenceDiagram
    participant User
    participant Unity
    participant APIGateway
    participant VoiceService
    participant LLMService
    participant MemoryService
    participant EmotionService
    participant AnimationService
    
    User->>Unity: Speak
    Unity->>VoiceService: Audio Stream (WebSocket)
    VoiceService->>VoiceService: STT (Whisper)
    VoiceService->>LLMService: Text Transcript
    LLMService->>MemoryService: Retrieve Context
    MemoryService-->>LLMService: Relevant Memories
    LLMService->>LLMService: Generate Response
    LLMService->>EmotionService: Detect Emotion
    EmotionService-->>LLMService: Emotion State
    LLMService->>VoiceService: Response Text
    VoiceService->>VoiceService: TTS (ElevenLabs)
    VoiceService->>AnimationService: Lip Sync Data
    AnimationService->>AnimationService: Generate Visemes
    VoiceService-->>Unity: Audio Stream
    AnimationService-->>Unity: Animation Data
    Unity->>User: Audio + Animation
    LLMService->>MemoryService: Store Conversation
```

### 5.2 AR Tracking Flow

```mermaid
sequenceDiagram
    participant Camera
    participant VisionService
    participant ARService
    participant PhysicsService
    participant Unity
    
    Camera->>VisionService: Video Frame
    VisionService->>VisionService: SLAM (ORB-SLAM3)
    VisionService->>VisionService: Plane Detection
    VisionService->>VisionService: Depth Estimation
    VisionService->>VisionService: Object Detection
    VisionService->>ARService: World Coordinates
    ARService->>ARService: Anchor Management
    ARService->>PhysicsService: Scene Data
    PhysicsService->>PhysicsService: Collision Detection
    PhysicsService->>PhysicsService: Path Planning
    PhysicsService-->>Unity: Avatar Position
    Unity->>Unity: Render Avatar
```

### 5.3 Memory Storage Flow

```mermaid
sequenceDiagram
    participant LLMService
    participant MemoryService
    participant Qdrant
    participant Neo4j
    participant Redis
    
    LLMService->>MemoryService: Store Memory
    MemoryService->>MemoryService: Extract Entities
    MemoryService->>MemoryService: Generate Embedding
    MemoryService->>Qdrant: Store Vector
    MemoryService->>Neo4j: Store Graph
    MemoryService->>Redis: Cache Summary
    MemoryService-->>LLMService: Memory ID
    
    LLMService->>MemoryService: Retrieve Memory
    MemoryService->>Redis: Check Cache
    alt Cache Hit
        Redis-->>MemoryService: Cached Results
    else Cache Miss
        MemoryService->>Qdrant: Vector Search
        Qdrant-->>MemoryService: Similar Vectors
        MemoryService->>Neo4j: Graph Traversal
        Neo4j-->>MemoryService: Related Entities
        MemoryService->>Redis: Update Cache
    end
    MemoryService-->>LLMService: Retrieved Memories
```

---

## 6. Deployment Architecture

### 6.1 Kubernetes Deployment

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-companion
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
  namespace: ai-companion
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
      - name: auth-service
        image: ai-companion/auth-service:latest
        ports:
        - containerPort: 3001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3001
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: auth-service
  namespace: ai-companion
spec:
  selector:
    app: auth-service
  ports:
  - port: 3001
    targetPort: 3001
  type: ClusterIP
```

### 6.2 Infrastructure Diagram

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "VPC"
            subgraph "Public Subnet"
                ALB[Application Load Balancer]
                NAT[NAT Gateway]
            end
            
            subgraph "Private Subnet - Services"
                K8S[Kubernetes Cluster]
                subgraph "K8S Nodes"
                    Node1[Node 1]
                    Node2[Node 2]
                    Node3[Node 3]
                end
            end
            
            subgraph "Private Subnet - Data"
                RDS[(Amazon RDS<br/>PostgreSQL)]
                ElastiCache[(Amazon ElastiCache<br/>Redis)]
                Neo4j[Neo4j on EC2]
                Qdrant[Qdrant on EC2]
            end
            
            subgraph "Private Subnet - Storage"
                S3[(Amazon S3)]
                EFS[Amazon EFS]
            end
        end
        
        subgraph "CDN"
            CloudFront[CloudFront]
        end
        
        subgraph "Monitoring"
            CloudWatch[CloudWatch]
            XRay[X-Ray]
        end
    end
    
    User[User] --> CloudFront
    CloudFront --> ALB
    ALB --> K8S
    K8S --> RDS
    K8S --> ElastiCache
    K8S --> Neo4j
    K8S --> Qdrant
    K8S --> S3
    K8S --> EFS
    
    K8S --> CloudWatch
    K8S --> XRay
```

### 6.3 Docker Compose (Development)

```yaml
version: '3.8'

services:
  # API Gateway
  api-gateway:
    image: kong:latest
    ports:
      - "8000:8000"
      - "8443:8443"
    environment:
      KONG_DATABASE: postgres
      KONG_PG_HOST: postgres
      KONG_PG_DATABASE: kong
    depends_on:
      - postgres
    networks:
      - ai-companion

  # Auth Service
  auth-service:
    build: ./services/auth
    ports:
      - "3001:3001"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/auth_db
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET}
    depends_on:
      - postgres
      - redis
    networks:
      - ai-companion

  # User Service
  user-service:
    build: ./services/user
    ports:
      - "3002:3002"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/user_db
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    networks:
      - ai-companion

  # LLM Service
  llm-service:
    build: ./services/llm
    ports:
      - "4001:4001"
    environment:
      REDIS_URL: redis://redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on:
      - redis
    networks:
      - ai-companion

  # Voice Service
  voice-service:
    build: ./services/voice
    ports:
      - "4002:4002"
    environment:
      REDIS_URL: redis://redis:6379
      ELEVENLABS_API_KEY: ${ELEVENLABS_API_KEY}
      DEEPGRAM_API_KEY: ${DEEPGRAM_API_KEY}
    depends_on:
      - redis
    networks:
      - ai-companion

  # Vision Service
  vision-service:
    build: ./services/vision
    ports:
      - "4003:4003"
    environment:
      REDIS_URL: redis://redis:6379
    depends_on:
      - redis
    networks:
      - ai-companion
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Memory Service
  memory-service:
    build: ./services/memory
    ports:
      - "4004:4004"
    environment:
      QDRANT_URL: http://qdrant:6333
      NEO4J_URL: bolt://neo4j:7687
      REDIS_URL: redis://redis:6379
    depends_on:
      - qdrant
      - neo4j
      - redis
    networks:
      - ai-companion

  # Emotion Service
  emotion-service:
    build: ./services/emotion
    ports:
      - "4005:4005"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/emotion_db
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    networks:
      - ai-companion

  # AI Agent Service
  agent-service:
    build: ./services/agent
    ports:
      - "4007:4007"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/agent_db
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    networks:
      - ai-companion

  # Databases
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: ai_companion
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - ai-companion

  mongodb:
    image: mongo:7
    environment:
      MONGO_INITDB_ROOT_USERNAME: user
      MONGO_INITDB_ROOT_PASSWORD: pass
    volumes:
      - mongodb_data:/data/db
    networks:
      - ai-companion

  redis:
    image: redis:7
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - ai-companion

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - ai-companion

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data
    networks:
      - ai-companion

  # Message Queues
  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    networks:
      - ai-companion

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    networks:
      - ai-companion

  rabbitmq:
    image: rabbitmq:3.12-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: admin
    networks:
      - ai-companion

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - ai-companion

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - ai-companion

volumes:
  postgres_data:
  mongodb_data:
  redis_data:
  qdrant_data:
  neo4j_data:
  prometheus_data:
  grafana_data:

networks:
  ai-companion:
    driver: bridge
```

---

## 7. Security Architecture

### 7.1 Authentication & Authorization

```mermaid
graph LR
    A[User] --> B[Login Request]
    B --> C[Auth Service]
    C --> D{Credentials Valid?}
    D -->|Yes| E[Generate JWT]
    D -->|No| F[Return Error]
    E --> G[Store Refresh Token]
    G --> H[Return Access Token]
    H --> I[Client]
    I --> J[API Request]
    J --> K[API Gateway]
    K --> L[Validate JWT]
    L -->|Valid| M[Route to Service]
    L -->|Invalid| N[Return 401]
```

### 7.2 Security Layers

```yaml
Application Security:
  authentication:
    method: "JWT + OAuth 2.0"
    token_expiry: "15 minutes (access), 7 days (refresh)"
  
  authorization:
    method: "RBAC (Role-Based Access Control)"
    roles:
      - admin
      - user
      - guest
  
  rate_limiting:
    algorithm: "Token Bucket"
    limits:
      - authenticated: "1000 requests/hour"
      - unauthenticated: "100 requests/hour"

Network Security:
  tls:
    version: "TLS 1.3"
    certificate: "Let's Encrypt"
  
  firewall:
    inbound:
      - "Allow: 80, 443, 22"
      - "Deny: All"
    outbound:
      - "Allow: Specific APIs"
  
  vpn:
    type: "AWS Site-to-Site VPN"
    encryption: "AES-256"

Data Security:
  encryption:
    at_rest: "AES-256"
    in_transit: "TLS 1.3"
  
  pii_protection:
    compliance: "GDPR"
    data_masking: true
    anonymization: true
  
  backup:
    frequency: "Daily"
    retention: "90 days"
    encryption: true

API Security:
  validation:
    input_validation: true
    output_encoding: true
    sql_injection_prevention: true
    xss_prevention: true
  
  cors:
    policy: "Whitelist specific domains"
  
  api_keys:
    rotation: "Monthly"
    scope: "Per service"
```

### 7.3 IAM Policies

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::ai-companion-assets/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": ["${VPC_CIDR}"]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:Encrypt"
      ],
      "Resource": "arn:aws:kms:*:*:key/*"
    }
  ]
}
```

---

## 8. Scalability Strategy

### 8.1 Horizontal Scaling

```yaml
Auto-scaling:
  kubernetes:
    hpa:
      metrics:
        - type: Resource
          resource:
            name: cpu
            target:
              type: Utilization
              averageUtilization: 70
        - type: Resource
          resource:
            name: memory
            target:
              type: Utilization
              averageUtilization: 80
      min_replicas: 3
      max_replicas: 50
      
  services:
    auth_service:
      min_replicas: 3
      max_replicas: 10
    
    llm_service:
      min_replicas: 5
      max_replicas: 100
      
    voice_service:
      min_replicas: 5
      max_replicas: 50
      
    vision_service:
      min_replicas: 3
      max_replicas: 20
```

### 8.2 Database Scaling

```yaml
PostgreSQL:
  read_replicas: 3
  connection_pooling: "PgBouncer"
  sharding: false
  
MongoDB:
  sharding: true
  replica_sets: 3
  read_preference: "secondaryPreferred"
  
Redis:
  clustering: true
  sentinel: true
  partitioning: "hash"
  
Qdrant:
  sharding: true
  replication_factor: 2
  
Neo4j:
  causal_clustering: true
  read_replicas: 2
```

### 8.3 Caching Strategy

```yaml
Cache Layers:
  L1: "In-memory cache (Python dicts)"
  L2: "Redis (distributed cache)"
  L3: "CDN (CloudFront)"
  
Cache Invalidation:
  strategy: "TTL + Event-based"
  ttl:
    short: "5 minutes"
    medium: "1 hour"
    long: "24 hours"
  
Cache Patterns:
  - cache_aside
  - write_through
  - write_behind
  - refresh_ahead
```

### 8.4 Load Balancing

```yaml
Load Balancer:
  type: "Application Load Balancer"
  algorithm: "Round Robin"
  health_check:
    path: "/health"
    interval: "30 seconds"
    timeout: "5 seconds"
    healthy_threshold: 2
    unhealthy_threshold: 3
  
  sticky_sessions:
    enabled: true
    duration: "1 hour"
```

---

## 9. Monitoring & Observability

### 9.1 Metrics Collection

```yaml
Prometheus Metrics:
  service_metrics:
    - request_count
    - request_duration
    - error_rate
    - active_connections
    - queue_length
  
  business_metrics:
    - daily_active_users
    - conversation_count
    - session_duration
    - memory_storage_count
  
  infrastructure_metrics:
    - cpu_usage
    - memory_usage
    - disk_usage
    - network_io
    - gpu_usage
```

### 9.2 Logging Strategy

```yaml
Log Levels:
  - ERROR
  - WARN
  - INFO
  - DEBUG
  
Log Format:
  type: "JSON"
  fields:
    - timestamp
    - level
    - service
    - trace_id
    - user_id
    - message
    - context
    
Log Retention:
  - ERROR: 90 days
  - WARN: 30 days
  - INFO: 7 days
  - DEBUG: 1 day
```

### 9.3 Distributed Tracing

```yaml
Tracing:
  tool: "Jaeger"
  sampling_rate: "10%"
  
Span Types:
  - http
  - database
  - cache
  - messaging
  - external_api
  
Trace Context:
  format: "W3C Trace Context"
  propagation: "HTTP headers"
```

---

## 10. Disaster Recovery

### 10.1 Backup Strategy

```yaml
Backups:
  database:
    type: "Snapshot + WAL"
    frequency: "Every 6 hours"
    retention: "30 days"
    destination: "S3 Glacier"
  
  assets:
    type: "Versioning + Cross-region replication"
    frequency: "Real-time"
    retention: "Forever"
  
  configuration:
    type: "Git repository"
    frequency: "On change"
    retention: "Forever"
```

### 10.2 High Availability

```yaml
HA Architecture:
  multi_az: true
  regions: 2
  failover:
    rto: "5 minutes"
    rpo: "1 minute"
    
  dr_plan:
    frequency: "Monthly test"
    documentation: "Confluence"
```

---

## 11. Cost Optimization

### 11.1 Resource Optimization

```yaml
Compute:
  right_sizing: true
  spot_instances: true (for non-critical workloads)
  autoscaling: true
  
Storage:
  lifecycle_policies: true
  compression: true
  deduplication: true
  
Network:
    data_transfer: true
    caching: true
```

### 11.2 Cost Monitoring

```yaml
Cost Alerts:
  threshold: "$10,000/month"
  frequency: "Daily"
  
Cost Allocation:
  tags:
    - environment
    - service
    - team
    
  reports: "Monthly"
```

---

## Conclusion

Đây là kiến trúc tổng thể cho hệ thống AI Companion với:
- **17 microservices** được tổ chức theo chức năng
- **6 loại database** khác nhau cho các use case khác nhau
- **Multi-layer security** với authentication, authorization, encryption
- **Horizontal scaling** với Kubernetes auto-scaling
- **Comprehensive monitoring** với Prometheus, Grafana, ELK
- **Disaster recovery** với backup và HA strategy

Kiến trúc này được thiết kế để:
- Hỗ trợ **10,000 concurrent users**
- Đảm bảo **99.9% uptime**
- Giữ latency **< 100ms**
- Scale horizontal theo nhu cầu
- Tuân thủ các standard security (GDPR, SOC2)
