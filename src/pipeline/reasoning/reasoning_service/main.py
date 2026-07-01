"""
Reasoning Service - Logical inference, decision making, and context understanding
Provides reasoning capabilities for the AI character pipeline
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from prometheus_client import Counter, Histogram, Gauge, start_http_server


class ReasoningType(Enum):
    """Types of reasoning operations"""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    CAUSAL = "causal"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    ANALOGICAL = "analogical"
    CONTEXTUAL = "contextual"


class InferenceStatus(Enum):
    """Status of inference operations"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class Fact:
    """Represents a fact in the knowledge base"""
    fact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    statement: str = ""
    confidence: float = 1.0
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    validity_period: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "statement": self.statement,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "validity_period": str(self.validity_period) if self.validity_period else None,
            "metadata": self.metadata
        }


@dataclass
class Rule:
    """Represents a reasoning rule"""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    premises: List[str] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 1.0
    reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "premises": self.premises,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "reasoning_type": self.reasoning_type.value,
            "metadata": self.metadata
        }


@dataclass
class Inference:
    """Represents an inference result"""
    inference_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE
    premises: List[Fact] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    status: InferenceStatus = InferenceStatus.PENDING
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "inference_id": self.inference_id,
            "reasoning_type": self.reasoning_type.value,
            "premises": [fact.to_dict() for fact in self.premises],
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "status": self.status.value,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Decision:
    """Represents a decision made by reasoning"""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: Dict[str, Any] = field(default_factory=dict)
    alternatives: List[str] = field(default_factory=list)
    selected_alternative: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "context": self.context,
            "alternatives": self.alternatives,
            "selected_alternative": self.selected_alternative,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


class ReasoningService:
    """
    Reasoning Service - Provides logical inference and decision making
    Handles various types of reasoning and context understanding
    """
    
    def __init__(self):
        # Knowledge base
        self.facts: Dict[str, Fact] = {}
        self.rules: Dict[str, Rule] = {}
        
        # Inference cache
        self.inferences: Dict[str, Inference] = {}
        self.decisions: Dict[str, Decision] = {}
        
        # Working memory
        self.working_context: Dict[str, Any] = {}
        
        # Metrics
        self.inferences_counter = Counter('reasoning_inferences_total', 'Total inferences', ['type', 'status'])
        self.decisions_counter = Counter('reasoning_decisions_total', 'Total decisions')
        self.reasoning_time = Histogram('reasoning_processing_seconds', 'Reasoning processing time', ['type'])
        self.facts_count = Gauge('reasoning_facts_count', 'Number of facts in knowledge base')
        self.rules_count = Gauge('reasoning_rules_count', 'Number of rules')
        
        # Tracing
        self.setup_tracing()
        self.tracer = trace.get_tracer(__name__)
        
        # Logger
        self.logger = logging.getLogger("reasoning_service")
    
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
        """Initialize reasoning service with default rules and facts"""
        with self.tracer.start_as_current_span("initialize_reasoning") as span:
            try:
                # Load default reasoning rules
                await self._load_default_rules()
                
                # Load default facts
                await self._load_default_facts()
                
                self.logger.info("Reasoning service initialized successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize reasoning service: {e}")
                span.record_exception(e)
                return False
    
    async def _load_default_rules(self):
        """Load default reasoning rules"""
        default_rules = [
            Rule(
                name="Object Permanence",
                premises=["If an object exists at location A", "If object moves to location B"],
                conclusion="Object no longer exists at location A",
                reasoning_type=ReasoningType.CAUSAL,
                confidence=0.95
            ),
            Rule(
                name="Causality",
                premises=["If event A occurs", "If event A typically causes event B"],
                conclusion="Event B is likely to occur",
                reasoning_type=ReasoningType.CAUSAL,
                confidence=0.85
            ),
            Rule(
                name="Temporal Sequence",
                premises=["If event A precedes event B", "If event B precedes event C"],
                conclusion="Event A precedes event C",
                reasoning_type=ReasoningType.TEMPORAL,
                confidence=0.90
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
        
        self.rules_count.set(len(self.rules))
    
    async def _load_default_facts(self):
        """Load default facts"""
        default_facts = [
            Fact(
                statement="Objects continue to exist even when not observed",
                confidence=0.99,
                source="axiom"
            ),
            Fact(
                statement="Events have temporal order",
                confidence=0.99,
                source="axiom"
            ),
            Fact(
                statement="Physical objects obey causality",
                confidence=0.95,
                source="physics"
            )
        ]
        
        for fact in default_facts:
            self.facts[fact.fact_id] = fact
        
        self.facts_count.set(len(self.facts))
    
    async def add_fact(self, fact: Fact) -> str:
        """Add a fact to the knowledge base"""
        with self.tracer.start_as_current_span("add_fact") as span:
            span.set_attribute("fact_id", fact.fact_id)
            
            self.facts[fact.fact_id] = fact
            self.facts_count.set(len(self.facts))
            
            self.logger.info(f"Added fact {fact.fact_id}")
            return fact.fact_id
    
    async def add_rule(self, rule: Rule) -> str:
        """Add a reasoning rule"""
        with self.tracer.start_as_current_span("add_rule") as span:
            span.set_attribute("rule_id", rule.rule_id)
            
            self.rules[rule.rule_id] = rule
            self.rules_count.set(len(self.rules))
            
            self.logger.info(f"Added rule {rule.rule_id}")
            return rule.rule_id
    
    async def deductive_reasoning(self, premises: List[str]) -> Inference:
        """Perform deductive reasoning"""
        with self.tracer.start_as_current_span("deductive_reasoning") as span:
            import time
            start_time = time.time()
            
            inference = Inference(
                reasoning_type=ReasoningType.DEDUCTIVE,
                premises=[Fact(statement=p) for p in premises],
                status=InferenceStatus.PROCESSING
            )
            
            try:
                # Find applicable rules
                applicable_rules = []
                for rule in self.rules.values():
                    if rule.reasoning_type == ReasoningType.DEDUCTIVE:
                        if all(any(premise in fact.statement for fact in self.facts.values()) 
                               for premise in rule.premises):
                            applicable_rules.append(rule)
                
                # Apply rules to derive conclusions
                conclusions = []
                for rule in applicable_rules:
                    conclusions.append({
                        "conclusion": rule.conclusion,
                        "confidence": rule.confidence,
                        "rule_id": rule.rule_id
                    })
                
                if conclusions:
                    # Select highest confidence conclusion
                    best_conclusion = max(conclusions, key=lambda x: x["confidence"])
                    inference.conclusion = best_conclusion["conclusion"]
                    inference.confidence = best_conclusion["confidence"]
                    inference.status = InferenceStatus.COMPLETED
                else:
                    inference.status = InferenceStatus.INSUFFICIENT_DATA
                
                inference.processing_time = time.time() - start_time
                
                # Update metrics
                self.reasoning_time.labels(type="deductive").observe(inference.processing_time)
                self.inferences_counter.labels(type="deductive", status=inference.status.value).inc()
                
                span.set_attribute("conclusion", inference.conclusion)
                span.set_attribute("confidence", inference.confidence)
                
                self.inferences[inference.inference_id] = inference
                return inference
                
            except Exception as e:
                self.logger.error(f"Deductive reasoning error: {e}")
                inference.status = InferenceStatus.FAILED
                span.record_exception(e)
                return inference
    
    async def inductive_reasoning(self, observations: List[str]) -> Inference:
        """Perform inductive reasoning"""
        with self.tracer.start_as_current_span("inductive_reasoning") as span:
            import time
            start_time = time.time()
            
            inference = Inference(
                reasoning_type=ReasoningType.INDUCTIVE,
                premises=[Fact(statement=obs) for obs in observations],
                status=InferenceStatus.PROCESSING
            )
            
            try:
                # Analyze patterns in observations
                pattern_frequencies = {}
                for obs in observations:
                    words = obs.lower().split()
                    for word in words:
                        pattern_frequencies[word] = pattern_frequencies.get(word, 0) + 1
                
                # Generate generalization based on patterns
                if pattern_frequencies:
                    most_common = max(pattern_frequencies.items(), key=lambda x: x[1])
                    generalization = f"Generally, {most_common[0]} is observed in these contexts"
                    inference.conclusion = generalization
                    inference.confidence = min(most_common[1] / len(observations), 0.9)
                    inference.status = InferenceStatus.COMPLETED
                else:
                    inference.status = InferenceStatus.INSUFFICIENT_DATA
                
                inference.processing_time = time.time() - start_time
                
                # Update metrics
                self.reasoning_time.labels(type="inductive").observe(inference.processing_time)
                self.inferences_counter.labels(type="inductive", status=inference.status.value).inc()
                
                span.set_attribute("conclusion", inference.conclusion)
                span.set_attribute("confidence", inference.confidence)
                
                self.inferences[inference.inference_id] = inference
                return inference
                
            except Exception as e:
                self.logger.error(f"Inductive reasoning error: {e}")
                inference.status = InferenceStatus.FAILED
                span.record_exception(e)
                return inference
    
    async def causal_reasoning(self, events: List[Dict[str, Any]]) -> Inference:
        """Perform causal reasoning"""
        with self.tracer.start_as_current_span("causal_reasoning") as span:
            import time
            start_time = time.time()
            
            inference = Inference(
                reasoning_type=ReasoningType.CAUSAL,
                status=InferenceStatus.PROCESSING
            )
            
            try:
                # Analyze temporal sequence of events
                sorted_events = sorted(events, key=lambda x: x.get("timestamp", ""))
                
                # Identify potential causal relationships
                causal_chains = []
                for i in range(len(sorted_events) - 1):
                    event_a = sorted_events[i]
                    event_b = sorted_events[i + 1]
                    
                    # Check for causal patterns
                    if self._is_likely_causal(event_a, event_b):
                        causal_chains.append({
                            "cause": event_a,
                            "effect": event_b,
                            "confidence": 0.7
                        })
                
                if causal_chains:
                    strongest_causal = max(causal_chains, key=lambda x: x["confidence"])
                    inference.conclusion = f"Event '{strongest_causal['cause'].get('type', 'unknown')}' likely causes '{strongest_causal['effect'].get('type', 'unknown')}'"
                    inference.confidence = strongest_causal["confidence"]
                    inference.status = InferenceStatus.COMPLETED
                else:
                    inference.status = InferenceStatus.INSUFFICIENT_DATA
                
                inference.processing_time = time.time() - start_time
                
                # Update metrics
                self.reasoning_time.labels(type="causal").observe(inference.processing_time)
                self.inferences_counter.labels(type="causal", status=inference.status.value).inc()
                
                span.set_attribute("conclusion", inference.conclusion)
                span.set_attribute("confidence", inference.confidence)
                
                self.inferences[inference.inference_id] = inference
                return inference
                
            except Exception as e:
                self.logger.error(f"Causal reasoning error: {e}")
                inference.status = InferenceStatus.FAILED
                span.record_exception(e)
                return inference
    
    def _is_likely_causal(self, event_a: Dict[str, Any], event_b: Dict[str, Any]) -> bool:
        """Check if two events are likely causally related"""
        # Simplified causal relationship detection
        # In production, use more sophisticated causal inference methods
        
        # Check temporal proximity
        if "timestamp" in event_a and "timestamp" in event_b:
            try:
                time_a = datetime.fromisoformat(event_a["timestamp"])
                time_b = datetime.fromisoformat(event_b["timestamp"])
                time_diff = (time_b - time_a).total_seconds()
                
                # Events within 5 seconds might be causally related
                if 0 < time_diff < 5:
                    return True
            except:
                pass
        
        # Check spatial proximity
        if "position" in event_a and "position" in event_b:
            pos_a = event_a["position"]
            pos_b = event_b["position"]
            
            if isinstance(pos_a, list) and isinstance(pos_b, list):
                distance = sum((a - b) ** 2 for a, b in zip(pos_a, pos_b)) ** 0.5
                if distance < 2.0:  # Within 2 meters
                    return True
        
        return False
    
    async def make_decision(self, context: Dict[str, Any], alternatives: List[str]) -> Decision:
        """Make a decision based on context and alternatives"""
        with self.tracer.start_as_current_span("make_decision") as span:
            import time
            start_time = time.time()
            
            decision = Decision(
                context=context,
                alternatives=alternatives
            )
            
            try:
                # Analyze context
                context_score = {}
                for alternative in alternatives:
                    score = await self._evaluate_alternative(alternative, context)
                    context_score[alternative] = score
                
                # Select best alternative
                if context_score:
                    best_alternative = max(context_score.items(), key=lambda x: x[1])
                    decision.selected_alternative = best_alternative[0]
                    decision.confidence = best_alternative[1]
                    decision.reasoning = f"Selected based on context analysis with score {best_alternative[1]:.2f}"
                else:
                    decision.selected_alternative = alternatives[0] if alternatives else ""
                    decision.confidence = 0.5
                    decision.reasoning = "Default selection due to insufficient analysis"
                
                decision.timestamp = datetime.utcnow()
                
                # Update metrics
                self.decisions_counter.inc()
                
                span.set_attribute("selected_alternative", decision.selected_alternative)
                span.set_attribute("confidence", decision.confidence)
                
                self.decisions[decision.decision_id] = decision
                return decision
                
            except Exception as e:
                self.logger.error(f"Decision making error: {e}")
                span.record_exception(e)
                return decision
    
    async def _evaluate_alternative(self, alternative: str, context: Dict[str, Any]) -> float:
        """Evaluate an alternative based on context"""
        score = 0.5  # Base score
        
        # Simple evaluation based on context keywords
        alternative_lower = alternative.lower()
        context_str = json.dumps(context).lower()
        
        # Check for positive keywords
        positive_keywords = ["best", "optimal", "efficient", "fast", "effective"]
        for keyword in positive_keywords:
            if keyword in alternative_lower:
                score += 0.1
        
        # Check for context relevance
        for key, value in context.items():
            if str(value).lower() in alternative_lower:
                score += 0.05
        
        return min(score, 1.0)
    
    async def update_context(self, context_update: Dict[str, Any]):
        """Update working context"""
        self.working_context.update(context_update)
        self.logger.info(f"Updated context with {len(context_update)} items")
    
    async def get_context(self) -> Dict[str, Any]:
        """Get current working context"""
        return self.working_context.copy()


# FastAPI application
app = FastAPI(title="Reasoning Service")
reasoning_service: Optional[ReasoningService] = None


class FactInput(BaseModel):
    """Input for creating a fact"""
    statement: str
    confidence: float = 1.0
    source: str = ""
    validity_period: Optional[float] = None  # in seconds
    metadata: Dict[str, Any] = {}


class RuleInput(BaseModel):
    """Input for creating a rule"""
    name: str
    premises: List[str]
    conclusion: str
    confidence: float = 1.0
    reasoning_type: str = "deductive"
    metadata: Dict[str, Any] = {}


class ReasoningInput(BaseModel):
    """Input for reasoning operations"""
    reasoning_type: str
    premises: List[str] = []
    observations: List[str] = []
    events: List[Dict[str, Any]] = []


class DecisionInput(BaseModel):
    """Input for decision making"""
    context: Dict[str, Any]
    alternatives: List[str]


@app.on_event("startup")
async def startup_event():
    """Initialize reasoning service on startup"""
    global reasoning_service
    reasoning_service = ReasoningService()
    await reasoning_service.initialize()
    
    # Start metrics server
    start_http_server(8004)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup reasoning service on shutdown"""
    if reasoning_service:
        # Cleanup if needed
        pass


@app.get("/status")
async def get_status():
    """Get reasoning service status"""
    return {
        "status": "running",
        "facts_count": len(reasoning_service.facts) if reasoning_service else 0,
        "rules_count": len(reasoning_service.rules) if reasoning_service else 0,
        "inferences_count": len(reasoning_service.inferences) if reasoning_service else 0,
        "decisions_count": len(reasoning_service.decisions) if reasoning_service else 0
    }


@app.post("/facts")
async def create_fact(fact_input: FactInput):
    """Create a new fact"""
    if not reasoning_service:
        raise HTTPException(status_code=503, detail="Reasoning service not initialized")
    
    fact = Fact(
        statement=fact_input.statement,
        confidence=fact_input.confidence,
        source=fact_input.source,
        validity_period=timedelta(seconds=fact_input.validity_period) if fact_input.validity_period else None,
        metadata=fact_input.metadata
    )
    
    fact_id = await reasoning_service.add_fact(fact)
    
    return {"fact_id": fact_id, "status": "created"}


@app.post("/rules")
async def create_rule(rule_input: RuleInput):
    """Create a new reasoning rule"""
    if not reasoning_service:
        raise HTTPException(status_code=503, detail="Reasoning service not initialized")
    
    rule = Rule(
        name=rule_input.name,
        premises=rule_input.premises,
        conclusion=rule_input.conclusion,
        confidence=rule_input.confidence,
        reasoning_type=ReasoningType(rule_input.reasoning_type),
        metadata=rule_input.metadata
    )
    
    rule_id = await reasoning_service.add_rule(rule)
    
    return {"rule_id": rule_id, "status": "created"}


@app.post("/reason")
async def perform_reasoning(reasoning_input: ReasoningInput):
    """Perform reasoning operation"""
    if not reasoning_service:
        raise HTTPException(status_code=503, detail="Reasoning service not initialized")
    
    reasoning_type = ReasoningType(reasoning_input.reasoning_type)
    
    if reasoning_type == ReasoningType.DEDUCTIVE:
        inference = await reasoning_service.deductive_reasoning(reasoning_input.premises)
    elif reasoning_type == ReasoningType.INDUCTIVE:
        inference = await reasoning_service.inductive_reasoning(reasoning_input.observations)
    elif reasoning_type == ReasoningType.CAUSAL:
        inference = await reasoning_service.causal_reasoning(reasoning_input.events)
    else:
        raise HTTPException(status_code=400, detail="Unsupported reasoning type")
    
    return inference.to_dict()


@app.post("/decide")
async def make_decision_endpoint(decision_input: DecisionInput):
    """Make a decision"""
    if not reasoning_service:
        raise HTTPException(status_code=503, detail="Reasoning service not initialized")
    
    decision = await reasoning_service.make_decision(
        decision_input.context,
        decision_input.alternatives
    )
    
    return decision.to_dict()


@app.post("/context")
async def update_context_endpoint(context_update: Dict[str, Any]):
    """Update working context"""
    if not reasoning_service:
        raise HTTPException(status_code=503, detail="Reasoning service not initialized")
    
    await reasoning_service.update_context(context_update)
    
    return {"status": "updated"}


@app.get("/context")
async def get_context_endpoint():
    """Get current working context"""
    if not reasoning_service:
        raise HTTPException(status_code=503, detail="Reasoning service not initialized")
    
    return await reasoning_service.get_context()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
