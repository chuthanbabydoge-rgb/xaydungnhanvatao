"""
AI Brain Service - Core Intelligence Engine
Local decision-making engine with LLM integration for language reasoning only.
All decisions are made by local engines, LLM is only used for text understanding/generation.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import asyncio
import json
from datetime import datetime, timedelta
import uuid

from .planner import Planner
from .reasoning import ReasoningEngine
from .goal_system import GoalSystem
from .need_system import NeedSystem
from .memory_retrieval import MemoryRetrieval
from .working_memory import WorkingMemory
from .long_term_memory import LongTermMemory
from .reflection import ReflectionEngine
from .learning import LearningEngine
from .social_system import SocialSystem
from .personality import PersonalityEngine
from .decision_engine import DecisionEngine
from .action_planner import ActionPlanner
from .behavior_tree import BehaviorTree
from .emotion_fusion import EmotionFusion

app = FastAPI(title="AI Brain Service", version="1.0.0")

# Initialize brain components
planner = Planner()
reasoning_engine = ReasoningEngine()
goal_system = GoalSystem()
need_system = NeedSystem()
memory_retrieval = MemoryRetrieval()
working_memory = WorkingMemory()
long_term_memory = LongTermMemory()
reflection_engine = ReflectionEngine()
learning_engine = LearningEngine()
social_system = SocialSystem()
personality_engine = PersonalityEngine()
decision_engine = DecisionEngine()
action_planner = ActionPlanner()
behavior_tree = BehaviorTree()
emotion_fusion = EmotionFusion()

# Link components together
decision_engine.set_goal_system(goal_system)
decision_engine.set_need_system(need_system)
decision_engine.set_personality(personality_engine)
decision_engine.set_emotion_fusion(emotion_fusion)
decision_engine.set_social_system(social_system)

action_planner.set_decision_engine(decision_engine)
action_planner.set_behavior_tree(behavior_tree)

emotion_fusion.set_need_system(need_system)
emotion_fusion.set_personality(personality_engine)
emotion_fusion.set_social_system(social_system)


class Stimulus(BaseModel):
    """Input stimulus for AI Brain processing"""
    stimulus_type: str  # "text", "voice", "vision", "internal"
    content: Any
    context: Optional[Dict[str, Any]] = None
    priority: float = 0.5
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BrainResponse(BaseModel):
    """Response from AI Brain"""
    actions: List[Dict[str, Any]]
    emotions: Dict[str, float]
    thoughts: List[str]
    goals: List[Dict[str, Any]]
    speech: Optional[str] = None
    animation: Optional[str] = None
    confidence: float
    processing_time: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProcessRequest(BaseModel):
    """Request to process stimulus"""
    stimulus: Stimulus
    character_id: str
    session_id: str


@app.on_event("startup")
async def startup():
    """Initialize AI Brain components"""
    print("Initializing AI Brain Service...")
    
    # Initialize all components (each wrapped to prevent cascade failures)
    components = [
        ("planner", planner.initialize()),
        ("reasoning_engine", reasoning_engine.initialize()),
        ("goal_system", goal_system.initialize()),
        ("need_system", need_system.initialize()),
        ("memory_retrieval", memory_retrieval.initialize()),
        ("working_memory", working_memory.initialize()),
        ("long_term_memory", long_term_memory.initialize()),
        ("reflection_engine", reflection_engine.initialize()),
        ("learning_engine", learning_engine.initialize()),
        ("social_system", social_system.initialize()),
        ("personality_engine", personality_engine.initialize()),
        ("decision_engine", decision_engine.initialize()),
        ("action_planner", action_planner.initialize()),
        ("behavior_tree", behavior_tree.initialize()),
        ("emotion_fusion", emotion_fusion.initialize())
    ]
    
    for name, coro in components:
        try:
            await coro
        except Exception as e:
            print(f"Warning: {name} initialization failed: {e}")
    
    print("AI Brain Service initialized")


@app.on_event("shutdown")
async def shutdown():
    """Shutdown AI Brain components"""
    print("Shutting down AI Brain Service...")
    
    components = [
        ("planner", planner.shutdown()),
        ("reasoning_engine", reasoning_engine.shutdown()),
        ("goal_system", goal_system.shutdown()),
        ("need_system", need_system.shutdown()),
        ("memory_retrieval", memory_retrieval.shutdown()),
        ("working_memory", working_memory.shutdown()),
        ("long_term_memory", long_term_memory.shutdown()),
        ("reflection_engine", reflection_engine.shutdown()),
        ("learning_engine", learning_engine.shutdown()),
        ("social_system", social_system.shutdown()),
        ("personality_engine", personality_engine.shutdown()),
        ("decision_engine", decision_engine.shutdown()),
        ("action_planner", action_planner.shutdown()),
        ("behavior_tree", behavior_tree.shutdown()),
        ("emotion_fusion", emotion_fusion.shutdown())
    ]
    
    for name, coro in components:
        try:
            await coro
        except Exception as e:
            print(f"Warning: {name} shutdown error: {e}")
    
    print("AI Brain Service shutdown complete")


@app.post("/process", response_model=BrainResponse)
async def process_stimulus(request: ProcessRequest):
    """
    Main entry point for processing stimuli through AI Brain
    This is the core decision-making pipeline - all decisions are local
    """
    start_time = datetime.utcnow()
    
    try:
        character_id = request.character_id
        session_id = request.session_id
        stimulus = request.stimulus
        
        # Step 1: Update needs based on time passage
        await need_system.update_needs(character_id)
        
        # Step 2: Store stimulus in working memory
        await working_memory.add_stimulus(session_id, stimulus)
        
        # Step 3: Retrieve relevant memories
        relevant_memories = await memory_retrieval.retrieve_memories(
            character_id, 
            stimulus.content,
            limit=5
        )
        
        # Step 4: Update emotions based on stimulus and needs
        emotions = await emotion_fusion.process_stimulus(
            character_id, 
            stimulus,
            relevant_memories
        )
        
        # Step 5: Process with reasoning engine (LLM for language only)
        if stimulus.stimulus_type in ["text", "voice"]:
            reasoning_result = await reasoning_engine.reason_about_stimulus(
                character_id,
                stimulus,
                relevant_memories,
                emotions
            )
        else:
            reasoning_result = None
        
        # Step 6: Update goals based on current state
        active_goals = await goal_system.update_goals(
            character_id,
            stimulus,
            emotions,
            reasoning_result
        )
        
        # Step 7: Make local decision (NOT LLM-dependent)
        decision = await decision_engine.make_decision(
            character_id,
            stimulus,
            emotions,
            active_goals,
            relevant_memories,
            personality_engine.get_personality(character_id)
        )
        
        # Step 8: Plan actions using behavior tree
        actions = await action_planner.plan_actions(
            character_id,
            decision,
            behavior_tree.get_active_tree(character_id)
        )
        
        # Step 9: Update social system
        if stimulus.context and "user_id" in stimulus.context:
            await social_system.update_interaction(
                character_id,
                stimulus.context["user_id"],
                stimulus,
                emotions,
                decision
            )
        
        # Step 10: Learning from experience
        await learning_engine.learn_from_interaction(
            character_id,
            stimulus,
            decision,
            actions,
            emotions
        )
        
        # Step 11: Periodic reflection
        if await reflection_engine.should_reflect(character_id):
            await reflection_engine.reflect(character_id)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Generate response
        response = BrainResponse(
            actions=actions,
            emotions=emotions,
            thoughts=reasoning_result.thoughts if reasoning_result else [],
            goals=[{"goal": g.description, "priority": g.priority} for g in active_goals],
            speech=reasoning_result.speech if reasoning_result else None,
            animation=decision.get("animation"),
            confidence=decision.get("confidence", 0.5),
            processing_time=processing_time
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Brain processing error: {str(e)}")


@app.get("/state/{character_id}")
async def get_brain_state(character_id: str):
    """Get current brain state for a character"""
    return {
        "needs": await need_system.get_needs(character_id),
        "emotions": await emotion_fusion.get_emotions(character_id),
        "goals": await goal_system.get_active_goals(character_id),
        "personality": personality_engine.get_personality(character_id),
        "social_state": await social_system.get_social_state(character_id),
        "working_memory": await working_memory.get_state(character_id),
        "timestamp": datetime.utcnow()
    }


@app.post("/goals/{character_id}")
async def set_goal(character_id: str, goal: Dict[str, Any]):
    """Manually set a goal for a character"""
    await goal_system.add_goal(character_id, goal)
    return {"status": "success", "message": "Goal added"}


@app.post("/reflect/{character_id}")
async def trigger_reflection(character_id: str):
    """Manually trigger reflection process"""
    result = await reflection_engine.reflect(character_id)
    return {"status": "success", "reflections": result}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Brain Service",
        "timestamp": datetime.utcnow()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)