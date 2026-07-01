"""
Prometheus Metrics Configuration
Centralized metrics setup for all agents using Prometheus
"""
import logging
from typing import Optional, Dict, Any

try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, start_http_server
    from prometheus_client import CONTENT_TYPE_LATEST
    from prometheus_client.openmetrics.exposition import generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class MetricsConfig:
    """Centralized metrics configuration"""
    
    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        metrics_port: int = 9090,
        enable_server: bool = True
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.metrics_port = metrics_port
        self.enable_server = enable_server
        
        # Check if Prometheus is available
        if not PROMETHEUS_AVAILABLE:
            self.logger = logging.getLogger("metrics")
            self.logger.warning("Prometheus client not available, metrics disabled")
            self.registry = None
            return
        
        # Create custom registry for this service
        self.registry = CollectorRegistry()
        
        # Common metrics
        self.setup_common_metrics()
        
        self.logger = logging.getLogger("metrics")
    
    def setup_common_metrics(self):
        """Setup common metrics for all agents"""
        if not PROMETHEUS_AVAILABLE:
            return
            
        # Message processing metrics
        self.message_counter = Counter(
            f'{self.service_name}_messages_total',
            'Total messages processed',
            ['message_type', 'status'],
            registry=self.registry
        )
        
        self.message_processing_time = Histogram(
            f'{self.service_name}_message_processing_seconds',
            'Message processing time in seconds',
            ['message_type'],
            registry=self.registry
        )
        
        # Task execution metrics
        self.task_counter = Counter(
            f'{self.service_name}_tasks_total',
            'Total tasks executed',
            ['task_type', 'status'],
            registry=self.registry
        )
        
        self.task_execution_time = Histogram(
            f'{self.service_name}_task_execution_seconds',
            'Task execution time in seconds',
            ['task_type'],
            registry=self.registry
        )
        
        # Error metrics
        self.error_counter = Counter(
            f'{self.service_name}_errors_total',
            'Total errors',
            ['error_type', 'severity'],
            registry=self.registry
        )
        
        # Active connections/operations
        self.active_operations = Gauge(
            f'{self.service_name}_active_operations',
            'Number of currently active operations',
            registry=self.registry
        )
        
        # Memory usage
        self.memory_usage = Gauge(
            f'{self.service_name}_memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
        
        # Agent health
        self.agent_health = Gauge(
            f'{self.service_name}_health',
            'Agent health status (1=healthy, 0=unhealthy)',
            registry=self.registry
        )
        
        self.logger.info(f"Common metrics setup for {self.service_name}")
    
    def setup_custom_metrics(self, metrics_config: Dict[str, Any]):
        """Setup custom metrics based on configuration"""
        if not PROMETHEUS_AVAILABLE:
            return
            
        for metric_name, metric_config in metrics_config.items():
            metric_type = metric_config.get("type")
            labels = metric_config.get("labels", [])
            description = metric_config.get("description", "")
            
            if metric_type == "counter":
                counter = Counter(
                    f'{self.service_name}_{metric_name}',
                    description,
                    labels,
                    registry=self.registry
                )
                setattr(self, metric_name, counter)
            
            elif metric_type == "histogram":
                histogram = Histogram(
                    f'{self.service_name}_{metric_name}',
                    description,
                    labels,
                    registry=self.registry
                )
                setattr(self, metric_name, histogram)
            
            elif metric_type == "gauge":
                gauge = Gauge(
                    f'{self.service_name}_{metric_name}',
                    description,
                    labels,
                    registry=self.registry
                )
                setattr(self, metric_name, gauge)
        
        self.logger.info(f"Custom metrics setup for {self.service_name}")
    
    async def start_metrics_server(self):
        """Start the Prometheus metrics HTTP server"""
        if not PROMETHEUS_AVAILABLE or not self.enable_server:
            return
            
        try:
            start_http_server(self.metrics_port, registry=self.registry)
            self.logger.info(f"Prometheus metrics server started on port {self.metrics_port}")
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}")
    
    def increment_message_counter(self, message_type: str, status: str = "processed"):
        """Increment message counter"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'message_counter'):
            self.message_counter.labels(message_type=message_type, status=status).inc()
    
    def observe_message_processing_time(self, message_type: str, duration: float):
        """Observe message processing time"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'message_processing_time'):
            self.message_processing_time.labels(message_type=message_type).observe(duration)
    
    def increment_task_counter(self, task_type: str, status: str = "completed"):
        """Increment task counter"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'task_counter'):
            self.task_counter.labels(task_type=task_type, status=status).inc()
    
    def observe_task_execution_time(self, task_type: str, duration: float):
        """Observe task execution time"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'task_execution_time'):
            self.task_execution_time.labels(task_type=task_type).observe(duration)
    
    def increment_error_counter(self, error_type: str, severity: str = "error"):
        """Increment error counter"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'error_counter'):
            self.error_counter.labels(error_type=error_type, severity=severity).inc()
    
    def set_active_operations(self, count: int):
        """Set active operations count"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'active_operations'):
            self.active_operations.set(count)
    
    def set_memory_usage(self, bytes_used: int):
        """Set memory usage"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'memory_usage'):
            self.memory_usage.set(bytes_used)
    
    def set_agent_health(self, healthy: bool):
        """Set agent health status"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'agent_health'):
            self.agent_health.set(1 if healthy else 0)
    
    def get_metrics(self) -> str:
        """Get current metrics in Prometheus format"""
        if PROMETHEUS_AVAILABLE and self.registry:
            return generate_latest(self.registry)
        return ""


class AgentMetrics:
    """Helper class for agent-specific metrics"""
    
    def __init__(self, agent_id: str, agent_type: str, metrics_port: int = 9090):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = MetricsConfig(
            service_name=f"{agent_type}-agent",
            metrics_port=metrics_port
        )
        
        # Agent-specific metrics
        if PROMETHEUS_AVAILABLE and self.config.registry:
            self.setup_agent_metrics()
    
    def setup_agent_metrics(self):
        """Setup agent-specific metrics"""
        if not PROMETHEUS_AVAILABLE or not self.config.registry:
            return
            
        # Agent communication metrics
        self.messages_sent = self.config.registry.get_or_create_counter(
            f'{self.config.service_name}_messages_sent_total',
            'Total messages sent',
            ['target_agent_type']
        )
        
        self.messages_received = self.config.registry.get_or_create_counter(
            f'{self.config.service_name}_messages_received_total',
            'Total messages received',
            ['source_agent_type']
        )
        
        # Task queue metrics
        self.queue_size = self.config.registry.get_or_create_gauge(
            f'{self.config.service_name}_queue_size',
            'Current task queue size'
        )
        
        self.queue_wait_time = self.config.registry.get_or_create_histogram(
            f'{self.config.service_name}_queue_wait_seconds',
            'Time tasks spend in queue'
        )
        
        # Resource utilization
        self.cpu_usage = self.config.registry.get_or_create_gauge(
            f'{self.config.service_name}_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        self.disk_usage = self.config.registry.get_or_create_gauge(
            f'{self.config.service_name}_disk_usage_bytes',
            'Disk usage in bytes'
        )
        
        # Performance metrics
        self.response_time = self.config.registry.get_or_create_histogram(
            f'{self.config.service_name}_response_seconds',
            'Response time in seconds',
            ['operation_type']
        )
        
        self.throughput = self.config.registry.get_or_create_gauge(
            f'{self.config.service_name}_throughput_per_second',
            'Operations per second'
        )
    
    def record_message_sent(self, target_agent_type: str):
        """Record a sent message"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'messages_sent'):
            self.config.message_counter.labels(
                message_type="outbound",
                status="sent"
            ).inc()
            self.messages_sent.labels(target_agent_type=target_agent_type).inc()
    
    def record_message_received(self, source_agent_type: str):
        """Record a received message"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'messages_received'):
            self.config.message_counter.labels(
                message_type="inbound",
                status="received"
            ).inc()
            self.messages_received.labels(source_agent_type=source_agent_type).inc()
    
    def update_queue_size(self, size: int):
        """Update queue size metric"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'queue_size'):
            self.queue_size.set(size)
    
    def record_queue_wait_time(self, duration: float):
        """Record queue wait time"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'queue_wait_time'):
            self.queue_wait_time.observe(duration)
    
    def update_cpu_usage(self, usage_percent: float):
        """Update CPU usage metric"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'cpu_usage'):
            self.cpu_usage.set(usage_percent)
    
    def update_disk_usage(self, bytes_used: int):
        """Update disk usage metric"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'disk_usage'):
            self.disk_usage.set(bytes_used)
    
    def record_response_time(self, operation_type: str, duration: float):
        """Record response time"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'response_time'):
            self.response_time.labels(operation_type=operation_type).observe(duration)
    
    def update_throughput(self, operations_per_second: float):
        """Update throughput metric"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'throughput'):
            self.throughput.set(operations_per_second)
    
    async def start_server(self):
        """Start the metrics server"""
        await self.config.start_metrics_server()
    
    def get_metrics(self) -> str:
        """Get current metrics"""
        return self.config.get_metrics()


def setup_agent_metrics(agent_id: str, agent_type: str, metrics_port: int = 9090) -> AgentMetrics:
    """Setup metrics for an agent"""
    return AgentMetrics(agent_id, agent_type, metrics_port)