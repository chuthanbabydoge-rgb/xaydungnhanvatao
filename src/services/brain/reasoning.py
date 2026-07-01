"""
Reasoning Engine - Language Understanding and Generation
LLM is ONLY used for language reasoning (text understanding/generation)
All decision-making is done by local engines
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
from datetime import datetime
import json


class ReasoningType(Enum):
    """Types of reasoning"""
    DEDUCTIVE = "deductive"  # General to specific
    INDUCTIVE = "inductive"  # Specific to general
    ABDUCTIVE = "abductive"  # Best explanation
    CAUSAL = "causal"  # Cause and effect
    ANALOGICAL = "analogical"  # Pattern matching


class ReasoningResult:
    """Result from reasoning engine"""
    def __init__(self, thoughts: List[str], intent: str, entities: Dict[str, Any], 
                 speech: Optional[str] = None, confidence: float = 0.5):
        self.thoughts = thoughts
        self.intent = intent
        self.entities = entities
        self.speech = speech
        self.confidence = confidence
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "thoughts": self.thoughts,
            "intent": self.intent,
            "entities": self.entities,
            "speech": self.speech,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


class ReasoningEngine:
    """
    Reasoning engine for language understanding and generation
    Uses LLM ONLY for text processing, not for decision-making
    """
    
    def __init__(self):
        self.llm_client = None  # Will be initialized with LLM service
        self.is_initialized = False
        self.reasoning_cache = {}
    
    async def initialize(self):
        """Initialize reasoning engine"""
        # Setup LLM client (for language only)
        import sys, os
        llm_path = os.path.join(os.path.dirname(__file__), '..', 'llm')
        if llm_path not in sys.path:
            sys.path.insert(0, llm_path)
        from app.services.llm_service import LLMService
        self.llm_client = LLMService()
        await self.llm_client.initialize()
        
        self.is_initialized = True
        print("Reasoning Engine initialized")
    
    async def shutdown(self):
        """Shutdown reasoning engine"""
        if self.llm_client:
            await self.llm_client.shutdown()
        
        self.is_initialized = False
        print("Reasoning Engine shutdown")
    
    async def reason_about_stimulus(
        self,
        character_id: str,
        stimulus: Any,
        memories: List[Dict[str, Any]],
        emotions: Dict[str, float]
    ) -> ReasoningResult:
        """
        Reason about a stimulus using LLM for language understanding only
        This does NOT make decisions - only processes language
        """
        
        if stimulus.stimulus_type not in ["text", "voice"]:
            # Non-language stimuli don't need LLM reasoning
            return ReasoningResult(
                thoughts=["Non-language stimulus received"],
                intent="perceive",
                entities={},
                confidence=0.5
            )
        
        # Extract text content
        text_content = stimulus.content if isinstance(stimulus.content, str) else str(stimulus.content)
        
        # Use LLM for language understanding (NOT decision making)
        reasoning_result = await self._analyze_text_with_llm(
            character_id,
            text_content,
            memories,
            emotions
        )
        
        return reasoning_result
    
    async def _analyze_text_with_llm(
        self,
        character_id: str,
        text: str,
        memories: List[Dict[str, Any]],
        emotions: Dict[str, float]
    ) -> ReasoningResult:
        """
        Use LLM to analyze text - understanding only, no decision making
        """
        
        # Create prompt for LLM (focused on understanding, not decisions)
        prompt = self._create_analysis_prompt(text, memories, emotions)
        
        # Call LLM for text analysis
        llm_response = await self.llm_client.generate_response(
            prompt=prompt,
            character_id=character_id,
            max_tokens=500
        )
        
        # Parse LLM response
        parsed_result = self._parse_llm_response(llm_response)
        
        return ReasoningResult(
            thoughts=parsed_result.get("thoughts", []),
            intent=parsed_result.get("intent", "unknown"),
            entities=parsed_result.get("entities", {}),
            speech=parsed_result.get("speech"),  # Generated speech response
            confidence=parsed_result.get("confidence", 0.5)
        )
    
    def _create_analysis_prompt(
        self,
        text: str,
        memories: List[Dict[str, Any]],
        emotions: Dict[str, float]
    ) -> str:
        """Create prompt for LLM text analysis"""
        
        prompt = f"""Analyze the following text. Provide:
1. Intent (what the person wants)
2. Entities (important people, objects, locations)
3. Thoughts (brief reasoning)
4. Appropriate response (if a response is expected)

Text: "{text}"

Current emotional state: {json.dumps(emotions, indent=2)}

Relevant context from memory:
{self._format_memories(memories)}

Respond in JSON format:
{{
    "intent": "intent_here",
    "entities": {{"entity_type": "value"}},
    "thoughts": ["thought1", "thought2"],
    "speech": "appropriate response if needed",
    "confidence": 0.0-1.0
}}"""
        
        return prompt
    
    def _format_memories(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories for prompt"""
        if not memories:
            return "No relevant memories."
        
        formatted = []
        for memory in memories[:3]:  # Limit to 3 most relevant
            formatted.append(f"- {memory.get('content', 'memory')}")
        
        return "\n".join(formatted)
    
    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM response"""
        try:
            # Try to parse as JSON
            parsed = json.loads(llm_response)
            return parsed
        except json.JSONDecodeError:
            # Fallback parsing
            return {
                "intent": "unknown",
                "entities": {},
                "thoughts": [llm_response],
                "speech": llm_response,
                "confidence": 0.3
            }
    
    async def generate_speech(
        self,
        character_id: str,
        intent: str,
        context: Dict[str, Any],
        personality: Dict[str, float]
    ) -> str:
        """
        Generate speech using LLM based on intent and context
        This is purely language generation, not decision making
        """
        
        prompt = f"""Generate a natural response for the following situation:

Intent: {intent}
Context: {json.dumps(context, indent=2)}
Personality: {json.dumps(personality, indent=2)}

Generate a brief, natural response (1-2 sentences):"""
        
        response = await self.llm_client.generate_response(
            prompt=prompt,
            character_id=character_id,
            max_tokens=100
        )
        
        return response.strip()
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text using LLM"""
        
        prompt = f"""Extract entities from the following text. Identify:
- People
- Objects
- Locations
- Actions
- Times

Text: "{text}"

Respond in JSON format:
{{
    "people": [],
    "objects": [],
    "locations": [],
    "actions": [],
    "times": []
}}"""
        
        response = await self.llm_client.generate_response(
            prompt=prompt,
            character_id="entity_extraction",
            max_tokens=200
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "people": [],
                "objects": [],
                "locations": [],
                "actions": [],
                "times": []
            }
    
    async def detect_intent(self, text: str) -> str:
        """Detect intent from text using LLM"""
        
        prompt = f"""Detect the intent of the following text. 
Possible intents: greeting, question, request, command, statement, farewell, emotion_expression

Text: "{text}"

Respond with just the intent name:"""
        
        response = await self.llm_client.generate_response(
            prompt=prompt,
            character_id="intent_detection",
            max_tokens=50
        )
        
        return response.strip().lower()
    
    async def apply_reasoning_type(
        self,
        reasoning_type: ReasoningType,
        premises: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Apply specific reasoning type
        This is still language-based reasoning, not decision making
        """
        
        if reasoning_type == ReasoningType.DEDUCTIVE:
            return await self._deductive_reasoning(premises, context)
        elif reasoning_type == ReasoningType.INDUCTIVE:
            return await self._inductive_reasoning(premises, context)
        elif reasoning_type == ReasoningType.ABDUCTIVE:
            return await self._abductive_reasoning(premises, context)
        elif reasoning_type == ReasoningType.CAUSAL:
            return await self._causal_reasoning(premises, context)
        elif reasoning_type == ReasoningType.ANALOGICAL:
            return await self._analogical_reasoning(premises, context)
        else:
            return []
    
    async def _deductive_reasoning(self, premises: List[str], context: Dict[str, Any]) -> List[str]:
        """Deductive reasoning - general to specific"""
        prompt = f"""Apply deductive reasoning to these premises:
{json.dumps(premises, indent=2)}

Context: {json.dumps(context, indent=2) if context else "None"}

Provide logical conclusions:"""
        
        response = await self.llm_client.generate_response(
            prompt=prompt,
            character_id="reasoning",
            max_tokens=300
        )
        
        return [line.strip() for line in response.split('\n') if line.strip()]
    
    async def _inductive_reasoning(self, premises: List[str], context: Dict[str, Any]) -> List[str]:
        """Inductive reasoning - specific to general"""
        prompt = f"""Apply inductive reasoning to these observations:
{json.dumps(premises, indent=2)}

Context: {json.dumps(context, indent=2) if context else "None"}

Provide general patterns or rules:"""
        
        response = await self.llm_client.generate_response(
            prompt=prompt,
            character_id="reasoning",
            max_tokens=300
        )
        
        return [line.strip() for line in response.split('\n') if line.strip()]
    
    async def _abductive_reasoning(self, premises: List[str], context: Dict[str, Any]) -> List[str]:
        """Abductive reasoning - best explanation"""
        prompt = f"""Apply abductive reasoning to find the best explanation:
{json.dumps(premises, indent=2)}

Context: {json.dumps(context, indent=2) if context else "None"}

Provide the most likely explanations:"""
        
        response = await self.llm_client.generate_response(
            prompt=prompt,
            character_id="reasoning",
            max_tokens=300
        )
        
        return [line.strip() for line in response.split('\n') if line.strip()]
    
    async def _causal_reasoning(self, premises: List[str], context: Dict[str, Any]) -> List[str]:
        """Causal reasoning - cause and effect"""
        prompt = f"""Apply causal reasoning to identify causes and effects:
{json.dumps(premises, indent=2)}

Context: {json.dumps(context, indent=2) if context else "None"}

Provide cause-effect relationships:"""
        
        response = await self.llm_client.generate_response(
            prompt=prompt,
            character_id="reasoning",
            max_tokens=300
        )
        
        return [line.strip() for line in response.split('\n') if line.strip()]
    
    async def _analogical_reasoning(self, premises: List[str], context: Dict[str, Any]) -> List[str]:
        """Analogical reasoning - pattern matching"""
        prompt = f"""Apply analogical reasoning to find similar patterns:
{json.dumps(premises, indent=2)}

Context: {json.dumps(context, indent=2) if context else "None"}

Provide analogous situations or patterns:"""
        
        response = await self.llm_client.generate_response(
            prompt=prompt,
            character_id="reasoning",
            max_tokens=300
        )
        
        return [line.strip() for line in response.split('\n') if line.strip()]