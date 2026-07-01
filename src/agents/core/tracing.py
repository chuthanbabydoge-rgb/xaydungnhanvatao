"""
OpenTelemetry Tracing Configuration
Centralized tracing setup for all agents using OpenTelemetry
"""
import logging
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_RESOURCE
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.zipkin.proto import ZipkinExporter
from opentelemetry.exporter.otlp.proto.grpc import OTLPSpanExporter
try:
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
except ImportError:
    AioHttpClientInstrumentor = None
    AsyncioInstrumentor = None


class TracingConfig:
    """Centralized tracing configuration"""
    
    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        zipkin_endpoint: Optional[str] = None,
        otlp_endpoint: Optional[str] = None,
        enable_console_exporter: bool = False,
        sample_rate: float = 1.0
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.zipkin_endpoint = zipkin_endpoint
        self.otlp_endpoint = otlp_endpoint
        self.enable_console_exporter = enable_console_exporter
        self.sample_rate = sample_rate
        
        self.logger = logging.getLogger("tracing")
    
    def setup_tracing(self) -> trace.Tracer:
        """Setup OpenTelemetry tracing"""
        # Create resource
        resource = Resource.create({
            SERVICE_RESOURCE: {
                "service.name": self.service_name,
                "service.version": self.service_version
            }
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Add Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=self.jaeger_host,
            agent_port=self.jaeger_port,
        )
        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        self.logger.info(f"Added Jaeger exporter: {self.jaeger_host}:{self.jaeger_port}")
        
        # Add Zipkin exporter if configured
        if self.zipkin_endpoint:
            zipkin_exporter = ZipkinExporter(
                endpoint=self.zipkin_endpoint,
            )
            provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))
            self.logger.info(f"Added Zipkin exporter: {self.zipkin_endpoint}")
        
        # Add OTLP exporter if configured
        if self.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.otlp_endpoint,
                insecure=True
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            self.logger.info(f"Added OTLP exporter: {self.otlp_endpoint}")
        
        # Add console exporter if enabled
        if self.enable_console_exporter:
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            self.logger.info("Added console exporter")
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Instrument asyncio if available
        if AsyncioInstrumentor:
            AsyncioInstrumentor().instrument()
        
        # Instrument aiohttp client if available
        if AioHttpClientInstrumentor:
            AioHttpClientInstrumentor().instrument()
        
        self.logger.info(f"Tracing setup complete for {self.service_name}")
        
        return trace.get_tracer(__name__)
    
    def get_tracer(self, name: str) -> trace.Tracer:
        """Get a tracer with a specific name"""
        return trace.get_tracer(name)


class AgentTracer:
    """Helper class for agent-specific tracing"""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = TracingConfig(
            service_name=f"{agent_type}-agent",
            service_version="1.0.0"
        )
        self.tracer = self.config.setup_tracing()
    
    def start_span(self, name: str, **kwargs):
        """Start a new span"""
        return self.tracer.start_as_current_span(name, attributes={
            "agent.id": self.agent_id,
            "agent.type": self.agent_type,
            **kwargs
        })
    
    def add_event(self, name: str, attributes: dict = None):
        """Add an event to the current span"""
        current_span = trace.get_current_span()
        if current_span:
            current_span.add_event(name, attributes or {})
    
    def set_attribute(self, key: str, value):
        """Set an attribute on the current span"""
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(key, value)
    
    def record_exception(self, exception: Exception):
        """Record an exception on the current span"""
        current_span = trace.get_current_span()
        if current_span:
            current_span.record_exception(exception)


def setup_agent_tracing(agent_id: str, agent_type: str) -> AgentTracer:
    """Setup tracing for an agent"""
    return AgentTracer(agent_id, agent_type)