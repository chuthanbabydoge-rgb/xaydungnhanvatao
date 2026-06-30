"""
Research Agent - Information gathering and analysis
Performs web searches, data collection, and information synthesis
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import aiohttp
from bs4 import BeautifulSoup

from shared.agent_base import BaseAgent, AgentMessage, MessageType


class ResearchStatus(Enum):
    """Research status states"""
    INITIATED = "initiated"
    SEARCHING = "searching"
    GATHERING = "gathering"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(Enum):
    """Types of information sources"""
    WEB = "web"
    DATABASE = "database"
    API = "api"
    DOCUMENT = "document"
    KNOWLEDGE_BASE = "knowledge_base"


@dataclass
class ResearchQuery:
    """Represents a research query"""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    query_type: str = "general"  # general, academic, technical, news
    sources: List[SourceType] = field(default_factory=list)
    max_results: int = 10
    date_range: Optional[tuple] = None  # (start_date, end_date)
    language: str = "en"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query": self.query,
            "query_type": self.query_type,
            "sources": [s.value for s in self.sources],
            "max_results": self.max_results,
            "date_range": self.date_range,
            "language": self.language,
            "metadata": self.metadata
        }


@dataclass
class ResearchResult:
    """Represents a research result"""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_id: str = ""
    title: str = ""
    url: str = ""
    content: str = ""
    summary: str = ""
    relevance_score: float = 0.0
    source_type: SourceType = SourceType.WEB
    published_date: Optional[datetime] = None
    authors: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "query_id": self.query_id,
            "title": self.title,
            "url": self.url,
            "content": self.content[:500],  # Truncate for display
            "summary": self.summary,
            "relevance_score": self.relevance_score,
            "source_type": self.source_type.value,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "authors": self.authors,
            "tags": self.tags,
            "metadata": self.metadata
        }


@dataclass
class ResearchReport:
    """Represents a complete research report"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_id: str = ""
    title: str = ""
    summary: str = ""
    key_findings: List[str] = field(default_factory=list)
    results: List[ResearchResult] = field(default_factory=list)
    status: ResearchStatus = ResearchStatus.INITIATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "query_id": self.query_id,
            "title": self.title,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "results": [r.to_dict() for r in self.results],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "confidence_score": self.confidence_score
        }


class ResearchAgent(BaseAgent):
    """
    Research Agent - Performs information gathering and analysis
    Searches web sources, collects data, and synthesizes findings
    """
    
    def __init__(
        self,
        agent_id: str = "research-agent-1",
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        enable_tracing: bool = True,
        enable_metrics: bool = True
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="research",
            rabbitmq_url=rabbitmq_url,
            enable_tracing=enable_tracing,
            enable_metrics=enable_metrics
        )
        
        # Research storage
        self.queries: Dict[str, ResearchQuery] = {}
        self.results: Dict[str, List[ResearchResult]] = {}
        self.reports: Dict[str, ResearchReport] = {}
        
        # HTTP session for web requests
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Research capabilities
        self.capabilities = [
            "web_search",
            "data_extraction",
            "content_analysis",
            "source_validation",
            "information_synthesis"
        ]
    
    def register_handlers(self):
        """Register message handlers"""
        self.message_handlers[MessageType.TASK_REQUEST] = self.handle_task_request
        self.message_handlers[MessageType.QUERY] = self.handle_query
        self.message_handlers[MessageType.EVENT] = self.handle_event
    
    async def start(self):
        """Start the research agent"""
        await super().start()
        
        # Initialize HTTP session
        self.http_session = aiohttp.ClientSession()
        
        # Announce capabilities
        await self.announce_capabilities()
    
    async def stop(self):
        """Stop the research agent"""
        if self.http_session:
            await self.http_session.close()
        
        await super().stop()
    
    async def announce_capabilities(self):
        """Announce agent capabilities to the system"""
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
        """Handle incoming research task"""
        task_data = message.content
        
        # Create research query
        query = ResearchQuery(
            query=task_data.get("query", ""),
            query_type=task_data.get("query_type", "general"),
            sources=[SourceType(s) for s in task_data.get("sources", ["web"])],
            max_results=task_data.get("max_results", 10),
            language=task_data.get("language", "en"),
            metadata=task_data.get("metadata", {})
        )
        
        self.queries[query.query_id] = query
        
        # Execute research
        report = await self.execute_research(query)
        
        return {
            "query_id": query.query_id,
            "report_id": report.report_id,
            "status": report.status.value,
            "results_count": len(report.results)
        }
    
    async def handle_query(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle query messages"""
        query_type = message.content.get("query_type")
        
        if query_type == "research_status":
            query_id = message.content.get("query_id")
            if query_id in self.queries:
                return self.queries[query_id].to_dict()
            else:
                return {"error": "Query not found"}
        
        elif query_type == "report_status":
            report_id = message.content.get("report_id")
            if report_id in self.reports:
                return self.reports[report_id].to_dict()
            else:
                return {"error": "Report not found"}
        
        elif query_type == "capabilities":
            return {"capabilities": self.capabilities}
        
        else:
            return {"error": "Unknown query type"}
    
    async def handle_event(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle event messages"""
        event_type = message.content.get("event_type")
        
        if event_type == "new_research_topic":
            # Auto-initiate research on new topic
            topic = message.content.get("topic")
            if topic:
                query = ResearchQuery(query=topic)
                report = await self.execute_research(query)
                return {"report_id": report.report_id}
        
        return {"status": "acknowledged"}
    
    async def execute_research(self, query: ResearchQuery) -> ResearchReport:
        """Execute research query and generate report"""
        with self.tracer.start_as_current_span("execute_research") as span:
            span.set_attribute("query_id", query.query_id)
            span.set_attribute("query", query.query)
            
            # Create report
            report = ResearchReport(
                query_id=query.query_id,
                title=f"Research Report: {query.query}",
                status=ResearchStatus.SEARCHING
            )
            
            try:
                # Search for information
                report.status = ResearchStatus.SEARCHING
                results = await self.search_information(query)
                
                # Gather detailed content
                report.status = ResearchStatus.GATHERING
                detailed_results = await self.gather_detailed_content(results)
                
                # Analyze results
                report.status = ResearchStatus.ANALYZING
                analyzed_results = await self.analyze_results(detailed_results, query)
                
                # Generate report
                report.results = analyzed_results
                report.key_findings = await self.extract_key_findings(analyzed_results)
                report.summary = await self.generate_summary(analyzed_results, query)
                report.confidence_score = await self.calculate_confidence(analyzed_results)
                
                report.status = ResearchStatus.COMPLETED
                report.completed_at = datetime.utcnow()
                
                self.reports[report.report_id] = report
                self.results[query.query_id] = analyzed_results
                
            except Exception as e:
                self.logger.error(f"Research error: {e}")
                report.status = ResearchStatus.FAILED
            
            return report
    
    async def search_information(self, query: ResearchQuery) -> List[Dict[str, Any]]:
        """Search for information based on query"""
        results = []
        
        # Web search (simulated - in production, use real search APIs)
        if SourceType.WEB in query.sources or not query.sources:
            web_results = await self.web_search(query)
            results.extend(web_results)
        
        # API search (if configured)
        if SourceType.API in query.sources:
            api_results = await self.api_search(query)
            results.extend(api_results)
        
        # Limit results
        return results[:query.max_results]
    
    async def web_search(self, query: ResearchQuery) -> List[Dict[str, Any]]:
        """Perform web search (simulated)"""
        # In production, integrate with real search APIs (Google, Bing, etc.)
        simulated_results = [
            {
                "title": f"Result about {query.query}",
                "url": f"https://example.com/{query.query.replace(' ', '-')}",
                "snippet": f"This is a simulated search result for {query.query}",
                "source_type": SourceType.WEB
            }
        ]
        
        # Generate multiple simulated results
        for i in range(query.max_results):
            simulated_results.append({
                "title": f"{query.query} - Source {i+1}",
                "url": f"https://example.com/{query.query.replace(' ', '-')}-{i+1}",
                "snippet": f"Additional information about {query.query} from source {i+1}",
                "source_type": SourceType.WEB
            })
        
        return simulated_results
    
    async def api_search(self, query: ResearchQuery) -> List[Dict[str, Any]]:
        """Perform API search"""
        # In production, integrate with specific APIs (Wikipedia, academic databases, etc.)
        return []
    
    async def gather_detailed_content(self, results: List[Dict[str, Any]]) -> List[ResearchResult]:
        """Gather detailed content from search results"""
        detailed_results = []
        
        for result in results:
            try:
                # Fetch content from URL
                if result.get("url"):
                    content = await self.fetch_web_content(result["url"])
                    
                    research_result = ResearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        content=content,
                        summary=result.get("snippet", ""),
                        source_type=result.get("source_type", SourceType.WEB)
                    )
                    
                    detailed_results.append(research_result)
                
            except Exception as e:
                self.logger.error(f"Error fetching content: {e}")
        
        return detailed_results
    
    async def fetch_web_content(self, url: str) -> str:
        """Fetch and extract content from a URL"""
        try:
            async with self.http_session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Extract text content
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    # Get text
                    text = soup.get_text()
                    
                    # Clean up text
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    return text[:5000]  # Limit content length
                
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
        
        return ""
    
    async def analyze_results(self, results: List[ResearchResult], query: ResearchQuery) -> List[ResearchResult]:
        """Analyze and score research results"""
        analyzed_results = []
        
        for result in results:
            # Calculate relevance score
            relevance = await self.calculate_relevance(result, query)
            result.relevance_score = relevance
            
            # Extract tags
            result.tags = await self.extract_tags(result)
            
            # Only include results with reasonable relevance
            if relevance > 0.3:
                analyzed_results.append(result)
        
        # Sort by relevance
        analyzed_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return analyzed_results
    
    async def calculate_relevance(self, result: ResearchResult, query: ResearchQuery) -> float:
        """Calculate relevance score for a result"""
        score = 0.0
        
        # Check query terms in title
        query_terms = query.query.lower().split()
        title_lower = result.title.lower()
        
        for term in query_terms:
            if term in title_lower:
                score += 0.3
        
        # Check query terms in content
        content_lower = result.content.lower()
        for term in query_terms:
            if term in content_lower:
                score += 0.2
        
        # Normalize score
        return min(score, 1.0)
    
    async def extract_tags(self, result: ResearchResult) -> List[str]:
        """Extract tags from research result"""
        tags = []
        
        # Simple keyword extraction
        words = result.content.lower().split()
        word_freq = {}
        
        for word in words:
            if len(word) > 3:  # Ignore short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get most frequent words as tags
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        tags = [word for word, freq in sorted_words[:5] if freq > 2]
        
        return tags
    
    async def extract_key_findings(self, results: List[ResearchResult]) -> List[str]:
        """Extract key findings from research results"""
        findings = []
        
        # Simple extraction based on content analysis
        for result in results[:5]:  # Top 5 results
            # Extract sentences with high information content
            sentences = result.content.split('.')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 50 and len(sentence) < 200:
                    # Check for informative patterns
                    if any(keyword in sentence.lower() for keyword in 
                          ["important", "key", "significant", "main", "primary", "essential"]):
                        findings.append(sentence)
                        if len(findings) >= 10:
                            break
            
            if len(findings) >= 10:
                break
        
        return findings[:10]
    
    async def generate_summary(self, results: List[ResearchResult], query: ResearchQuery) -> str:
        """Generate summary of research findings"""
        if not results:
            return f"No relevant information found for query: {query.query}"
        
        # Simple summary generation
        summary_parts = [
            f"Research completed for query: {query.query}",
            f"Found {len(results)} relevant results",
            f"Top sources include: {', '.join([r.title[:50] for r in results[:3]])}"
        ]
        
        if results[0].summary:
            summary_parts.append(f"Key finding: {results[0].summary[:200]}")
        
        return ". ".join(summary_parts)
    
    async def calculate_confidence(self, results: List[ResearchResult]) -> float:
        """Calculate confidence score for research results"""
        if not results:
            return 0.0
        
        # Confidence based on number and quality of results
        result_count_factor = min(len(results) / 10, 1.0)
        avg_relevance = sum(r.relevance_score for r in results) / len(results)
        
        confidence = (result_count_factor * 0.4) + (avg_relevance * 0.6)
        
        return confidence
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a research task"""
        query = task.get("query", "")
        
        if not query:
            return {"error": "No query provided"}
        
        research_query = ResearchQuery(
            query=query,
            query_type=task.get("query_type", "general"),
            max_results=task.get("max_results", 10)
        )
        
        report = await self.execute_research(research_query)
        
        return report.to_dict()


async def main():
    """Main entry point for the research agent"""
    agent = ResearchAgent()
    
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