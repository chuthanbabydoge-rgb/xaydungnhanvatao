"""
Working Memory - Short-term Memory for Active Processing
Local working memory management, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
from collections import deque
import asyncio
from datetime import datetime, timedelta
import math


class WorkingMemory:
    """
    Working memory for active information processing - ENHANCED LOCAL MANAGEMENT
    Limited capacity, short-term storage for current context with advanced features
    """
    
    def __init__(self, capacity: int = 7):
        self.memories: Dict[str, Dict[str, deque]] = {}  # session_id -> memory_type -> deque
        self.capacity = capacity  # Miller's number: 7±2 items
        self.attention_weights: Dict[str, Dict[str, float]] = {}  # session_id -> memory_id -> attention
        self.context_clusters: Dict[str, List[Dict[str, Any]]] = {}  # session_id -> clusters
        self.decay_rates: Dict[str, float] = {}  # session_id -> decay rate
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize working memory"""
        self.is_initialized = True
        print("Working Memory initialized")
    
    async def shutdown(self):
        """Shutdown working memory"""
        self.is_initialized = False
        print("Working Memory shutdown")
    
    async def add_stimulus(self, session_id: str, stimulus: Any):
        """Add stimulus to working memory with advanced local processing"""
        
        if session_id not in self.memories:
            self.memories[session_id] = {
                "stimuli": deque(maxlen=self.capacity),
                "thoughts": deque(maxlen=self.capacity),
                "actions": deque(maxlen=self.capacity),
                "perceptions": deque(maxlen=self.capacity)
            }
            self.attention_weights[session_id] = {}
            self.context_clusters[session_id] = []
            self.decay_rates[session_id] = 0.05  # Default decay rate
        
        memory_id = f"{session_id}_{datetime.utcnow().timestamp()}"
        
        memory_entry = {
            "memory_id": memory_id,
            "content": stimulus.content if hasattr(stimulus, 'content') else stimulus,
            "type": stimulus.stimulus_type if hasattr(stimulus, 'stimulus_type') else "unknown",
            "timestamp": datetime.utcnow(),
            "priority": stimulus.priority if hasattr(stimulus, 'priority') else 0.5,
            "attention": 1.0  # Initial attention weight
        }
        
        # Apply attention-based priority
        priority = memory_entry["priority"]
        memory_entry["effective_priority"] = await self._calculate_effective_priority(
            session_id, memory_entry, priority
        )
        
        self.memories[session_id]["stimuli"].append(memory_entry)
        self.attention_weights[session_id][memory_id] = 1.0
        
        # Update context clusters
        await self._update_context_clusters(session_id, memory_entry)
        
        # Apply decay to existing memories
        await self._apply_decay(session_id)
    
    async def add_thought(self, session_id: str, thought: str, confidence: float = 0.5):
        """Add a thought to working memory"""
        
        if session_id not in self.memories:
            self.memories[session_id] = {
                "stimuli": deque(maxlen=self.capacity),
                "thoughts": deque(maxlen=self.capacity),
                "actions": deque(maxlen=self.capacity),
                "perceptions": deque(maxlen=self.capacity)
            }
        
        thought_entry = {
            "content": thought,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.memories[session_id]["thoughts"].append(thought_entry)
    
    async def add_action(self, session_id: str, action: Dict[str, Any]):
        """Add an action to working memory"""
        
        if session_id not in self.memories:
            self.memories[session_id] = {
                "stimuli": deque(maxlen=self.capacity),
                "thoughts": deque(maxlen=self.capacity),
                "actions": deque(maxlen=self.capacity),
                "perceptions": deque(maxlen=self.capacity)
            }
        
        action_entry = {
            **action,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.memories[session_id]["actions"].append(action_entry)
    
    async def add_perception(self, session_id: str, perception: str, confidence: float = 0.5):
        """Add a perception to working memory"""
        
        if session_id not in self.memories:
            self.memories[session_id] = {
                "stimuli": deque(maxlen=self.capacity),
                "thoughts": deque(maxlen=self.capacity),
                "actions": deque(maxlen=self.capacity),
                "perceptions": deque(maxlen=self.capacity)
            }
        
        perception_entry = {
            "content": perception,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.memories[session_id]["perceptions"].append(perception_entry)
    
    async def get_recent_stimuli(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent stimuli from working memory"""
        if session_id not in self.memories:
            return []
        
        return list(self.memories[session_id]["stimuli"])[-limit:]
    
    async def get_recent_thoughts(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent thoughts from working memory"""
        if session_id not in self.memories:
            return []
        
        return list(self.memories[session_id]["thoughts"])[-limit:]
    
    async def get_recent_actions(self, session_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent actions from working memory"""
        if session_id not in self.memories:
            return []
        
        return list(self.memories[session_id]["actions"])[-limit:]
    
    async def get_state(self, character_id: str) -> Dict[str, Any]:
        """Get current working memory state"""
        # For simplicity, return state for all sessions
        # In production, you'd want to map character_id to session_id
        
        all_memories = {}
        for session_id, memories in self.memories.items():
            all_memories[session_id] = {
                "stimuli_count": len(memories["stimuli"]),
                "thoughts_count": len(memories["thoughts"]),
                "actions_count": len(memories["actions"]),
                "perceptions_count": len(memories["perceptions"])
            }
        
        return all_memories
    
    async def clear_session(self, session_id: str):
        """Clear working memory for a session"""
        if session_id in self.memories:
            del self.memories[session_id]
    
    async def search_working_memory(
        self,
        session_id: str,
        query: str,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search working memory for matching content"""
        
        if session_id not in self.memories:
            return []
        
        results = []
        
        types_to_search = [memory_type] if memory_type else self.memories[session_id].keys()
        
        for mem_type in types_to_search:
            if mem_type in self.memories[session_id]:
                for entry in self.memories[session_id][mem_type]:
                    content = str(entry.get("content", ""))
                    if query.lower() in content.lower():
                        results.append({
                            "type": mem_type,
                            "entry": entry,
                            "relevance": self._calculate_relevance(query, content)
                        })
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        
        return results
    
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate simple relevance score"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(content_words))
        return overlap / len(query_words)
    
    async def get_context_summary(self, session_id: str) -> str:
        """Get a summary of current working memory context"""
        
        if session_id not in self.memories:
            return "No active context"
        
        summaries = []
        
        # Recent stimuli
        recent_stimuli = await self.get_recent_stimuli(session_id, 3)
        if recent_stimuli:
            stimuli_summaries = [s.get("content", "") for s in recent_stimuli]
            summaries.append(f"Recent inputs: {', '.join(stimuli_summaries)}")
        
        # Recent thoughts
        recent_thoughts = await self.get_recent_thoughts(session_id, 3)
        if recent_thoughts:
            thought_summaries = [t.get("content", "") for t in recent_thoughts]
            summaries.append(f"Recent thoughts: {', '.join(thought_summaries)}")
        
        # Recent actions
        recent_actions = await self.get_recent_actions(session_id, 3)
        if recent_actions:
            action_summaries = [a.get("action", a.get("type", "unknown")) for a in recent_actions]
            summaries.append(f"Recent actions: {', '.join(action_summaries)}")
        
        return "; ".join(summaries) if summaries else "Empty context"
    
    async def _calculate_effective_priority(
        self, 
        session_id: str, 
        memory_entry: Dict[str, Any], 
        base_priority: float
    ) -> float:
        """Calculate effective priority using local factors"""
        
        # Factor 1: Recency boost
        recency_boost = 1.0
        if session_id in self.memories and "stimuli" in self.memories[session_id]:
            # Check if this is a recent stimulus
            pass
        
        # Factor 2: Attention-based adjustment
        attention_weight = self.attention_weights.get(session_id, {}).get(
            memory_entry.get("memory_id", ""), 1.0
        )
        
        # Factor 3: Type-based adjustment
        type_boosts = {
            "text": 1.1,
            "voice": 1.15,
            "vision": 1.05,
            "emergency": 1.5,
            "critical": 1.3
        }
        type_boost = type_boosts.get(memory_entry.get("type", ""), 1.0)
        
        # Calculate effective priority
        effective_priority = base_priority * attention_weight * type_boost
        
        return max(0.0, min(effective_priority, 1.0))
    
    async def _update_context_clusters(self, session_id: str, memory_entry: Dict[str, Any]):
        """Update context clusters based on new memory"""
        
        if session_id not in self.context_clusters:
            self.context_clusters[session_id] = []
        
        # Simple clustering based on content similarity
        content = str(memory_entry.get("content", "")).lower()
        
        # Check if fits existing cluster
        for cluster in self.context_clusters[session_id]:
            cluster_similarity = self._calculate_content_similarity(
                content, cluster.get("content", "")
            )
            
            if cluster_similarity > 0.7:  # High similarity threshold
                cluster["count"] += 1
                cluster["last_updated"] = datetime.utcnow()
                cluster["recent_memories"].append(memory_entry["memory_id"])
                return
        
        # Create new cluster
        new_cluster = {
            "content": content,
            "count": 1,
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
            "recent_memories": [memory_entry["memory_id"]]
        }
        
        self.context_clusters[session_id].append(new_cluster)
        
        # Maintain cluster limit
        if len(self.context_clusters[session_id]) > 5:
            # Remove oldest/least active cluster
            self.context_clusters[session_id].sort(
                key=lambda x: (x["count"], x["last_updated"]), 
                reverse=True
            )
            self.context_clusters[session_id] = self.context_clusters[session_id][:5]
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate content similarity using local word overlap"""
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return 0.0
        
        overlap = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return overlap / union if union > 0 else 0.0
    
    async def _apply_decay(self, session_id: str):
        """Apply attention decay to memories"""
        
        if session_id not in self.attention_weights:
            return
        
        decay_rate = self.decay_rates.get(session_id, 0.05)
        
        for memory_id in list(self.attention_weights[session_id].keys()):
            current_attention = self.attention_weights[session_id][memory_id]
            decayed_attention = current_attention * (1.0 - decay_rate)
            
            self.attention_weights[session_id][memory_id] = max(0.1, decayed_attention)
    
    async def boost_attention(self, session_id: str, memory_id: str, boost: float = 0.2):
        """Boost attention for a specific memory"""
        if session_id in self.attention_weights and memory_id in self.attention_weights[session_id]:
            current = self.attention_weights[session_id][memory_id]
            self.attention_weights[session_id][memory_id] = min(1.0, current + boost)
    
    async def get_context_clusters(self, session_id: str) -> List[Dict[str, Any]]:
        """Get current context clusters"""
        if session_id not in self.context_clusters:
            return []
        
        return [
            {
                "content": cluster["content"],
                "count": cluster["count"],
                "activity": (datetime.utcnow() - cluster["last_updated"]).total_seconds()
            }
            for cluster in self.context_clusters[session_id]
        ]
    
    async def get_attention_profile(self, session_id: str) -> Dict[str, float]:
        """Get attention profile for the session"""
        if session_id not in self.attention_weights:
            return {}
        
        attention_values = list(self.attention_weights[session_id].values())
        
        if not attention_values:
            return {}
        
        return {
            "average_attention": sum(attention_values) / len(attention_values),
            "max_attention": max(attention_values),
            "min_attention": min(attention_values),
            "active_memories": len(attention_values)
        }