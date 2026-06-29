"""
Reflection Engine - Conversation review, self-review, mistake detection, and memory update
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from shared.database.mongodb import get_mongodb
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Reflection Service",
    description="Conversation review, self-review, mistake detection, and memory update for AI Companion",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ConversationReviewRequest(BaseModel):
    """Conversation review request"""
    conversation_id: str = Field(..., description="Conversation ID")
    user_id: str = Field(..., description="User ID")
    messages: List[Dict[str, Any]] = Field(..., description="Conversation messages")


class ConversationReviewResponse(BaseModel):
    """Conversation review response"""
    conversation_id: str = Field(..., description="Conversation ID")
    clarity_score: float = Field(..., description="Clarity score (0-1)")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    helpfulness_score: float = Field(..., description="Helpfulness score (0-1)")
    accuracy_score: float = Field(..., description="Accuracy score (0-1)")
    overall_score: float = Field(..., description="Overall score (0-1)")
    issues: List[Dict[str, Any]] = Field(..., description="Detected issues")
    strengths: List[str] = Field(..., description="Identified strengths")
    weaknesses: List[str] = Field(..., description="Identified weaknesses")


class SelfReviewRequest(BaseModel):
    """Self review request"""
    conversation_review: ConversationReviewResponse = Field(..., description="Conversation review results")
    performance_history: Optional[List[Dict[str, Any]]] = Field(default=None, description="Historical performance data")


class SelfReviewResponse(BaseModel):
    """Self review response"""
    timestamp: str = Field(..., description="Review timestamp")
    performance_analysis: Dict[str, Any] = Field(..., description="Performance analysis")
    mistake_analysis: Dict[str, Any] = Field(..., description="Mistake analysis")
    improvement_suggestions: List[str] = Field(..., description="Improvement suggestions")
    action_items: List[Dict[str, Any]] = Field(..., description="Action items to implement")


class MistakeDetectionRequest(BaseModel):
    """Mistake detection request"""
    conversation_id: str = Field(..., description="Conversation ID")
    user_feedback: Optional[str] = Field(default=None, description="User feedback on the conversation")
    issues: List[Dict[str, Any]] = Field(..., description="Issues detected in conversation review")


class MistakeDetectionResponse(BaseModel):
    """Mistake detection response"""
    mistakes: List[Dict[str, Any]] = Field(..., description="Detected mistakes")
    root_causes: List[str] = Field(..., description="Root causes of mistakes")
    severity: str = Field(..., description="Overall severity: low, medium, high, critical")


class MemoryUpdateRequest(BaseModel):
    """Memory update request"""
    conversation_id: str = Field(..., description="Conversation ID")
    learnings: List[str] = Field(..., description="Learnings from the conversation")
    corrections: List[Dict[str, Any]] = Field(..., description="Corrections to apply")
    new_knowledge: List[Dict[str, Any]] = Field(..., description="New knowledge to store")


class MemoryUpdateResponse(BaseModel):
    """Memory update response"""
    status: str = Field(..., description="Update status")
    learnings_stored: int = Field(..., description="Number of learnings stored")
    corrections_applied: int = Field(..., description="Number of corrections applied")
    knowledge_added: int = Field(..., description="Number of knowledge items added")


# Conversation reviewer
class ConversationReviewer:
    """Reviews conversations for quality and issues"""
    
    def __init__(self):
        self.clarity_threshold = 0.7
        self.relevance_threshold = 0.7
        self.helpfulness_threshold = 0.7
        self.accuracy_threshold = 0.8
    
    def review_conversation(self, conversation_id: str, messages: List[Dict[str, Any]]) -> ConversationReviewResponse:
        """Review a conversation"""
        # Evaluate clarity
        clarity_score = self._evaluate_clarity(messages)
        
        # Evaluate relevance
        relevance_score = self._evaluate_relevance(messages)
        
        # Evaluate helpfulness
        helpfulness_score = self._evaluate_helpfulness(messages)
        
        # Evaluate accuracy
        accuracy_score = self._evaluate_accuracy(messages)
        
        # Calculate overall score
        overall_score = (clarity_score + relevance_score + helpfulness_score + accuracy_score) / 4
        
        # Detect issues
        issues = self._detect_issues(clarity_score, relevance_score, helpfulness_score, accuracy_score)
        
        # Identify strengths
        strengths = self._identify_strengths(clarity_score, relevance_score, helpfulness_score, accuracy_score)
        
        # Identify weaknesses
        weaknesses = self._identify_weaknesses(clarity_score, relevance_score, helpfulness_score, accuracy_score)
        
        return ConversationReviewResponse(
            conversation_id=conversation_id,
            clarity_score=clarity_score,
            relevance_score=relevance_score,
            helpfulness_score=helpfulness_score,
            accuracy_score=accuracy_score,
            overall_score=overall_score,
            issues=issues,
            strengths=strengths,
            weaknesses=weaknesses
        )
    
    def _evaluate_clarity(self, messages: List[Dict[str, Any]]) -> float:
        """Evaluate clarity of AI responses"""
        ai_responses = [m for m in messages if m.get("role") == "assistant"]
        
        if not ai_responses:
            return 0.5
        
        clarity_scores = []
        for response in ai_responses:
            content = response.get("content", "")
            length = len(content)
            
            if length < 10:
                clarity_scores.append(0.3)  # Too short
            elif length > 500:
                clarity_scores.append(0.5)  # Too long
            else:
                clarity_scores.append(0.8)  # Good length
        
        return sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0.5
    
    def _evaluate_relevance(self, messages: List[Dict[str, Any]]) -> float:
        """Evaluate relevance of AI responses to user queries"""
        relevance_scores = []
        
        for i in range(len(messages) - 1):
            if messages[i].get("role") == "user" and messages[i + 1].get("role") == "assistant":
                user_query = messages[i].get("content", "")
                ai_response = messages[i + 1].get("content", "")
                
                relevance = self._calculate_relevance(user_query, ai_response)
                relevance_scores.append(relevance)
        
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.5
    
    def _calculate_relevance(self, query: str, response: str) -> float:
        """Calculate relevance score between query and response"""
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        
        if not query_words:
            return 0.5
        
        matching_words = len(query_words & response_words)
        relevance = matching_words / len(query_words)
        
        return min(relevance, 1.0)
    
    def _evaluate_helpfulness(self, messages: List[Dict[str, Any]]) -> float:
        """Evaluate helpfulness based on user feedback"""
        user_messages = [m for m in messages if m.get("role") == "user"]
        
        if not user_messages:
            return 0.5
        
        feedback_scores = []
        for message in user_messages:
            feedback = message.get("feedback")
            if feedback is not None:
                feedback_scores.append(feedback)
        
        if feedback_scores:
            return sum(feedback_scores) / len(feedback_scores)
        
        return 0.5  # Default if no feedback
    
    def _evaluate_accuracy(self, messages: List[Dict[str, Any]]) -> float:
        """Evaluate accuracy of AI responses"""
        # Placeholder: In production, this would use fact-checking
        # For now, return a default score
        return 0.8
    
    def _detect_issues(
        self,
        clarity_score: float,
        relevance_score: float,
        helpfulness_score: float,
        accuracy_score: float
    ) -> List[Dict[str, Any]]:
        """Detect issues in the conversation"""
        issues = []
        
        if clarity_score < self.clarity_threshold:
            issues.append({
                "type": "clarity",
                "severity": "medium",
                "description": "AI responses lack clarity",
                "suggestion": "Improve response clarity and conciseness"
            })
        
        if relevance_score < self.relevance_threshold:
            issues.append({
                "type": "relevance",
                "severity": "high",
                "description": "AI responses not relevant to user queries",
                "suggestion": "Improve understanding of user intent"
            })
        
        if helpfulness_score < self.helpfulness_threshold:
            issues.append({
                "type": "helpfulness",
                "severity": "high",
                "description": "AI responses not helpful to user",
                "suggestion": "Improve response helpfulness and actionability"
            })
        
        if accuracy_score < self.accuracy_threshold:
            issues.append({
                "type": "accuracy",
                "severity": "critical",
                "description": "AI responses contain inaccuracies",
                "suggestion": "Improve fact-checking and knowledge base"
            })
        
        return issues
    
    def _identify_strengths(
        self,
        clarity_score: float,
        relevance_score: float,
        helpfulness_score: float,
        accuracy_score: float
    ) -> List[str]:
        """Identify strengths in the conversation"""
        strengths = []
        
        if clarity_score > 0.8:
            strengths.append("High clarity in responses")
        
        if relevance_score > 0.8:
            strengths.append("High relevance to user queries")
        
        if helpfulness_score > 0.8:
            strengths.append("High helpfulness to user")
        
        if accuracy_score > 0.8:
            strengths.append("High accuracy in responses")
        
        return strengths
    
    def _identify_weaknesses(
        self,
        clarity_score: float,
        relevance_score: float,
        helpfulness_score: float,
        accuracy_score: float
    ) -> List[str]:
        """Identify weaknesses in the conversation"""
        weaknesses = []
        
        if clarity_score < 0.6:
            weaknesses.append("Low clarity in responses")
        
        if relevance_score < 0.6:
            weaknesses.append("Low relevance to user queries")
        
        if helpfulness_score < 0.6:
            weaknesses.append("Low helpfulness to user")
        
        if accuracy_score < 0.6:
            weaknesses.append("Low accuracy in responses")
        
        return weaknesses


# Self reviewer
class SelfReviewer:
    """Performs self-review of AI performance"""
    
    def self_review(self, request: SelfReviewRequest) -> SelfReviewResponse:
        """Perform self-review"""
        review = request.conversation_review
        
        # Analyze performance
        performance_analysis = self._analyze_performance(review)
        
        # Analyze mistakes
        mistake_analysis = self._analyze_mistakes(review.issues)
        
        # Generate improvement suggestions
        improvement_suggestions = self._generate_improvement_suggestions(performance_analysis, mistake_analysis)
        
        # Generate action items
        action_items = self._generate_action_items(improvement_suggestions)
        
        return SelfReviewResponse(
            timestamp=datetime.utcnow().isoformat(),
            performance_analysis=performance_analysis,
            mistake_analysis=mistake_analysis,
            improvement_suggestions=improvement_suggestions,
            action_items=action_items
        )
    
    def _analyze_performance(self, review: ConversationReviewResponse) -> Dict[str, Any]:
        """Analyze overall performance"""
        return {
            "overall_score": review.overall_score,
            "score_breakdown": {
                "clarity": review.clarity_score,
                "relevance": review.relevance_score,
                "helpfulness": review.helpfulness_score,
                "accuracy": review.accuracy_score
            },
            "strengths_count": len(review.strengths),
            "weaknesses_count": len(review.weaknesses),
            "issues_count": len(review.issues)
        }
    
    def _analyze_mistakes(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze mistakes"""
        if not issues:
            return {
                "mistakes": [],
                "mistake_count": 0,
                "severity": "none",
                "root_causes": []
            }
        
        mistakes = []
        for issue in issues:
            mistakes.append({
                "type": issue["type"],
                "severity": issue["severity"],
                "description": issue["description"]
            })
        
        # Determine overall severity
        severities = [issue["severity"] for issue in issues]
        if "critical" in severities:
            overall_severity = "critical"
        elif "high" in severities:
            overall_severity = "high"
        elif "medium" in severities:
            overall_severity = "medium"
        else:
            overall_severity = "low"
        
        # Identify root causes
        root_causes = self._identify_root_causes(issues)
        
        return {
            "mistakes": mistakes,
            "mistake_count": len(mistakes),
            "severity": overall_severity,
            "root_causes": root_causes
        }
    
    def _identify_root_causes(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Identify root causes of mistakes"""
        root_causes = []
        
        issue_types = [issue["type"] for issue in issues]
        
        if "clarity" in issue_types:
            root_causes.append("Poor response generation clarity")
        
        if "relevance" in issue_types:
            root_causes.append("Misunderstanding of user intent")
        
        if "helpfulness" in issue_types:
            root_causes.append("Lack of actionability in responses")
        
        if "accuracy" in issue_types:
            root_causes.append("Knowledge gaps or outdated information")
        
        return root_causes
    
    def _generate_improvement_suggestions(
        self,
        performance_analysis: Dict[str, Any],
        mistake_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        
        # Based on performance
        if performance_analysis["score_breakdown"]["clarity"] < 0.7:
            suggestions.append("Focus on improving response clarity and conciseness")
        
        if performance_analysis["score_breakdown"]["relevance"] < 0.7:
            suggestions.append("Improve understanding of user intent and context")
        
        if performance_analysis["score_breakdown"]["helpfulness"] < 0.7:
            suggestions.append("Make responses more actionable and helpful")
        
        if performance_analysis["score_breakdown"]["accuracy"] < 0.7:
            suggestions.append("Update knowledge base and improve fact-checking")
        
        # Based on mistakes
        for root_cause in mistake_analysis.get("root_causes", []):
            suggestions.append(f"Address: {root_cause}")
        
        return suggestions
    
    def _generate_action_items(self, suggestions: List[str]) -> List[Dict[str, Any]]:
        """Generate action items from suggestions"""
        action_items = []
        
        for i, suggestion in enumerate(suggestions):
            action_items.append({
                "id": f"action_{i}",
                "description": suggestion,
                "priority": "high" if i < 2 else "medium",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            })
        
        return action_items


# Mistake detector
class MistakeDetector:
    """Detects mistakes from conversation issues and user feedback"""
    
    def detect_mistakes(self, request: MistakeDetectionRequest) -> MistakeDetectionResponse:
        """Detect mistakes from conversation review and user feedback"""
        mistakes = []
        
        # Analyze issues
        for issue in request.issues:
            mistakes.append({
                "type": issue["type"],
                "severity": issue["severity"],
                "description": issue["description"],
                "context": request.conversation_id
            })
        
        # Analyze user feedback
        if request.user_feedback:
            feedback_mistakes = self._analyze_user_feedback(request.user_feedback)
            mistakes.extend(feedback_mistakes)
        
        # Determine overall severity
        severities = [mistake["severity"] for mistake in mistakes]
        if "critical" in severities:
            overall_severity = "critical"
        elif "high" in severities:
            overall_severity = "high"
        elif "medium" in severities:
            overall_severity = "medium"
        else:
            overall_severity = "low"
        
        # Identify root causes
        root_causes = list(set([mistake.get("type", "unknown") for mistake in mistakes]))
        
        return MistakeDetectionResponse(
            mistakes=mistakes,
            root_causes=root_causes,
            severity=overall_severity
        )
    
    def _analyze_user_feedback(self, feedback: str) -> List[Dict[str, Any]]:
        """Analyze user feedback for mistakes"""
        mistakes = []
        
        feedback_lower = feedback.lower()
        
        if "wrong" in feedback_lower or "incorrect" in feedback_lower:
            mistakes.append({
                "type": "accuracy",
                "severity": "high",
                "description": "User indicated incorrect information",
                "context": "user_feedback"
            })
        
        if "unclear" in feedback_lower or "confusing" in feedback_lower:
            mistakes.append({
                "type": "clarity",
                "severity": "medium",
                "description": "User found response unclear",
                "context": "user_feedback"
            })
        
        if "not helpful" in feedback_lower or "useless" in feedback_lower:
            mistakes.append({
                "type": "helpfulness",
                "severity": "high",
                "description": "User found response unhelpful",
                "context": "user_feedback"
            })
        
        return mistakes


# Global instances
conversation_reviewer = ConversationReviewer()
self_reviewer = SelfReviewer()
mistake_detector = MistakeDetector()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Reflection Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Reflection Service")


# API endpoints
@app.post("/api/v1/reflection/review")
async def review_conversation(request: ConversationReviewRequest) -> ConversationReviewResponse:
    """
    Review a conversation for quality and issues
    """
    try:
        review = conversation_reviewer.review_conversation(
            request.conversation_id,
            request.messages
        )
        
        # Store review in database
        db = await get_mongodb()
        conversation_reviews = db["conversation_reviews"]
        
        await conversation_reviews.insert_one({
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "review": review.dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Reviewed conversation {request.conversation_id}")
        
        return review
        
    except Exception as e:
        logger.error(f"Failed to review conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review conversation: {str(e)}"
        )


@app.post("/api/v1/reflection/self-review")
async def self_review(request: SelfReviewRequest) -> SelfReviewResponse:
    """
    Perform self-review of AI performance
    """
    try:
        review = self_reviewer.self_review(request)
        
        # Store self-review in database
        db = await get_mongodb()
        self_reviews = db["self_reviews"]
        
        await self_reviews.insert_one({
            "review": review.dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info("Performed self-review")
        
        return review
        
    except Exception as e:
        logger.error(f"Failed to perform self-review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform self-review: {str(e)}"
        )


@app.post("/api/v1/reflection/detect-mistakes")
async def detect_mistakes(request: MistakeDetectionRequest) -> MistakeDetectionResponse:
    """
    Detect mistakes from conversation review and user feedback
    """
    try:
        detection = mistake_detector.detect_mistakes(request)
        
        # Store mistake detection in database
        db = await get_mongodb()
        mistake_detections = db["mistake_detections"]
        
        await mistake_detections.insert_one({
            "conversation_id": request.conversation_id,
            "detection": detection.dict(),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Detected mistakes for conversation {request.conversation_id}")
        
        return detection
        
    except Exception as e:
        logger.error(f"Failed to detect mistakes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect mistakes: {str(e)}"
        )


@app.post("/api/v1/reflection/update-memory")
async def update_memory(request: MemoryUpdateRequest) -> MemoryUpdateResponse:
    """
    Update memory based on reflection learnings
    """
    try:
        db = await get_mongodb()
        reflection_memories = db["reflection_memories"]
        
        # Store learnings
        learnings_stored = 0
        for learning in request.learnings:
            await reflection_memories.insert_one({
                "conversation_id": request.conversation_id,
                "type": "learning",
                "content": learning,
                "timestamp": datetime.utcnow().isoformat()
            })
            learnings_stored += 1
        
        # Store corrections
        corrections_applied = 0
        for correction in request.corrections:
            await reflection_memories.insert_one({
                "conversation_id": request.conversation_id,
                "type": "correction",
                "content": correction,
                "timestamp": datetime.utcnow().isoformat()
            })
            corrections_applied += 1
        
        # Store new knowledge
        knowledge_added = 0
        for knowledge in request.new_knowledge:
            await reflection_memories.insert_one({
                "conversation_id": request.conversation_id,
                "type": "knowledge",
                "content": knowledge,
                "timestamp": datetime.utcnow().isoformat()
            })
            knowledge_added += 1
        
        logger.info(f"Updated memory for conversation {request.conversation_id}")
        
        return MemoryUpdateResponse(
            status="updated",
            learnings_stored=learnings_stored,
            corrections_applied=corrections_applied,
            knowledge_added=knowledge_added
        )
        
    except Exception as e:
        logger.error(f"Failed to update memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "reflection-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
