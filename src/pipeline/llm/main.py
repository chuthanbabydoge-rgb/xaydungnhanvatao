"""
LLM Service - Natural language understanding, text generation, and dialogue management
Provides LLM capabilities for the AI character pipeline
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline as hf_pipeline
import torch
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from prometheus_client import Counter, Histogram, Gauge, start_http_server


class LLMProvider(Enum):
    """LLM provider options"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    HUGGINGFACE = "huggingface"


class TaskType(Enum):
    """Types of LLM tasks"""
    TEXT_GENERATION = "text_generation"
    TEXT_COMPLETION = "text_completion"
    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    DIALOGUE = "dialogue"
    CODE_GENERATION = "code_generation"


@dataclass
class LLMRequest:
    """Represents an LLM request"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.TEXT_GENERATION
    prompt: str = ""
    context: List[Dict[str, Any]] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "task_type": self.task_type.value,
            "prompt": self.prompt,
            "context": self.context,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class LLMResponse:
    """Represents an LLM response"""
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    task_type: TaskType = TaskType.TEXT_GENERATION
    generated_text: str = ""
    confidence: float = 0.0
    tokens_used: int = 0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id": self.response_id,
            "request_id": self.request_id,
            "task_type": self.task_type.value,
            "generated_text": self.generated_text,
            "confidence": self.confidence,
            "tokens_used": self.tokens_used,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DialogueTurn:
    """Represents a dialogue turn"""
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    speaker: str = ""
    text: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "speaker": self.speaker,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class DialogueSession:
    """Represents a dialogue session"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turns: List[DialogueTurn] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turns": [turn.to_dict() for turn in self.turns],
            "context": self.context,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }


class LLMService:
    """
    LLM Service - Provides natural language processing capabilities
    Handles text generation, dialogue management, and context maintenance
    """
    
    def __init__(self, provider: LLMProvider = LLMProvider.LOCAL, 
                 model_name: str = "gpt2", 
                 device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        self.provider = provider
        self.model_name = model_name
        self.device = device
        
        # Model and tokenizer
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        
        # Dialogue sessions
        self.sessions: Dict[str, DialogueSession] = {}
        
        # Request cache
        self.request_cache: Dict[str, LLMResponse] = {}
        
        # Metrics
        self.requests_counter = Counter('llm_requests_total', 'Total LLM requests', ['task_type', 'status'])
        self.tokens_counter = Counter('llm_tokens_total', 'Total tokens generated')
        self.generation_time = Histogram('llm_generation_seconds', 'Text generation time', ['task_type'])
        self.active_sessions = Gauge('llm_active_sessions', 'Number of active dialogue sessions')
        self.cache_hit_rate = Gauge('llm_cache_hit_rate', 'Cache hit rate')
        
        # Tracing
        self.setup_tracing()
        self.tracer = trace.get_tracer(__name__)
        
        # Logger
        self.logger = logging.getLogger("llm_service")
        
        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
    
    def setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()
        
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        tracer_provider.add_span_processor(span_processor)
    
    async def initialize(self):
        """Initialize LLM model and tokenizer"""
        with self.tracer.start_as_current_span("initialize_llm") as span:
            span.set_attribute("provider", self.provider.value)
            span.set_attribute("model_name", self.model_name)
            span.set_attribute("device", self.device)
            
            try:
                if self.provider == LLMProvider.LOCAL:
                    self.logger.info(f"Loading local model: {self.model_name}")
                    
                    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                    self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
                    self.model.to(self.device)
                    
                    # Set padding token if not set
                    if self.tokenizer.pad_token is None:
                        self.tokenizer.pad_token = self.tokenizer.eos_token
                    
                    self.logger.info("Local model loaded successfully")
                    
                elif self.provider == LLMProvider.HUGGINGFACE:
                    self.logger.info(f"Loading HuggingFace pipeline: {self.model_name}")
                    self.pipeline = hf_pipeline("text-generation", model=self.model_name, device=self.device)
                    self.logger.info("HuggingFace pipeline loaded successfully")
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM: {e}")
                span.record_exception(e)
                return False
    
    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        """Generate text using LLM"""
        with self.tracer.start_as_current_span("generate_text") as span:
            import time
            start_time = time.time()
            
            span.set_attribute("request_id", request.request_id)
            span.set_attribute("task_type", request.task_type.value)
            
            response = LLMResponse(
                request_id=request.request_id,
                task_type=request.task_type
            )
            
            try:
                # Check cache
                cache_key = self._get_cache_key(request)
                if cache_key in self.request_cache:
                    self.cache_hits += 1
                    cached_response = self.request_cache[cache_key]
                    self._update_cache_metrics()
                    return cached_response
                
                self.cache_misses += 1
                
                # Get generation parameters
                max_length = request.parameters.get("max_length", 100)
                temperature = request.parameters.get("temperature", 0.7)
                top_p = request.parameters.get("top_p", 0.9)
                num_return_sequences = request.parameters.get("num_return_sequences", 1)
                
                # Prepare input
                if self.provider == LLMProvider.LOCAL:
                    inputs = self.tokenizer(request.prompt, return_tensors="pt", padding=True)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    # Generate
                    with torch.no_grad():
                        outputs = self.model.generate(
                            **inputs,
                            max_length=max_length,
                            temperature=temperature,
                            top_p=top_p,
                            num_return_sequences=num_return_sequences,
                            do_sample=True,
                            pad_token_id=self.tokenizer.pad_token_id
                        )
                    
                    # Decode
                    generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                    tokens_used = outputs.shape[1]
                    
                elif self.provider == LLMProvider.HUGGINGFACE:
                    result = self.pipeline(
                        request.prompt,
                        max_length=max_length,
                        temperature=temperature,
                        top_p=top_p,
                        num_return_sequences=num_return_sequences
                    )
                    generated_text = result[0]["generated_text"]
                    tokens_used = len(self.tokenizer.encode(generated_text)) if self.tokenizer else len(generated_text.split())
                
                # Calculate confidence (simplified)
                confidence = self._calculate_confidence(generated_text, request)
                
                # Update response
                response.generated_text = generated_text
                response.confidence = confidence
                response.tokens_used = tokens_used
                response.processing_time = time.time() - start_time
                
                # Cache response
                self.request_cache[cache_key] = response
                
                # Update metrics
                self.requests_counter.labels(task_type=request.task_type.value, status="success").inc()
                self.tokens_counter.inc(tokens_used)
                self.generation_time.labels(task_type=request.task_type.value).observe(response.processing_time)
                self._update_cache_metrics()
                
                span.set_attribute("tokens_used", tokens_used)
                span.set_attribute("processing_time", response.processing_time)
                span.set_attribute("confidence", confidence)
                
                self.logger.info(f"Generated text for request {request.request_id}")
                return response
                
            except Exception as e:
                self.logger.error(f"Text generation error: {e}")
                response.processing_time = time.time() - start_time
                self.requests_counter.labels(task_type=request.task_type.value, status="error").inc()
                span.record_exception(e)
                return response
    
    async def complete_text(self, prompt: str, max_tokens: int = 50) -> str:
        """Complete text with context"""
        request = LLMRequest(
            task_type=TaskType.TEXT_COMPLETION,
            prompt=prompt,
            parameters={"max_length": max_tokens}
        )
        
        response = await self.generate_text(request)
        return response.generated_text
    
    async def answer_question(self, question: str, context: str = "") -> str:
        """Answer a question with optional context"""
        prompt = f"Context: {context}\n\nQuestion: {question}\n\nAnswer:" if context else f"Question: {question}\n\nAnswer:"
        
        request = LLMRequest(
            task_type=TaskType.QUESTION_ANSWERING,
            prompt=prompt,
            parameters={"max_length": 100}
        )
        
        response = await self.generate_text(request)
        return response.generated_text
    
    async def summarize_text(self, text: str, max_length: int = 50) -> str:
        """Summarize text"""
        prompt = f"Summarize the following text:\n\n{text}\n\nSummary:"
        
        request = LLMRequest(
            task_type=TaskType.SUMMARIZATION,
            prompt=prompt,
            parameters={"max_length": max_length}
        )
        
        response = await self.generate_text(request)
        return response.generated_text
    
    async def create_dialogue_session(self, context: Dict[str, Any] = None) -> str:
        """Create a new dialogue session"""
        session = DialogueSession(context=context or {})
        self.sessions[session.session_id] = session
        self.active_sessions.set(len(self.sessions))
        
        self.logger.info(f"Created dialogue session {session.session_id}")
        return session.session_id
    
    async def add_dialogue_turn(self, session_id: str, speaker: str, text: str, metadata: Dict[str, Any] = None) -> str:
        """Add a turn to a dialogue session"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        turn = DialogueTurn(
            speaker=speaker,
            text=text,
            metadata=metadata or {}
        )
        
        self.sessions[session_id].turns.append(turn)
        self.sessions[session_id].last_activity = datetime.utcnow()
        
        return turn.turn_id
    
    async def generate_dialogue_response(self, session_id: str, user_input: str) -> str:
        """Generate a response in dialogue context"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        # Add user turn
        await self.add_dialogue_turn(session_id, "user", user_input)
        
        # Build dialogue context
        dialogue_history = "\n".join([
            f"{turn.speaker}: {turn.text}" 
            for turn in session.turns[-5:]  # Last 5 turns
        ])
        
        prompt = f"Dialogue history:\n{dialogue_history}\n\nAI:"
        
        request = LLMRequest(
            task_type=TaskType.DIALOGUE,
            prompt=prompt,
            context=[{"speaker": turn.speaker, "text": turn.text} for turn in session.turns],
            parameters={"max_length": 100}
        )
        
        response = await self.generate_text(request)
        
        # Add AI turn
        await self.add_dialogue_turn(session_id, "ai", response.generated_text)
        
        return response.generated_text
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        # Simple sentiment analysis using keyword matching
        # In production, use a proper sentiment analysis model
        
        positive_words = ["good", "great", "excellent", "happy", "love", "wonderful", "amazing"]
        negative_words = ["bad", "terrible", "awful", "sad", "hate", "horrible", "poor"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            confidence = min(positive_count / (positive_count + negative_count + 1), 0.9)
        elif negative_count > positive_count:
            sentiment = "negative"
            confidence = min(negative_count / (positive_count + negative_count + 1), 0.9)
        else:
            sentiment = "neutral"
            confidence = 0.5
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_count": positive_count,
            "negative_count": negative_count
        }
    
    def _get_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for request"""
        import hashlib
        key_data = f"{request.task_type.value}:{request.prompt}:{json.dumps(request.parameters, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _calculate_confidence(self, generated_text: str, request: LLMRequest) -> float:
        """Calculate confidence score for generated text"""
        # Simplified confidence calculation
        # In production, use model-specific confidence measures
        
        if not generated_text:
            return 0.0
        
        # Check for coherent text
        words = generated_text.split()
        if len(words) < 3:
            return 0.3
        
        # Check for relevance to prompt
        prompt_words = set(request.prompt.lower().split())
        generated_words = set(generated_text.lower().split())
        overlap = len(prompt_words & generated_words)
        
        relevance_score = min(overlap / max(len(prompt_words), 1), 1.0)
        
        # Base confidence with relevance boost
        confidence = 0.5 + (relevance_score * 0.3)
        
        return min(confidence, 1.0)
    
    def _update_cache_metrics(self):
        """Update cache-related metrics"""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests > 0:
            hit_rate = self.cache_hits / total_requests
            self.cache_hit_rate.set(hit_rate)
    
    async def cleanup_session(self, session_id: str):
        """Cleanup a dialogue session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.active_sessions.set(len(self.sessions))
            self.logger.info(f"Cleaned up session {session_id}")


# FastAPI application
app = FastAPI(title="LLM Service")
llm_service: Optional[LLMService] = None


class TextGenerationInput(BaseModel):
    """Input for text generation"""
    prompt: str
    task_type: str = "text_generation"
    parameters: Dict[str, Any] = {}
    context: List[Dict[str, Any]] = []


class DialogueInput(BaseModel):
    """Input for dialogue"""
    session_id: Optional[str] = None
    user_input: str
    context: Dict[str, Any] = {}


class SentimentInput(BaseModel):
    """Input for sentiment analysis"""
    text: str


@app.on_event("startup")
async def startup_event():
    """Initialize LLM service on startup"""
    global llm_service
    llm_service = LLMService(provider=LLMProvider.LOCAL, model_name="gpt2")
    await llm_service.initialize()
    
    # Start metrics server
    start_http_server(8005)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup LLM service on shutdown"""
    if llm_service:
        # Cleanup if needed
        pass


@app.get("/status")
async def get_status():
    """Get LLM service status"""
    return {
        "status": "running",
        "provider": llm_service.provider.value if llm_service else "not_initialized",
        "model_name": llm_service.model_name if llm_service else "",
        "device": llm_service.device if llm_service else "",
        "active_sessions": len(llm_service.sessions) if llm_service else 0,
        "cache_hit_rate": llm_service.cache_hit_rate._value.get() if llm_service else 0.0
    }


@app.post("/generate")
async def generate_text_endpoint(input_data: TextGenerationInput):
    """Generate text using LLM"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    request = LLMRequest(
        task_type=TaskType(input_data.task_type),
        prompt=input_data.prompt,
        context=input_data.context,
        parameters=input_data.parameters
    )
    
    response = await llm_service.generate_text(request)
    
    return response.to_dict()


@app.post("/complete")
async def complete_text_endpoint(prompt: str, max_tokens: int = 50):
    """Complete text"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    completed_text = await llm_service.complete_text(prompt, max_tokens)
    
    return {"completed_text": completed_text}


@app.post("/answer")
async def answer_question_endpoint(question: str, context: str = ""):
    """Answer a question"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    answer = await llm_service.answer_question(question, context)
    
    return {"answer": answer}


@app.post("/summarize")
async def summarize_text_endpoint(text: str, max_length: int = 50):
    """Summarize text"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    summary = await llm_service.summarize_text(text, max_length)
    
    return {"summary": summary}


@app.post("/dialogue/session")
async def create_dialogue_session_endpoint(context: Dict[str, Any] = None):
    """Create a dialogue session"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    session_id = await llm_service.create_dialogue_session(context)
    
    return {"session_id": session_id, "status": "created"}


@app.post("/dialogue/response")
async def generate_dialogue_response_endpoint(dialogue_input: DialogueInput):
    """Generate dialogue response"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    if dialogue_input.session_id:
        session_id = dialogue_input.session_id
    else:
        session_id = await llm_service.create_dialogue_session(dialogue_input.context)
    
    response = await llm_service.generate_dialogue_response(session_id, dialogue_input.user_input)
    
    return {
        "session_id": session_id,
        "response": response
    }


@app.post("/sentiment")
async def analyze_sentiment_endpoint(sentiment_input: SentimentInput):
    """Analyze sentiment"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    sentiment_result = await llm_service.analyze_sentiment(sentiment_input.text)
    
    return sentiment_result


@app.websocket("/dialogue/ws")
async def dialogue_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time dialogue"""
    await websocket.accept()
    
    if not llm_service:
        await websocket.close(code=1000, reason="LLM service not initialized")
        return
    
    session_id = await llm_service.create_dialogue_session()
    
    try:
        while True:
            data = await websocket.receive_json()
            user_input = data.get("user_input", "")
            
            if user_input:
                response = await llm_service.generate_dialogue_response(session_id, user_input)
                
                await websocket.send_json({
                    "session_id": session_id,
                    "response": response,
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except Exception as e:
        llm_service.logger.error(f"Dialogue WebSocket error: {e}")
    finally:
        await llm_service.cleanup_session(session_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
