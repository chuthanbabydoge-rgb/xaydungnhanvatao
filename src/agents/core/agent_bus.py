"""
Agent Bus - RabbitMQ-based message bus for multi-agent communication
Handles message routing, exchanges, queues, and advanced messaging features
"""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import aio_pika
from aio_pika import ExchangeType, Message, Queue
from aio_pika.patterns import RPC


class ExchangeType(Enum):
    """Exchange types"""
    DIRECT = "direct"
    TOPIC = "topic"
    FANOUT = "fanout"
    HEADERS = "headers"


class QueueConfig(Enum):
    """Queue configuration presets"""
    DEFAULT = "default"
    DURABLE = "durable"
    AUTO_DELETE = "auto_delete"
    EXCLUSIVE = "exclusive"
    DLQ = "dead_letter_queue"


@dataclass
class ExchangeConfig:
    """Exchange configuration"""
    name: str
    type: ExchangeType = ExchangeType.TOPIC
    durable: bool = True
    auto_delete: bool = False
    arguments: Dict[str, Any] = None


@dataclass
class QueueBinding:
    """Queue binding configuration"""
    queue_name: str
    exchange_name: str
    routing_key: str
    arguments: Dict[str, Any] = None


class AgentBus:
    """
    Agent Bus - Central message bus for agent communication
    Provides high-level messaging abstractions over RabbitMQ
    """
    
    def __init__(
        self,
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        connection_name: str = "agent_bus"
    ):
        self.rabbitmq_url = rabbitmq_url
        self.connection_name = connection_name
        
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        
        self.exchanges: Dict[str, aio_pika.Exchange] = {}
        self.queues: Dict[str, aio_pika.Queue] = {}
        self.rpc_clients: Dict[str, RPC] = {}
        
        self.logger = logging.getLogger("agent_bus")
        
        # Message callbacks
        self.message_callbacks: Dict[str, Callable] = {}
    
    async def connect(self):
        """Connect to RabbitMQ"""
        self.connection = await aio_pika.connect_robust(
            self.rabbitmq_url,
            client_name=self.connection_name
        )
        self.channel = await self.connection.channel()
        
        # Set QoS
        await self.channel.set_qos(prefetch_count=100)
        
        self.logger.info(f"Connected to RabbitMQ as {self.connection_name}")
    
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection:
            await self.connection.close()
            self.logger.info("Disconnected from RabbitMQ")
    
    async def declare_exchange(self, config: ExchangeConfig) -> aio_pika.Exchange:
        """Declare an exchange"""
        exchange = await self.channel.declare_exchange(
            config.name,
            config.type.value,
            durable=config.durable,
            auto_delete=config.auto_delete,
            arguments=config.arguments or {}
        )
        
        self.exchanges[config.name] = exchange
        self.logger.info(f"Declared exchange: {config.name}")
        
        return exchange
    
    async def declare_queue(
        self,
        name: str,
        config: QueueConfig = QueueConfig.DEFAULT,
        arguments: Dict[str, Any] = None
    ) -> aio_pika.Queue:
        """Declare a queue"""
        args = arguments or {}
        
        # Apply configuration preset
        if config == QueueConfig.DURABLE:
            args.setdefault("x-durable", True)
        elif config == QueueConfig.AUTO_DELETE:
            args.setdefault("x-auto-delete", True)
        elif config == QueueConfig.EXCLUSIVE:
            args.setdefault("x-exclusive", True)
        elif config == QueueConfig.DLQ:
            args.setdefault("x-dead-letter-exchange", "dlx")
            args.setdefault("x-dead-letter-routing-key", name)
        
        queue = await self.channel.declare_queue(
            name,
            durable=(config != QueueConfig.AUTO_DELETE and config != QueueConfig.EXCLUSIVE),
            exclusive=(config == QueueConfig.EXCLUSIVE),
            auto_delete=(config == QueueConfig.AUTO_DELETE),
            arguments=args
        )
        
        self.queues[name] = queue
        self.logger.info(f"Declared queue: {name}")
        
        return queue
    
    async def bind_queue(self, binding: QueueBinding):
        """Bind a queue to an exchange"""
        if binding.queue_name not in self.queues:
            await self.declare_queue(binding.queue_name)
        
        if binding.exchange_name not in self.exchanges:
            await self.declare_exchange(ExchangeConfig(binding.exchange_name))
        
        await self.queues[binding.queue_name].bind(
            self.exchanges[binding.exchange_name],
            routing_key=binding.routing_key,
            arguments=binding.arguments or {}
        )
        
        self.logger.info(f"Bound queue {binding.queue_name} to {binding.exchange_name} with {binding.routing_key}")
    
    async def publish_message(
        self,
        exchange_name: str,
        routing_key: str,
        message: Dict[str, Any],
        priority: int = 5,
        correlation_id: str = None,
        reply_to: str = None,
        expiration: int = None,
        headers: Dict[str, Any] = None
    ):
        """Publish a message to an exchange"""
        if exchange_name not in self.exchanges:
            self.logger.error(f"Exchange {exchange_name} not found")
            return
        
        message_body = Message(
            body=json.dumps(message).encode(),
            content_type="application/json",
            priority=priority,
            correlation_id=correlation_id,
            reply_to=reply_to,
            expiration=expiration,
            headers=headers or {}
        )
        
        await self.exchanges[exchange_name].publish(
            message_body,
            routing_key=routing_key
        )
        
        self.logger.debug(f"Published message to {exchange_name} with routing key {routing_key}")
    
    async def consume_messages(
        self,
        queue_name: str,
        callback: Callable,
        auto_ack: bool = False
    ):
        """Consume messages from a queue"""
        if queue_name not in self.queues:
            self.logger.error(f"Queue {queue_name} not found")
            return
        
        async with self.queues[queue_name].iterator(no_ack=auto_ack) as queue_iterator:
            async for message in queue_iterator:
                try:
                    await callback(message)
                    if not auto_ack:
                        message.ack()
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    if not auto_ack:
                        message.nack(requeue=False)
    
    async def setup_rpc(self, exchange_name: str, queue_name: str) -> RPC:
        """Setup RPC client"""
        if exchange_name not in self.exchanges:
            await self.declare_exchange(ExchangeConfig(exchange_name))
        
        if queue_name not in self.queues:
            await self.declare_queue(queue_name)
        
        rpc = await RPC.create(self.channel)
        self.rpc_clients[queue_name] = rpc
        
        self.logger.info(f"Setup RPC for {queue_name}")
        return rpc
    
    async def rpc_call(
        self,
        exchange_name: str,
        routing_key: str,
        message: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """Make an RPC call"""
        if exchange_name not in self.rpc_clients:
            await self.setup_rpc(exchange_name, routing_key)
        
        rpc = self.rpc_clients[exchange_name]
        
        try:
            response = await asyncio.wait_for(
                rpc.call(
                    exchange_name,
                    routing_key,
                    json.dumps(message).encode()
                ),
                timeout=timeout
            )
            
            return json.loads(response.decode())
        except asyncio.TimeoutError:
            self.logger.error(f"RPC call to {routing_key} timed out")
            return None
        except Exception as e:
            self.logger.error(f"RPC call error: {e}")
            return None
    
    async def setup_dead_letter_exchange(self):
        """Setup dead letter exchange and queue"""
        # Declare dead letter exchange
        dlx = await self.declare_exchange(ExchangeConfig(
            name="dlx",
            type=ExchangeType.FANOUT
        ))
        
        # Declare dead letter queue
        dlq = await self.declare_queue(
            "dead_letter_queue",
            config=QueueConfig.DURABLE
        )
        
        # Bind DLQ to DLX
        await dlq.bind(dlx, "")
        
        self.logger.info("Setup dead letter exchange and queue")
    
    async def setup_standard_infrastructure(self):
        """Setup standard messaging infrastructure"""
        # Main exchange
        await self.declare_exchange(ExchangeConfig(
            name="agent_bus",
            type=ExchangeType.TOPIC
        ))
        
        # Dead letter infrastructure
        await self.setup_dead_letter_exchange()
        
        # Task exchange
        await self.declare_exchange(ExchangeConfig(
            name="task_exchange",
            type=ExchangeType.DIRECT
        ))
        
        # Event exchange
        await self.declare_exchange(ExchangeConfig(
            name="event_exchange",
            type=ExchangeType.FANOUT
        ))
        
        self.logger.info("Setup standard messaging infrastructure")
    
    async def create_agent_queue(
        self,
        agent_type: str,
        agent_id: str,
        with_dlq: bool = True
    ) -> str:
        """Create queue for an agent"""
        queue_name = f"{agent_type}.{agent_id}"
        
        arguments = {}
        if with_dlq:
            arguments["x-dead-letter-exchange"] = "dlx"
            arguments["x-dead-letter-routing-key"] = queue_name
        
        await self.declare_queue(
            queue_name,
            arguments=arguments
        )
        
        # Bind to main exchange
        await self.bind_queue(QueueBinding(
            queue_name=queue_name,
            exchange_name="agent_bus",
            routing_key=f"{agent_type}.{agent_id}"
        ))
        
        # Also bind to agent type for broadcast
        await self.bind_queue(QueueBinding(
            queue_name=queue_name,
            exchange_name="agent_bus",
            routing_key=f"{agent_type}.*"
        ))
        
        return queue_name
    
    async def send_to_agent(
        self,
        agent_type: str,
        agent_id: str,
        message: Dict[str, Any],
        priority: int = 5
    ):
        """Send message to specific agent"""
        await self.publish_message(
            "agent_bus",
            f"{agent_type}.{agent_id}",
            message,
            priority=priority
        )
    
    async def broadcast_to_type(
        self,
        agent_type: str,
        message: Dict[str, Any],
        priority: int = 5
    ):
        """Broadcast message to all agents of a type"""
        await self.publish_message(
            "agent_bus",
            f"{agent_type}.*",
            message,
            priority=priority
        )
    
    async def broadcast_to_all(
        self,
        message: Dict[str, Any],
        priority: int = 5
    ):
        """Broadcast message to all agents"""
        await self.publish_message(
            "event_exchange",
            "",
            message,
            priority=priority
        )
    
    async def publish_task(
        self,
        task_type: str,
        task: Dict[str, Any],
        priority: int = 5
    ):
        """Publish a task to the task exchange"""
        await self.publish_message(
            "task_exchange",
            task_type,
            task,
            priority=priority
        )
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            "connected": self.connection is not None and not self.connection.is_closed,
            "exchanges": list(self.exchanges.keys()),
            "queues": list(self.queues.keys()),
            "rpc_clients": list(self.rpc_clients.keys())
        }