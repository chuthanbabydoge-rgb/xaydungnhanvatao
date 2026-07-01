"""
Long-term Memory - Persistent Memory Storage
Local memory management with consolidation, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
from datetime import datetime, timedelta
import json


class MemoryType(Enum):
    """Types of long-term memories"""
    EPISODIC = "episodic"  # Specific events/experiences
    SEMANTIC = "semantic"  # General knowledge/facts
    PROCEDURAL = "procedural"  # Skills/how-to knowledge
    EMOTIONAL = "emotional"  # Emotional associations
    PROFILE = "profile"  # User profile information


class Memory:
    """Represents a long-term memory"""
    def __init__(
        self,
        memory_id: str,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        emotional_valence: float = 0.0,
        access_count: int = 0
    ):
        self.memory_id = memory_id
        self.content = content
        self.memory_type = memory_type
        self.importance = importance  # 0.0 to 1.0
        self.emotional_valence = emotional_valence  # -1.0 (negative) to 1.0 (positive)
        self.access_count = access_count
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.last_modified = datetime.utcnow()
        self.tags: List[str] = []
        self.related_memories: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance,
            "emotional_valence": self.emotional_valence,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "tags": self.tags,
            "related_memories": self.related_memories,
            "metadata": self.metadata
        }
    
    def access(self):
        """Record memory access"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def modify(self, new_content: str):
        """Modify memory content"""
        self.content = new_content
        self.last_modified = datetime.utcnow()


class LongTermMemory:
    """
    Long-term memory management with consolidation and forgetting
    Local memory operations, not LLM-dependent
    """
    
    def __init__(self):
        self.memories: Dict[str, Dict[str, Memory]] = {}  # character_id -> memory_id -> Memory
        self.memory_types: Dict[str, Dict[MemoryType, List[str]]] = {}  # character_id -> type -> memory_ids
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize long-term memory"""
        self.is_initialized = True
        print("Long-term Memory initialized")
    
    async def shutdown(self):
        """Shutdown long-term memory"""
        self.is_initialized = False
        print("Long-term Memory shutdown")
    
    async def store_memory(
        self,
        character_id: str,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        emotional_valence: float = 0.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Memory:
        """Store a new memory"""
        
        import uuid
        memory_id = str(uuid.uuid4())
        
        memory = Memory(
            memory_id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            emotional_valence=emotional_valence
        )
        
        if tags:
            memory.tags = tags
        
        if metadata:
            memory.metadata = metadata
        
        # Store memory
        if character_id not in self.memories:
            self.memories[character_id] = {}
        
        self.memories[character_id][memory_id] = memory
        
        # Index by type
        if character_id not in self.memory_types:
            self.memory_types[character_id] = {mt: [] for mt in MemoryType}
        
        self.memory_types[character_id][memory_type].append(memory_id)
        
        return memory
    
    async def retrieve_memory(
        self,
        character_id: str,
        memory_id: str
    ) -> Optional[Memory]:
        """Retrieve a specific memory"""
        if character_id in self.memories and memory_id in self.memories[character_id]:
            memory = self.memories[character_id][memory_id]
            memory.access()
            return memory
        return None
    
    async def retrieve_memories_by_type(
        self,
        character_id: str,
        memory_type: MemoryType,
        limit: int = 10
    ) -> List[Memory]:
        """Retrieve memories of a specific type"""
        
        if character_id not in self.memory_types:
            return []
        
        memory_ids = self.memory_types[character_id].get(memory_type, [])
        
        memories = []
        for memory_id in memory_ids[:limit]:
            memory = await self.retrieve_memory(character_id, memory_id)
            if memory:
                memories.append(memory)
        
        # Sort by importance and recency
        memories.sort(
            key=lambda m: (m.importance, m.last_accessed),
            reverse=True
        )
        
        return memories
    
    async def search_memories(
        self,
        character_id: str,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10
    ) -> List[Memory]:
        """Search memories by content"""
        
        if character_id not in self.memories:
            return []
        
        results = []
        query_lower = query.lower()
        
        for memory_id, memory in self.memories[character_id].items():
            # Filter by type if specified
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # Simple content matching
            if query_lower in memory.content.lower():
                results.append(memory)
            # Tag matching
            elif any(query_lower in tag.lower() for tag in memory.tags):
                results.append(memory)
        
        # Sort by relevance (importance + access frequency)
        results.sort(
            key=lambda m: (m.importance, m.access_count),
            reverse=True
        )
        
        return results[:limit]
    
    async def update_memory(
        self,
        character_id: str,
        memory_id: str,
        new_content: Optional[str] = None,
        new_importance: Optional[float] = None,
        new_tags: Optional[List[str]] = None
    ) -> bool:
        """Update an existing memory"""
        
        memory = await self.retrieve_memory(character_id, memory_id)
        if not memory:
            return False
        
        if new_content:
            memory.modify(new_content)
        
        if new_importance is not None:
            memory.importance = max(0.0, min(new_importance, 1.0))
        
        if new_tags:
            memory.tags = new_tags
        
        return True
    
    async def delete_memory(self, character_id: str, memory_id: str) -> bool:
        """Delete a memory"""
        
        if character_id in self.memories and memory_id in self.memories[character_id]:
            memory = self.memories[character_id][memory_id]
            
            # Remove from type index
            if character_id in self.memory_types:
                if memory.memory_type in self.memory_types[character_id]:
                    self.memory_types[character_id][memory.memory_type].remove(memory_id)
            
            # Remove memory
            del self.memories[character_id][memory_id]
            return True
        
        return False
    
    async def consolidate_memories(self, character_id: str):
        """
        Consolidate similar memories
        Local consolidation algorithm, not LLM-dependent
        """
        
        if character_id not in self.memories:
            return
        
        # Group memories by type and content similarity
        episodic_memories = await self.retrieve_memories_by_type(
            character_id, MemoryType.EPISODIC, limit=100
        )
        
        # Simple consolidation: merge memories with similar content
        consolidated_groups = []
        
        for memory in episodic_memories:
            # Check if this memory fits into an existing group
            merged = False
            for group in consolidated_groups:
                if self._are_memories_similar(memory, group[0]):
                    group.append(memory)
                    merged = True
                    break
            
            if not merged:
                consolidated_groups.append([memory])
        
        # Merge each group into a single memory
        for group in consolidated_groups:
            if len(group) > 1:
                await self._merge_memory_group(character_id, group)
    
    def _are_memories_similar(self, memory1: Memory, memory2: Memory) -> bool:
        """Check if two memories are similar"""
        # Simple similarity check based on content overlap
        words1 = set(memory1.content.lower().split())
        words2 = set(memory2.content.lower().split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1.intersection(words2))
        similarity = overlap / min(len(words1), len(words2))
        
        return similarity > 0.5  # 50% similarity threshold
    
    async def _merge_memory_group(self, character_id: str, memories: List[Memory]):
        """Merge a group of similar memories"""
        
        # Keep the most important memory as the base
        memories.sort(key=lambda m: m.importance, reverse=True)
        base_memory = memories[0]
        
        # Combine content from all memories
        all_content = [m.content for m in memories]
        combined_content = " | ".join(all_content)
        
        # Update base memory
        await self.update_memory(
            character_id,
            base_memory.memory_id,
            new_content=combined_content,
            new_importance=min(base_memory.importance + 0.1, 1.0)
        )
        
        # Delete other memories
        for memory in memories[1:]:
            await self.delete_memory(character_id, memory.memory_id)
    
    async def forget_memories(self, character_id: str):
        """
        Forget less important memories
        Local forgetting algorithm based on importance and access
        """
        
        if character_id not in self.memories:
            return
        
        memories_to_forget = []
        
        for memory_id, memory in self.memories[character_id].items():
            # Calculate forgettability score
            days_since_access = (datetime.utcnow() - memory.last_accessed).days
            days_since_creation = (datetime.utcnow() - memory.created_at).days
            
            # Forgetting criteria:
            # - Low importance
            # - Not accessed recently
            # - Old
            if (memory.importance < 0.3 and 
                days_since_access > 30 and 
                days_since_creation > 90):
                memories_to_forget.append(memory_id)
        
        # Delete memories marked for forgetting
        for memory_id in memories_to_forget:
            await self.delete_memory(character_id, memory_id)
    
    async def get_memory_statistics(self, character_id: str) -> Dict[str, Any]:
        """Get statistics about memories"""
        
        if character_id not in self.memories:
            return {
                "total_memories": 0,
                "by_type": {},
                "average_importance": 0.0,
                "total_accesses": 0
            }
        
        total_memories = len(self.memories[character_id])
        
        by_type = {}
        total_importance = 0.0
        total_accesses = 0
        
        for memory in self.memories[character_id].values():
            by_type[memory.memory_type.value] = by_type.get(memory.memory_type.value, 0) + 1
            total_importance += memory.importance
            total_accesses += memory.access_count
        
        return {
            "total_memories": total_memories,
            "by_type": by_type,
            "average_importance": total_importance / total_memories if total_memories > 0 else 0.0,
            "total_accesses": total_accesses
        }
    
    async def relate_memories(self, character_id: str, memory_id1: str, memory_id2: str):
        """Mark two memories as related"""
        
        if character_id not in self.memories:
            return
        
        if memory_id1 in self.memories[character_id]:
            if memory_id2 not in self.memories[character_id][memory_id1].related_memories:
                self.memories[character_id][memory_id1].related_memories.append(memory_id2)
        
        if memory_id2 in self.memories[character_id]:
            if memory_id1 not in self.memories[character_id][memory_id2].related_memories:
                self.memories[character_id][memory_id2].related_memories.append(memory_id1)
    
    async def get_related_memories(self, character_id: str, memory_id: str) -> List[Memory]:
        """Get memories related to a given memory"""
        
        memory = await self.retrieve_memory(character_id, memory_id)
        if not memory:
            return []
        
        related_memories = []
        for related_id in memory.related_memories:
            related_memory = await self.retrieve_memory(character_id, related_id)
            if related_memory:
                related_memories.append(related_memory)
        
        return related_memories