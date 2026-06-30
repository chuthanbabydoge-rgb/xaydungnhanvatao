# Multi-Agent System

A distributed multi-agent system with independent agents communicating via RabbitMQ message bus.

## Architecture

### Components

- **Agent Bus**: RabbitMQ-based message bus for inter-agent communication
- **Planner Agent**: Task planning and coordination
- **Research Agent**: Information gathering and analysis
- **Coder Agent**: Code generation and analysis
- **Memory Agent**: Memory management and retrieval
- **Emotion Agent**: Emotional processing and state management
- **Scheduler Agent**: Task scheduling and execution
- **Vision Agent**: Visual processing and analysis
- **Plugin Agent**: Plugin management and execution

### Features

- **Event-Driven**: Asynchronous communication via RabbitMQ
- **Independent Agents**: Each agent runs as a separate service
- **Tracing**: OpenTelemetry distributed tracing
- **Metrics**: Prometheus metrics collection
- **Scalable**: Horizontal scaling support
- **Fault-Tolerant**: Retry mechanisms and dead letter queues

## Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check agent status
curl http://localhost:8080/health
```

## Configuration

Each agent can be configured via environment variables or config files.

```yaml
agent:
  id: "planner-agent-1"
  type: "planner"
  bus:
    host: "rabbitmq"
    port: 5672
    username: "guest"
    password: "guest"
  tracing:
    enabled: true
    endpoint: "http://jaeger:14268/api/traces"
  metrics:
    enabled: true
    port: 9090
```

## Development

See individual agent directories for specific implementation details.