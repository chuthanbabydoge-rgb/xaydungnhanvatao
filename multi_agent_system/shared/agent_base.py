"""
Base Agent Framework - Core agent architecture
Provides foundation for all agents in the multi-agent system
"""
import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
import aio_pika
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import Counter, Histogram, Gauge, start_http_server


class AgentStatus(Enum):
    """Agent status states"""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class MessageType(Enum):
    """Message types for agent communication"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    EVENT = "event"
    QUERY = "query"
    RESPONSE = "response"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    STATUS_UPDATE = "status_update"


@dataclass
class AgentMessage:
    """Standard message format for agent communication"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: str = ""
    message_type: MessageType = MessageType.EVENT
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    priority: int = 5  # 1-10, 10 being highest
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "priority": self.priority,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            sender_id=data.get("sender_id", ""),
            receiver_id=data.get("receiver_id", ""),
            message_type=MessageType(data.get("message_type", "event")),
            content=data.get("content", {}),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            priority=data.get("priority", 5),
            metadata=data.get("metadata", {})
        )


class BaseAgent(ABC):
    """
    Base agent class that all agents inherit from
    Provides common functionality for message handling, lifecycle management, monitoring
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        enable_tracing: bool = True,
        enable_metrics: bool = True,
        metrics_port: int = 9090
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.rabbitmq_url = rabbitmq_url
        self.enable_tracing = enable_tracing
        self.enable_metrics = enable_metrics
        self.metrics_port = metrics_port
        
        self.status = AgentStatus.STARTING
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchanges: Dict[str, aio_pika.Exchange] = {}
        self.queues: Dict[str, aio_pika.Queue] = {}
        
        # Message handlers
        self.message_handlers: Dict[MessageType, Callable] = {}
        
        # Metrics
        self.setup_metrics()
        
        # Tracing
        self.setup_tracing()
        
        # Logger
        self.logger = logging.getLogger(f"agent.{agent_type}.{agent_id}")
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
    
    def setup_metrics(self):
        """Setup Prometheus metrics"""
        if not self.enable_metrics:
            return
        
        self.message_counter = Counter(
            f'agent_{self.agent_type}_messages_total',
            'Total messages processed',
            ['message_type', 'status']
        )
        
        self.processing_time = Histogram(
            f'agent_{self.agent_type}_processing_seconds',
            'Message processing time',
            ['message_type']
        )
        
        self.active_tasks = Gauge(
            f'agent_{self.agent_type}_active_tasks',
            'Number of active tasks'
        )
        
        self.error_counter = Counter(
            f'agent_{self.agent_type}_errors_total',
            'Total errors',
            ['error_type']
        )
    
    def setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        if not self.enable_tracing:
            return
        
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()
        
        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        self.tracer = trace.get_tracer(__name__)
    
    async def start(self):
        """Start the agent"""
        self.logger.info(f"Starting {self.agent_type} agent {self.agent_id}")
        
        try:
            # Start metrics server if enabled
            if self.enable_metrics:
                start_http_server(self.metrics_port)
                self.logger.info(f"Metrics server started on port {self.metrics_port}")
            
            # Connect to RabbitMQ
            await self.connect_to_bus()
            
            # Setup exchanges and queues
            await self.setup_message_infrastructure()
            
            # Register message handlers
            self.register_handlers()
            
            # Start background tasks
            await self.start_background_tasks()
            
            # Start consuming messages
            consume_task = asyncio.create_task(self.consume_messages())
            self.background_tasks.append(consume_task)
            
            self.status = AgentStatus.RUNNING
            self.logger.info(f"{self.agent_type} agent {self.agent_id} started successfully")
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to start agent: {e}")
            raise
    
    async def stop(self):
        """Stop the agent"""
        self.logger.info(f"Stopping {self.agent_type} agent {self.agent_id}")
        self.status = AgentStatus.STOPPING
        
        try:
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            # Close connection
            if self.connection:
                await self.connection.close()
            
            self.status = AgentStatus.STOPPED
            self.logger.info(f"{self.agent_type} agent {self.agent_id} stopped successfully")
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Error stopping agent: {e}")
    
    async def connect_to_bus(self):
        """Connect to RabbitMQ message bus"""
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        
        # Set prefetch count
        await self.channel.set_qos(prefetch_count=10)
        
        self.logger.info("Connected to RabbitMQ message bus")
    
    async def setup_message_infrastructure(self):
        """Setup exchanges and queues"""
        # Main exchange for agent communication
        self.exchanges["main"] = await self.channel.declare_exchange(
            "agent_bus",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        # Agent-specific queue
        queue_name = f"{self.agent_type}.{self.agent_id}"
        self.queues["inbox"] = await self.channel.declare_queue(
            queue_name,
            durable=True,
            arguments={"x-max-length": 1000}
        )
        
        # Bind queue to exchange
        await self.queues["inbox"].bind(
            self.exchanges["main"],
            routing_key=f"{self.agent_type}.{self.agent_id}"
        )
        
        # Also bind to agent type for broadcast
        await self.queues["inbox"].bind(
            self.exchanges["main"],
            routing_key=f"{self.agent_type}.*"
        )
        
        self.logger.info("Message infrastructure setup complete")
    
    @abstractmethod
    def register_handlers(self):
        """Register message handlers - must be implemented by subclasses"""
        pass
    
    async def start_background_tasks(self):
        """Start background tasks"""
        # Heartbeat task
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        self.background_tasks.append(heartbeat_task)
    
    async def heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        while self.status == AgentStatus.RUNNING:
            try:
                heartbeat = AgentMessage(
                    sender_id=self.agent_id,
                    message_type=MessageType.HEARTBEAT,
                    content={
                        "status": self.status.value,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                await self.publish_message(
                    heartbeat,
                    routing_key=f"{self.agent_type}.{self.agent_id}.heartbeat"
                )
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(30)
    
    async def publish_message(
        self,
        message: AgentMessage,
        routing_key: str,
        exchange: str = "main"
    ):
        """Publish a message to the bus"""
        if exchange not in self.exchanges:
            self.logger.error(f"Exchange {exchange} not found")
            return
        
        try:
            message.sender_id = self.agent_id
            
            await self.exchanges[exchange].publish(
                aio_pika.Message(
                    body=json.dumps(message.to_dict()).encode(),
                    content_type="application/json",
                    priority=message.priority,
                    correlation_id=message.correlation_id,
                    reply_to=message.reply_to
                ),
                routing_key=routing_key
            )
            
            self.message_counter.labels(
                message_type=message.message_type.value,
                status="published"
            ).inc()
            
        except Exception as e:
            self.logger.error(f"Failed to publish message: {e}")
            self.error_counter.labels(error_type="publish").inc()
    
    async def consume_messages(self):
        """Start consuming messages from the inbox queue"""
        async with self.queues["inbox"].iterator() as queue_iterator:
            async for message in queue_iterator:
                async with message.process():
                    try:
                        # Parse message
                        data = json.loads(message.body.decode())
                        agent_message = AgentMessage.from_dict(data)
                        
                        # Process message
                        await self.process_message(agent_message)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}")
                        self.error_counter.labels(error_type="process").inc()
    
    async def process_message(self, message: AgentMessage):
        """Process incoming message"""
        with self.processing_time.labels(
            message_type=message.message_type.value
        ).time():
            
            # Get handler for message type
            handler = self.message_handlers.get(message.message_type)
            
            if handler:
                try:
                    response = await handler(message)
                    
                    # Send response if needed
                    if message.reply_to and response:
                        response_message = AgentMessage(
                            sender_id=self.agent_id,
                            receiver_id=message.sender_id,
                            message_type=MessageType.RESPONSE,
                            content=response,
                            correlation_id=message.correlation_id
                        )
                        
                        await self.publish_message(
                            response_message,
                            routing_key=message.reply_to
                        )
                    
                    self.message_counter.labels(
                        message_type=message.message_type.value,
                        status="processed"
                    ).inc()
                    
                except Exception as e:
                    self.logger.error(f"Handler error: {e}")
                    self.error_counter.labels(error_type="handler").inc()
                    
                    # Send error response
                    if message.reply_to:
                        error_message = AgentMessage(
                            sender_id=self.agent_id,
                            receiver_id=message.sender_id,
                            message_type=MessageType.ERROR,
                            content={"error": str(e)},
                            correlation_id=message.correlation_id
                        )
                        
                        await self.publish_message(
                            error_message,
                            routing_key=message.reply_to
                        )
            else:
                self.logger.warning(f"No handler for message type: {message.message_type}")
    
    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task - must be implemented by subclasses"""
        pass
    
    async def send_task_request(
        self,
        target_agent: str,
        task: Dict[str, Any],
        priority: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Send a task request to another agent"""
        correlation_id = str(uuid.uuid4())
        reply_queue = f"reply.{self.agent_id}.{correlation_id}"
        
        # Create temporary reply queue
        reply_queue_obj = await self.channel.declare_queue(
            reply_queue,
            exclusive=True,
            auto_delete=True
        )
        
        # Create task request message
        task_message = AgentMessage(
            sender_id=self.agent_id,
            receiver_id=target_agent,
            message_type=MessageType.TASK_REQUEST,
            content=task,
            correlation_id=correlation_id,
            reply_to=reply_queue,
            priority=priority
        )
        
        # Send task request
        await self.publish_message(
            task_message,
            routing_key=f"{target_agent}"
        )
        
        # Wait for response
        future = asyncio.Future()
        
        async def wait_for_response():
            async with reply_queue_obj.iterator() as queue_iterator:
                async for message in queue_iterator:
                    async with message.process():
                        data = json.loads(message.body.decode())
                        response = AgentMessage.from_dict(data)
                        
                        if response.correlation_id == correlation_id:
                            future.set_result(response.content)
                            break
        
        # Start waiting for response
        response_task = asyncio.create_task(wait_for_response())
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            self.logger.error(f"Task request to {target_agent} timed out")
            return None
        finally:
            response_task.cancel()
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "timestamp": datetime.utcnow().isoformat()
        }