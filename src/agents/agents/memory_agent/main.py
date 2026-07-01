"""
Memory Agent - Memory management and retrieval
Manages short-term and long-term memory, handles storage and retrieval of information
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json
from collections import deque
import hashlib

from ...core.agent_base import BaseAgent, AgentMessage, MessageType


class MemoryType(Enum):
    """Types of memory"""
    EPISODIC = "episodic"  # Personal experiences
    SEMANTIC = "semantic"  # General knowledge
    PROCEDURAL = "procedural"  # Skills and procedures
    WORKING = "working"  # Short-term active memory
    LONG_TERM = "long_term"  # Persistent long-term memory


class MemoryPriority(Enum):
    """Memory priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class MemoryItem:
    """Represents a memory item"""
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.EPISODIC
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: MemoryPriority = MemoryPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    related_memories: List[str] = field(default_factory=list)
    expiration: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value,
            "content": self.content[:500],  # Truncate for display
            "metadata": self.metadata,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "tags": self.tags,
            "related_memories": self.related_memories,
            "expiration": self.expiration.isoformat() if self.expiration else None
        }


@dataclass
class MemoryQuery:
    """Represents a memory query"""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    memory_types: List[MemoryType] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    time_range: Optional[tuple] = None  # (start_date, end_date)
    limit: int = 10
    similarity_threshold: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query": self.query,
            "memory_types": [mt.value for mt in self.memory_types],
            "tags": self.tags,
            "time_range": self.time_range,
            "limit": self.limit,
            "similarity_threshold": self.similarity_threshold
        }


class MemoryAgent(BaseAgent):
    """
    Memory Agent - Manages memory storage and retrieval
    Handles different types of memory with intelligent retrieval
    """
    
    def __init__(
        self,
        agent_id: str = "memory-agent-1",
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        enable_tracing: bool = True,
        enable_metrics: bool = True,
        working_memory_capacity: int = 50,
        long_term_capacity: int = 10000
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="memory",
            rabbitmq_url=rabbitmq_url,
            enable_tracing=enable_tracing,
            enable_metrics=enable_metrics
        )
        
        # Memory storage
        self.working_memory: deque = deque(maxlen=working_memory_capacity)
        self.long_term_memory: Dict[str, MemoryItem] = {}
        self.memory_index: Dict[str, List[str]] = {}  # tag -> memory_ids
        self.temporal_index: Dict[str, List[tuple]] = {}  # time -> (memory_id, timestamp)
        
        # Configuration
        self.working_memory_capacity = working_memory_capacity
        self.long_term_capacity = long_term_capacity
        
        # Capabilities
        self.capabilities = [
            "memory_storage",
            "memory_retrieval",
            "memory_search",
            "memory_management",
            "memory_consolidation",
            "memory_cleanup"
        ]
    
    def register_handlers(self):
        """Register message handlers"""
        self.message_handlers[MessageType.TASK_REQUEST] = self.handle_task_request
        self.message_handlers[MessageType.QUERY] = self.handle_query
        self.message_handlers[MessageType.EVENT] = self.handle_event
    
    async def start(self):
        """Start the memory agent"""
        await super().start()
        
        # Start background tasks
        await self.start_background_tasks()
        
        # Announce capabilities
        await self.announce_capabilities()
    
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        # Memory consolidation task
        consolidation_task = asyncio.create_task(self.memory_consolidation_loop())
        self.background_tasks.append(consolidation_task)
        
        # Memory cleanup task
        cleanup_task = asyncio.create_task(self.memory_cleanup_loop())
        self.background_tasks.append(cleanup_task)
    
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
    
    async def handle_task_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming memory task"""
        task_data = message.content
        task_type = task_data.get("task_type")
        
        if task_type == "store":
            result = await self.store_memory(task_data)
        elif task_type == "retrieve":
            result = await self.retrieve_memory(task_data)
        elif task_type == "search":
            result = await self.search_memory(task_data)
        elif task_type == "update":
            result = await self.update_memory(task_data)
        elif task_type == "delete":
            result = await self.delete_memory(task_data)
        else:
            result = {"error": "Unknown task type"}
        
        return result
    
    async def handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle query messages"""
        query_type = message.content.get("query_type")
        
        if query_type == "memory_status":
            return await self.get_memory_status()
        elif query_type == "memory_stats":
            return await self.get_memory_stats()
        elif query_type == "capabilities":
            return {"capabilities": self.capabilities}
        else:
            return {"error": "Unknown query type"}
    
    async def handle_event(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle event messages"""
        event_type = message.content.get("event_type")
        
        if event_type == "consolidate_memory":
            await self.consolidate_working_memory()
        
        return {"status": "acknowledged"}
    
    async def store_memory(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a memory item"""
        with self.tracer.start_as_current_span("store_memory") as span:
            memory_type = MemoryType(task_data.get("memory_type", "episodic"))
            content = task_data.get("content", "")
            metadata = task_data.get("metadata", {})
            tags = task_data.get("tags", [])
            priority = MemoryPriority(task_data.get("priority", 3))
            
            # Create memory item
            memory = MemoryItem(
                memory_type=memory_type,
                content=content,
                metadata=metadata,
                tags=tags,
                priority=priority
            )
            
            # Generate embedding
            memory.embedding = await self.generate_embedding(content)
            
            # Store based on memory type
            if memory_type == MemoryType.WORKING:
                self.working_memory.append(memory)
            else:
                # Check capacity
                if len(self.long_term_memory) >= self.long_term_capacity:
                    await self.evict_low_priority_memories()
                
                self.long_term_memory[memory.memory_id] = memory
            
            # Update indexes
            await self.update_indexes(memory)
            
            span.set_attribute("memory_id", memory.memory_id)
            span.set_attribute("memory_type", memory_type.value)
            
            return {
                "memory_id": memory.memory_id,
                "status": "stored",
                "memory_type": memory_type.value
            }
    
    async def retrieve_memory(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve a specific memory"""
        memory_id = task_data.get("memory_id")
        
        # Check working memory first
        for memory in self.working_memory:
            if memory.memory_id == memory_id:
                memory.last_accessed = datetime.utcnow()
                memory.access_count += 1
                return memory.to_dict()
        
        # Check long-term memory
        if memory_id in self.long_term_memory:
            memory = self.long_term_memory[memory_id]
            memory.last_accessed = datetime.utcnow()
            memory.access_count += 1
            return memory.to_dict()
        
        return {"error": "Memory not found"}
    
    async def search_memory(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for memories"""
        query = task_data.get("query", "")
        memory_types = [MemoryType(mt) for mt in task_data.get("memory_types", [])]
        tags = task_data.get("tags", [])
        limit = task_data.get("limit", 10)
        similarity_threshold = task_data.get("similarity_threshold", 0.5)
        
        results = []
        
        # Generate query embedding
        query_embedding = await self.generate_embedding(query)
        
        # Search in working memory
        for memory in self.working_memory:
            if await self.matches_criteria(memory, memory_types, tags):
                similarity = await self.calculate_similarity(query_embedding, memory.embedding)
                if similarity >= similarity_threshold:
                    results.append((memory, similarity))
        
        # Search in long-term memory
        for memory in self.long_term_memory.values():
            if await self.matches_criteria(memory, memory_types, tags):
                similarity = await self.calculate_similarity(query_embedding, memory.embedding)
                if similarity >= similarity_threshold:
                    results.append((memory, similarity))
        
        # Sort by similarity and limit results
        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:limit]
        
        return {
            "query": query,
            "results": [memory.to_dict() for memory, similarity in results],
            "count": len(results)
        }
    
    async def update_memory(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing memory"""
        memory_id = task_data.get("memory_id")
        updates = task_data.get("updates", {})
        
        # Find and update memory
        for memory in self.working_memory:
            if memory.memory_id == memory_id:
                for key, value in updates.items():
                    if hasattr(memory, key):
                        setattr(memory, key, value)
                return {"status": "updated", "memory_id": memory_id}
        
        if memory_id in self.long_term_memory:
            memory = self.long_term_memory[memory_id]
            for key, value in updates.items():
                if hasattr(memory, key):
                    setattr(memory, key, value)
            return {"status": "updated", "memory_id": memory_id}
        
        return {"error": "Memory not found"}
    
    async def delete_memory(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a memory"""
        memory_id = task_data.get("memory_id")
        
        # Remove from working memory
        self.working_memory = deque(
            [m for m in self.working_memory if m.memory_id != memory_id],
            maxlen=self.working_memory_capacity
        )
        
        # Remove from long-term memory
        if memory_id in self.long_term_memory:
            del self.long_term_memory[memory_id]
            return {"status": "deleted", "memory_id": memory_id}
        
        return {"error": "Memory not found"}
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (simplified)"""
        # In production, use real embedding models
        # This is a simplified hash-based embedding
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to numeric vector
        embedding = []
        for i in range(0, len(text_hash), 2):
            byte_pair = text_hash[i:i+2]
            value = int(byte_pair, 16) / 255.0
            embedding.append(value)
        
        # Pad to fixed length
        while len(embedding) < 128:
            embedding.append(0.0)
        
        return embedding[:128]
    
    async def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        if not embedding1 or not embedding2:
            return 0.0
        
        # Ensure same length
        min_len = min(len(embedding1), len(embedding2))
        embedding1 = embedding1[:min_len]
        embedding2 = embedding2[:min_len]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def matches_criteria(self, memory: MemoryItem, memory_types: List[MemoryType], tags: List[str]) -> bool:
        """Check if memory matches search criteria"""
        # Check memory type
        if memory_types and memory.memory_type not in memory_types:
            return False
        
        # Check tags
        if tags:
            if not any(tag in memory.tags for tag in tags):
                return False
        
        return True
    
    async def update_indexes(self, memory: MemoryItem):
        """Update memory indexes"""
        # Update tag index
        for tag in memory.tags:
            if tag not in self.memory_index:
                self.memory_index[tag] = []
            if memory.memory_id not in self.memory_index[tag]:
                self.memory_index[tag].append(memory.memory_id)
        
        # Update temporal index
        date_key = memory.created_at.strftime("%Y-%m-%d")
        if date_key not in self.temporal_index:
            self.temporal_index[date_key] = []
        self.temporal_index[date_key].append((memory.memory_id, memory.created_at))
    
    async def evict_low_priority_memories(self):
        """Evict low priority memories when capacity is reached"""
        # Sort by priority and access time
        memories = list(self.long_term_memory.values())
        memories.sort(key=lambda m: (m.priority.value, m.last_accessed))
        
        # Evict lowest priority memories
        to_evict = memories[:len(memories) - self.long_term_capacity + 100]
        for memory in to_evict:
            del self.long_term_memory[memory.memory_id]
            self.logger.info(f"Evicted memory {memory.memory_id}")
    
    async def memory_consolidation_loop(self):
        """Periodically consolidate working memory to long-term memory"""
        while self.status.value == "running":
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self.consolidate_working_memory()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Memory consolidation error: {e}")
    
    async def consolidate_working_memory(self):
        """Consolidate working memory to long-term memory"""
        if not self.working_memory:
            return
        
        # Move important memories to long-term storage
        memories_to_consolidate = []
        
        for memory in self.working_memory:
            # Consolidate if high priority or frequently accessed
            if memory.priority in [MemoryPriority.CRITICAL, MemoryPriority.HIGH] or memory.access_count > 3:
                memories_to_consolidate.append(memory)
        
        for memory in memories_to_consolidate:
            # Check capacity
            if len(self.long_term_memory) >= self.long_term_capacity:
                await self.evict_low_priority_memories()
            
            # Move to long-term memory
            self.long_term_memory[memory.memory_id] = memory
            self.logger.info(f"Consolidated memory {memory.memory_id} to long-term storage")
        
        # Remove consolidated memories from working memory
        if memories_to_consolidate:
            self.working_memory = deque(
                [m for m in self.working_memory if m not in memories_to_consolidate],
                maxlen=self.working_memory_capacity
            )
    
    async def memory_cleanup_loop(self):
        """Periodically clean up expired memories"""
        while self.status.value == "running":
            try:
                await asyncio.sleep(600)  # Every 10 minutes
                await self.cleanup_expired_memories()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Memory cleanup error: {e}")
    
    async def cleanup_expired_memories(self):
        """Clean up expired memories"""
        now = datetime.utcnow()
        expired_ids = []
        
        # Check long-term memory for expired items
        for memory_id, memory in self.long_term_memory.items():
            if memory.expiration and memory.expiration < now:
                expired_ids.append(memory_id)
        
        # Remove expired memories
        for memory_id in expired_ids:
            del self.long_term_memory[memory_id]
            self.logger.info(f"Removed expired memory {memory_id}")
    
    async def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory status"""
        return {
            "working_memory_count": len(self.working_memory),
            "working_memory_capacity": self.working_memory_capacity,
            "long_term_memory_count": len(self.long_term_memory),
            "long_term_capacity": self.long_term_capacity,
            "indexed_tags": len(self.memory_index),
            "indexed_dates": len(self.temporal_index)
        }
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        # Calculate statistics
        memory_types = {}
        priority_distribution = {}
        
        for memory in self.long_term_memory.values():
            memory_type = memory.memory_type.value
            memory_types[memory_type] = memory_types.get(memory_type, 0) + 1
            
            priority = memory.priority.value
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        return {
            "total_memories": len(self.long_term_memory),
            "memory_types": memory_types,
            "priority_distribution": priority_distribution,
            "average_access_count": sum(m.access_count for m in self.long_term_memory.values()) / len(self.long_term_memory) if self.long_term_memory else 0
        }
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a memory task"""
        task_type = task.get("task_type")
        
        if task_type == "store":
            return await self.store_memory(task)
        elif task_type == "retrieve":
            return await self.retrieve_memory(task)
        elif task_type == "search":
            return await self.search_memory(task)
        else:
            return {"error": "Unknown task type"}


async def main():
    """Main entry point for the memory agent"""
    agent = MemoryAgent()
    
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