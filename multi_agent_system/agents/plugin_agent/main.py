"""
Plugin Agent - Plugin management and execution
Manages plugin lifecycle, handles plugin loading, execution, and monitoring
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import importlib
import sys
import os
import json
from pathlib import Path

from shared.agent_base import BaseAgent, AgentMessage, MessageType


class PluginStatus(Enum):
    """Plugin status states"""
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UNLOADED = "unloaded"


class PluginType(Enum):
    """Types of plugins"""
    PROCESSOR = "processor"
    FILTER = "filter"
    TRANSFORMER = "transformer"
    ANALYZER = "analyzer"
    GENERATOR = "generator"
    INTEGRATION = "integration"
    CUSTOM = "custom"


@dataclass
class Plugin:
    """Represents a plugin"""
    plugin_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"
    plugin_type: PluginType = PluginType.CUSTOM
    description: str = ""
    author: str = ""
    file_path: str = ""
    status: PluginStatus = PluginStatus.UNLOADED
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    loaded_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "plugin_type": self.plugin_type.value,
            "description": self.description,
            "author": self.author,
            "file_path": self.file_path,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "config": self.config,
            "metadata": self.metadata,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
            "error_message": self.error_message
        }


@dataclass
class PluginExecution:
    """Represents a plugin execution"""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plugin_id: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
    status: str = "pending"
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "plugin_id": self.plugin_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "execution_time": self.execution_time,
            "status": self.status,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class PluginAgent(BaseAgent):
    """
    Plugin Agent - Plugin management and execution
    Manages plugin lifecycle, handles plugin loading, execution, and monitoring
    """
    
    def __init__(
        self,
        agent_id: str = "plugin-agent-1",
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        enable_tracing: bool = True,
        enable_metrics: bool = True,
        plugin_directory: str = "./plugins"
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="plugin",
            rabbitmq_url=rabbitmq_url,
            enable_tracing=enable_tracing,
            enable_metrics=enable_metrics
        )
        
        # Plugin storage
        self.plugins: Dict[str, Plugin] = {}  # plugin_id -> plugin
        self.plugin_registry: Dict[str, str] = {}  # name -> plugin_id
        self.loaded_plugins: Dict[str, Any] = {}  # plugin_id -> loaded module
        
        # Execution tracking
        self.executions: Dict[str, PluginExecution] = {}
        
        # Configuration
        self.plugin_directory = plugin_directory
        
        # Capabilities
        self.capabilities = [
            "plugin_loading",
            "plugin_unloading",
            "plugin_execution",
            "plugin_management",
            "dependency_resolution",
            "plugin_monitoring"
        ]
    
    def register_handlers(self):
        """Register message handlers"""
        self.message_handlers[MessageType.TASK_REQUEST] = self.handle_task_request
        self.message_handlers[MessageType.QUERY] = self.handle_query
        self.message_handlers[MessageType.EVENT] = self.handle_event
    
    async def start(self):
        """Start the plugin agent"""
        await super().start()
        
        # Create plugin directory if it doesn't exist
        os.makedirs(self.plugin_directory, exist_ok=True)
        
        # Load available plugins
        await self.discover_plugins()
        
        # Start background tasks
        await self.start_background_tasks()
        
        # Announce capabilities
        await self.announce_capabilities()
    
    async def start_background_tasks(self):
        """Start background plugin management tasks"""
        # Plugin health check loop
        health_check = asyncio.create_task(self.plugin_health_check_loop())
        self.background_tasks.append(health_check)
    
    async def announce_capabilities(self):
        """Announce agent capabilities"""
        capabilities_message = AgentMessage(
            sender_id=self.agent_id,
            message_type=MessageType.EVENT,
            content={
                "event_type": "agent_capabilities",
                "agent_id": self.agent_id,
                "capabilities": self.capabilities
            }
        )
        
        await self.publish_message(
            capabilities_message,
            routing_key="planner.*"
        )
    
    async def discover_plugins(self):
        """Discover available plugins in the plugin directory"""
        plugin_path = Path(self.plugin_directory)
        
        if not plugin_path.exists():
            self.logger.warning(f"Plugin directory {self.plugin_directory} does not exist")
            return
        
        # Look for Python files
        for plugin_file in plugin_path.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                # Create plugin entry
                plugin = Plugin(
                    name=plugin_file.stem,
                    file_path=str(plugin_file),
                    plugin_type=PluginType.CUSTOM,
                    description=f"Plugin from {plugin_file.name}",
                    status=PluginStatus.UNLOADED
                )
                
                self.plugins[plugin.plugin_id] = plugin
                self.plugin_registry[plugin.name] = plugin.plugin_id
                
                self.logger.info(f"Discovered plugin: {plugin.name}")
            
            except Exception as e:
                self.logger.error(f"Error discovering plugin {plugin_file}: {e}")
    
    async def handle_task_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming plugin task"""
        task_data = message.content
        task_type = task_data.get("task_type")
        
        if task_type == "load_plugin":
            result = await self.load_plugin(task_data)
        elif task_type == "unload_plugin":
            result = await self.unload_plugin(task_data)
        elif task_type == "execute_plugin":
            result = await self.execute_plugin(task_data)
        elif task_type == "reload_plugin":
            result = await self.reload_plugin(task_data)
        elif task_type == "install_plugin":
            result = await self.install_plugin(task_data)
        else:
            result = {"error": "Unknown task type"}
        
        return result
    
    async def handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle query messages"""
        query_type = message.content.get("query_type")
        
        if query_type == "plugin_status":
            plugin_id = message.content.get("plugin_id")
            if plugin_id in self.plugins:
                return self.plugins[plugin_id].to_dict()
            else:
                return {"error": "Plugin not found"}
        
        elif query_type == "list_plugins":
            return await self.list_plugins()
        
        elif query_type == "execution_status":
            execution_id = message.content.get("execution_id")
            if execution_id in self.executions:
                return self.executions[execution_id].to_dict()
            else:
                return {"error": "Execution not found"}
        
        elif query_type == "capabilities":
            return {"capabilities": self.capabilities}
        
        else:
            return {"error": "Unknown query type"}
    
    async def handle_event(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle event messages"""
        event_type = message.content.get("event_type")
        
        if event_type == "plugin_update":
            # Reload plugin on update
            plugin_name = message.content.get("plugin_name")
            if plugin_name in self.plugin_registry:
                plugin_id = self.plugin_registry[plugin_name]
                await self.reload_plugin({"plugin_id": plugin_id})
        
        return {"status": "acknowledged"}
    
    async def load_plugin(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load a plugin"""
        with self.tracer.start_as_current_span("load_plugin") as span:
            plugin_id = task_data.get("plugin_id")
            file_path = task_data.get("file_path")
            
            # Get or create plugin
            if plugin_id and plugin_id in self.plugins:
                plugin = self.plugins[plugin_id]
            elif file_path:
                # Create new plugin entry
                plugin = Plugin(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    plugin_type=PluginType(task_data.get("plugin_type", "custom")),
                    description=task_data.get("description", ""),
                    author=task_data.get("author", ""),
                    config=task_data.get("config", {})
                )
                self.plugins[plugin.plugin_id] = plugin
                self.plugin_registry[plugin.name] = plugin.plugin_id
            else:
                return {"error": "Either plugin_id or file_path must be provided"}
            
            span.set_attribute("plugin_id", plugin.plugin_id)
            span.set_attribute("plugin_name", plugin.name)
            
            try:
                # Check dependencies
                if plugin.dependencies:
                    await self.resolve_dependencies(plugin.dependencies)
                
                # Load the plugin module
                if plugin.file_path:
                    # Add plugin directory to Python path
                    plugin_dir = str(Path(plugin.file_path).parent)
                    if plugin_dir not in sys.path:
                        sys.path.insert(0, plugin_dir)
                    
                    # Import the module
                    spec = importlib.util.spec_from_file_location(plugin.name, plugin.file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        self.loaded_plugins[plugin.plugin_id] = module
                        plugin.status = PluginStatus.LOADED
                        plugin.loaded_at = datetime.utcnow()
                        
                        # Extract capabilities from module
                        if hasattr(module, "get_capabilities"):
                            plugin.capabilities = module.get_capabilities()
                        
                        span.set_attribute("status", "loaded")
                        
                        return {
                            "plugin_id": plugin.plugin_id,
                            "status": "loaded",
                            "capabilities": plugin.capabilities
                        }
            
            except Exception as e:
                plugin.status = PluginStatus.ERROR
                plugin.error_message = str(e)
                span.set_attribute("error", str(e))
                self.logger.error(f"Error loading plugin {plugin.name}: {e}")
                
                return {
                    "plugin_id": plugin.plugin_id,
                    "status": "error",
                    "error": str(e)
                }
            
            return {"error": "Failed to load plugin"}
    
    async def unload_plugin(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Unload a plugin"""
        plugin_id = task_data.get("plugin_id")
        
        if plugin_id not in self.plugins:
            return {"error": "Plugin not found"}
        
        plugin = self.plugins[plugin_id]
        
        try:
            # Remove from loaded plugins
            if plugin_id in self.loaded_plugins:
                del self.loaded_plugins[plugin_id]
            
            plugin.status = PluginStatus.UNLOADED
            plugin.loaded_at = None
            
            self.logger.info(f"Unloaded plugin {plugin.name}")
            
            return {
                "plugin_id": plugin_id,
                "status": "unloaded"
            }
        
        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin.name}: {e}")
            return {
                "plugin_id": plugin_id,
                "status": "error",
                "error": str(e)
            }
    
    async def execute_plugin(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a plugin"""
        with self.tracer.start_as_current_span("execute_plugin") as span:
            plugin_id = task_data.get("plugin_id")
            input_data = task_data.get("input_data", {})
            function_name = task_data.get("function", "process")
            
            if plugin_id not in self.plugins:
                return {"error": "Plugin not found"}
            
            plugin = self.plugins[plugin_id]
            
            if plugin.status != PluginStatus.LOADED:
                return {"error": f"Plugin is not loaded (status: {plugin.status.value})"}
            
            span.set_attribute("plugin_id", plugin_id)
            span.set_attribute("plugin_name", plugin.name)
            span.set_attribute("function", function_name)
            
            # Create execution record
            execution = PluginExecution(
                plugin_id=plugin_id,
                input_data=input_data
            )
            
            try:
                # Get the loaded module
                module = self.loaded_plugins[plugin_id]
                
                # Execute the function
                if hasattr(module, function_name):
                    func = getattr(module, function_name)
                    
                    start_time = datetime.utcnow()
                    result = await asyncio.to_thread(func, input_data)
                    end_time = datetime.utcnow()
                    
                    execution.output_data = result
                    execution.execution_time = (end_time - start_time).total_seconds()
                    execution.status = "completed"
                    execution.completed_at = end_time
                    
                    # Update plugin usage stats
                    plugin.last_used = datetime.utcnow()
                    plugin.usage_count += 1
                    
                    span.set_attribute("execution_time", execution.execution_time)
                    span.set_attribute("status", "completed")
                    
                    self.executions[execution.execution_id] = execution
                    
                    return execution.to_dict()
                else:
                    execution.status = "error"
                    execution.error = f"Function {function_name} not found in plugin"
                    span.set_attribute("error", execution.error)
                    
                    return execution.to_dict()
            
            except Exception as e:
                execution.status = "error"
                execution.error = str(e)
                execution.completed_at = datetime.utcnow()
                
                span.set_attribute("error", str(e))
                self.logger.error(f"Error executing plugin {plugin.name}: {e}")
                
                self.executions[execution.execution_id] = execution
                
                return execution.to_dict()
    
    async def reload_plugin(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reload a plugin"""
        plugin_id = task_data.get("plugin_id")
        
        if plugin_id not in self.plugins:
            return {"error": "Plugin not found"}
        
        # Unload first
        unload_result = await self.unload_plugin({"plugin_id": plugin_id})
        
        if unload_result.get("status") == "unloaded":
            # Reload
            plugin = self.plugins[plugin_id]
            load_result = await self.load_plugin({
                "plugin_id": plugin_id,
                "file_path": plugin.file_path
            })
            
            return load_result
        
        return unload_result
    
    async def install_plugin(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Install a plugin from source"""
        # In production, this would download and install plugins
        plugin_url = task_data.get("url")
        plugin_name = task_data.get("name")
        
        # Simulated installation
        plugin = Plugin(
            name=plugin_name,
            plugin_type=PluginType(task_data.get("plugin_type", "custom")),
            description=task_data.get("description", ""),
            author=task_data.get("author", ""),
            status=PluginStatus.UNLOADED,
            metadata={"source": plugin_url}
        )
        
        self.plugins[plugin.plugin_id] = plugin
        self.plugin_registry[plugin.name] = plugin.plugin_id
        
        return {
            "plugin_id": plugin.plugin_id,
            "status": "installed"
        }
    
    async def resolve_dependencies(self, dependencies: List[str]) -> bool:
        """Resolve plugin dependencies"""
        # Check if dependencies are available
        for dep in dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                self.logger.warning(f"Dependency {dep} not found")
                return False
        
        return True
    
    async def list_plugins(self) -> Dict[str, Any]:
        """List all plugins"""
        return {
            "plugins": [plugin.to_dict() for plugin in self.plugins.values()],
            "total_count": len(self.plugins),
            "loaded_count": sum(1 for p in self.plugins.values() if p.status == PluginStatus.LOADED)
        }
    
    async def plugin_health_check_loop(self):
        """Monitor plugin health"""
        while self.status.value == "running":
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                for plugin_id, plugin in list(self.plugins.items()):
                    if plugin.status == PluginStatus.LOADED:
                        # Check if plugin is still responsive
                        try:
                            module = self.loaded_plugins.get(plugin_id)
                            if module and hasattr(module, "health_check"):
                                is_healthy = await asyncio.to_thread(module.health_check)
                                if not is_healthy:
                                    self.logger.warning(f"Plugin {plugin.name} health check failed")
                                    plugin.status = PluginStatus.ERROR
                        except Exception as e:
                            self.logger.error(f"Health check error for {plugin.name}: {e}")
                            plugin.status = PluginStatus.ERROR
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Plugin health check error: {e}")
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a plugin task"""
        task_type = task.get("task_type")
        
        if task_type == "execute_plugin":
            return await self.execute_plugin(task)
        elif task_type == "load_plugin":
            return await self.load_plugin(task)
        else:
            return {"error": "Unknown task type"}


async def main():
    """Main entry point for the plugin agent"""
    agent = PluginAgent()
    
    try:
        await agent.start()
        
        # Start consuming messages
        await agent.consume_messages()
        
    except KeyboardInterrupt:
        await agent.stop()
    except Exception as e:
        agent.logger.error(f"Agent error: {e}")
        await agent.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())