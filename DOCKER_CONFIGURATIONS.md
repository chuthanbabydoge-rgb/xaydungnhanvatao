# DOCKER CONFIGURATIONS

## Overview

Docker configurations for all 40 services in the AI Companion platform.

---

## 1. Backend Services

### Auth Service

```dockerfile
# docker/auth-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### LLM Service

```dockerfile
# docker/llm-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Voice Service

```dockerfile
# docker/voice-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8002

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
```

### Vision Service

```dockerfile
# docker/vision-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8003

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
```

### Memory Service

```dockerfile
# docker/memory-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8004

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
```

### Agent Service

```dockerfile
# docker/agent-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8005

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
```

### Personality Service

```dockerfile
# docker/personality-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8006

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006"]
```

### World Service

```dockerfile
# docker/world-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8007

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007"]
```

---

## 2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Databases
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ai_companion
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  mongodb:
    image: mongo:7
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USERNAME}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
    volumes:
      - mongodb_data:/data/db
    ports:
      - "27017:27017"
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
  
  qdrant:
    image: qdrant/qdrant:v1.7.0
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
  
  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    volumes:
      - neo4j_data:/data
    ports:
      - "7474:7474"
      - "7687:7687"
  
  # Message Queue
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
  
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    ports:
      - "2181:2181"
  
  # Backend Services
  auth-service:
    build: ./docker/auth-service
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ai_companion
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"
  
  llm-service:
    build: ./docker/llm-service
    environment:
      REDIS_URL: redis://redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on:
      - redis
    ports:
      - "8001:8001"
  
  voice-service:
    build: ./docker/voice-service
    environment:
      REDIS_URL: redis://redis:6379
      DEEPGRAM_API_KEY: ${DEEPGRAM_API_KEY}
      ELEVENLABS_API_KEY: ${ELEVENLABS_API_KEY}
    depends_on:
      - redis
    ports:
      - "8002:8002"
  
  vision-service:
    build: ./docker/vision-service
    environment:
      REDIS_URL: redis://redis:6379
    depends_on:
      - redis
    ports:
      - "8003:8003"
  
  memory-service:
    build: ./docker/memory-service
    environment:
      QDRANT_URL: http://qdrant:6333
      NEO4J_URL: bolt://neo4j:7687
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
    depends_on:
      - qdrant
      - neo4j
    ports:
      - "8004:8004"
  
  agent-service:
    build: ./docker/agent-service
    environment:
      REDIS_URL: redis://redis:6379
      MONGODB_URL: mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@mongodb:27017
    depends_on:
      - redis
      - mongodb
    ports:
      - "8005:8005"
  
  personality-service:
    build: ./docker/personality-service
    environment:
      MONGODB_URL: mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@mongodb:27017
    depends_on:
      - mongodb
    ports:
      - "8006:8006"
  
  world-service:
    build: ./docker/world-service
    environment:
      REDIS_URL: redis://redis:6379
    depends_on:
      - redis
    ports:
      - "8007:8007"
  
  # API Gateway
  api-gateway:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on:
      - auth-service
      - llm-service
      - voice-service
      - vision-service
      - memory-service
      - agent-service
      - personality-service
      - world-service

volumes:
  postgres_data:
  mongodb_data:
  redis_data:
  qdrant_data:
  neo4j_data:
```

---

## 3. Requirements Files

### Common Requirements

```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
redis==5.0.1
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
pymongo==4.6.0
qdrant-client==1.7.0
neo4j==5.14.0
kafka-python==2.0.2
celery==5.3.4
prometheus-client==0.19.0
structlog==23.2.0
httpx==0.25.2
websockets==12.0
```

### LLM Service Requirements

```txt
# llm-service/requirements.txt
openai==1.3.7
anthropic==0.7.8
google-generativeai==0.3.0
langchain==0.0.335
langchain-openai==0.0.2
langchain-anthropic==0.0.1
tiktoken==0.5.2
```

### Voice Service Requirements

```txt
# voice-service/requirements.txt
deepgram-sdk==3.2.2
elevenlabs==0.2.26
openai-whisper==20231117
pydub==0.25.1
soundfile==0.12.1
```

### Vision Service Requirements

```txt
# vision-service/requirements.txt
opencv-python==4.8.1.78
mediapipe==0.10.8
ultralytics==8.0.236
segment-anything-2==1.0
torch==2.1.1
torchvision==0.16.1
numpy==1.26.2
```

---

## 4. Build and Run

```bash
# Build all services
docker-compose build

# Run all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## 5. Multi-stage Build (Optimized)

```dockerfile
# Optimized Dockerfile with multi-stage build
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Conclusion

Docker configurations enable:
- **Containerized deployment** for all services
- **Consistent environments** across development, staging, production
- **Easy scaling** with Docker Compose or Kubernetes
- **Isolated dependencies** for each service
- **Fast deployment** with pre-built images
