"""
Working Memory - Short-term Memory for Active Processing
Local working memory management, not LLM-dependent
"""

from typing import List, Dict, Any, Optional
from collections import deque
import asyncio
from datetime import datetime


class WorkingMemory:
    """
    Working memory for active information processing
    Limited capacity, short-term storage for current context
    """
    
    def __init__(self, capacity: int = 7):
        self.memories: Dict[str, Dict[str, deque]] = {}  # session_id -> memory_type -> deque
        self.capacity = capacity  # Miller's number: 7±2 items
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
        """Add stimulus to working memory"""
        
        if session_id not in self.memories:
            self.memories[session_id] = {
                "stimuli": deque(maxlen=self.capacity),
                "thoughts": deque(maxlen=self.capacity),
                "actions": deque(maxlen=self.capacity),
                "perceptions": deque(maxlen=self.capacity)
            }
        
        memory_entry = {
            "content": stimulus.content if hasattr(stimulus, 'content') else stimulus,
            "type": stimulus.stimulus_type if hasattr(stimulus, 'stimulus_type') else "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "priority": stimulus.priority if hasattr(stimulus, 'priority') else 0.5
        }
        
        self.memories[session_id]["stimuli"].append(memory_entry)
    
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