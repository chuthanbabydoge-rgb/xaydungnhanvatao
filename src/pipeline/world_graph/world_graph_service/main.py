"""
World Graph Service - Dynamic world state management and spatial relationships
Manages object tracking, persistence, event timeline, and knowledge graph integration
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
from neo4j import AsyncGraphDatabase
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from prometheus_client import Counter, Histogram, Gauge, start_http_server


class EntityType(Enum):
    """Types of entities in the world graph"""
    PERSON = "person"
    OBJECT = "object"
    LOCATION = "location"
    EVENT = "event"
    CONCEPT = "concept"
    RELATIONSHIP = "relationship"


class RelationType(Enum):
    """Types of relationships between entities"""
    LOCATED_AT = "located_at"
    OWNS = "owns"
    INTERACTS_WITH = "interacts_with"
    PART_OF = "part_of"
    CAUSES = "causes"
    PRECEDES = "precedes"
    SIMILAR_TO = "similar_to"
    RELATED_TO = "related_to"


@dataclass
class Entity:
    """Represents an entity in the world graph"""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: EntityType = EntityType.OBJECT
    name: str = ""
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    spatial_position: Optional[Tuple[float, float, float]] = None
    temporal_validity: Optional[Tuple[datetime, datetime]] = None
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "spatial_position": self.spatial_position,
            "temporal_validity": [t.isoformat() if t else None for t in self.temporal_validity] if self.temporal_validity else None,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class Relationship:
    """Represents a relationship between entities"""
    relationship_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.RELATED_TO
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "properties": self.properties,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class WorldEvent:
    """Represents an event in the world timeline"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    entities: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration: Optional[timedelta] = None
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "entities": self.entities,
            "properties": self.properties,
            "timestamp": self.timestamp.isoformat(),
            "duration": str(self.duration) if self.duration else None,
            "confidence": self.confidence
        }


class WorldGraphService:
    """
    World Graph Service - Manages dynamic world state
    Handles entity tracking, relationships, and event timeline
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j", 
                 neo4j_password: str = "password"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver: Optional[AsyncGraphDatabase.driver] = None
        
        # In-memory storage for faster access
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.events: List[WorldEvent] = []
        
        # Spatial indexing
        self.spatial_index: Dict[Tuple[int, int, int], Set[str]] = {}  # Grid-based spatial index
        
        # Metrics
        self.entities_counter = Counter('worldgraph_entities_total', 'Total entities', ['type'])
        self.relationships_counter = Counter('worldgraph_relationships_total', 'Total relationships', ['type'])
        self.events_counter = Counter('worldgraph_events_total', 'Total events', ['type'])
        self.query_time = Histogram('worldgraph_query_seconds', 'Query execution time', ['operation'])
        self.graph_size = Gauge('worldgraph_size', 'Total graph size')
        
        # Tracing
        self.setup_tracing()
        self.tracer = trace.get_tracer(__name__)
        
        # Logger
        self.logger = logging.getLogger("world_graph_service")
    
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
        """Initialize Neo4j connection and indexes"""
        with self.tracer.start_as_current_span("initialize_world_graph") as span:
            span.set_attribute("neo4j_uri", self.neo4j_uri)
            
            try:
                self.driver = AsyncGraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.neo4j_user, self.neo4j_password)
                )
                
                # Verify connection
                await self.driver.verify_connectivity()
                
                # Create indexes
                await self._create_indexes()
                
                self.logger.info("World Graph service initialized successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize World Graph service: {e}")
                span.record_exception(e)
                return False
    
    async def _create_indexes(self):
        """Create Neo4j indexes for performance"""
        async with self.driver.session() as session:
            await session.run("CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.entity_id)")
            await session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)")
            await session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")
    
    async def add_entity(self, entity: Entity) -> str:
        """Add an entity to the world graph"""
        with self.tracer.start_as_current_span("add_entity") as span:
            span.set_attribute("entity_id", entity.entity_id)
            span.set_attribute("entity_type", entity.entity_type.value)
            
            try:
                # Add to in-memory storage
                self.entities[entity.entity_id] = entity
                
                # Update spatial index
                if entity.spatial_position:
                    grid_pos = self._get_grid_position(entity.spatial_position)
                    if grid_pos not in self.spatial_index:
                        self.spatial_index[grid_pos] = set()
                    self.spatial_index[grid_pos].add(entity.entity_id)
                
                # Add to Neo4j
                async with self.driver.session() as session:
                    await session.run(
                        """
                        CREATE (e:Entity {
                            entity_id: $entity_id,
                            entity_type: $entity_type,
                            name: $name,
                            description: $description,
                            properties: $properties,
                            spatial_position: $spatial_position,
                            confidence: $confidence,
                            created_at: $created_at,
                            updated_at: $updated_at
                        })
                        """,
                        entity_id=entity.entity_id,
                        entity_type=entity.entity_type.value,
                        name=entity.name,
                        description=entity.description,
                        properties=json.dumps(entity.properties),
                        spatial_position=json.dumps(entity.spatial_position) if entity.spatial_position else None,
                        confidence=entity.confidence,
                        created_at=entity.created_at.isoformat(),
                        updated_at=entity.updated_at.isoformat()
                    )
                
                # Update metrics
                self.entities_counter.labels(type=entity.entity_type.value).inc()
                self.graph_size.set(len(self.entities))
                
                self.logger.info(f"Added entity {entity.entity_id}")
                return entity.entity_id
                
            except Exception as e:
                self.logger.error(f"Failed to add entity: {e}")
                span.record_exception(e)
                raise
    
    async def add_relationship(self, relationship: Relationship) -> str:
        """Add a relationship between entities"""
        with self.tracer.start_as_current_span("add_relationship") as span:
            span.set_attribute("relationship_id", relationship.relationship_id)
            span.set_attribute("relation_type", relationship.relation_type.value)
            
            try:
                # Add to in-memory storage
                self.relationships[relationship.relationship_id] = relationship
                
                # Add to Neo4j
                async with self.driver.session() as session:
                    await session.run(
                        """
                        MATCH (source:Entity {entity_id: $source_id})
                        MATCH (target:Entity {entity_id: $target_id})
                        CREATE (source)-[r:RELATIONSHIP {
                            relationship_id: $relationship_id,
                            relation_type: $relation_type,
                            properties: $properties,
                            confidence: $confidence,
                            created_at: $created_at
                        }]->(target)
                        """,
                        source_id=relationship.source_id,
                        target_id=relationship.target_id,
                        relationship_id=relationship.relationship_id,
                        relation_type=relationship.relation_type.value,
                        properties=json.dumps(relationship.properties),
                        confidence=relationship.confidence,
                        created_at=relationship.created_at.isoformat()
                    )
                
                # Update metrics
                self.relationships_counter.labels(type=relationship.relation_type.value).inc()
                
                self.logger.info(f"Added relationship {relationship.relationship_id}")
                return relationship.relationship_id
                
            except Exception as e:
                self.logger.error(f"Failed to add relationship: {e}")
                span.record_exception(e)
                raise
    
    async def add_event(self, event: WorldEvent) -> str:
        """Add an event to the world timeline"""
        with self.tracer.start_as_current_span("add_event") as span:
            span.set_attribute("event_id", event.event_id)
            span.set_attribute("event_type", event.event_type)
            
            try:
                # Add to in-memory storage
                self.events.append(event)
                
                # Keep only recent events in memory (last 1000)
                if len(self.events) > 1000:
                    self.events = self.events[-1000:]
                
                # Add to Neo4j
                async with self.driver.session() as session:
                    await session.run(
                        """
                        CREATE (e:Event {
                            event_id: $event_id,
                            event_type: $event_type,
                            entities: $entities,
                            properties: $properties,
                            timestamp: $timestamp,
                            duration: $duration,
                            confidence: $confidence
                        })
                        """,
                        event_id=event.event_id,
                        event_type=event.event_type,
                        entities=json.dumps(event.entities),
                        properties=json.dumps(event.properties),
                        timestamp=event.timestamp.isoformat(),
                        duration=str(event.duration) if event.duration else None,
                        confidence=event.confidence
                    )
                
                # Update metrics
                self.events_counter.labels(type=event.event_type).inc()
                
                self.logger.info(f"Added event {event.event_id}")
                return event.event_id
                
            except Exception as e:
                self.logger.error(f"Failed to add event: {e}")
                span.record_exception(e)
                raise
    
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID"""
        import time
        start_time = time.time()
        
        # Check in-memory storage first
        if entity_id in self.entities:
            entity = self.entities[entity_id]
            self.query_time.labels(operation="get_entity").observe(time.time() - start_time)
            return entity
        
        # Query Neo4j
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity {entity_id: $entity_id}) RETURN e",
                entity_id=entity_id
            )
            record = await result.single()
            
            if record:
                node = record["e"]
                entity = Entity(
                    entity_id=node["entity_id"],
                    entity_type=EntityType(node["entity_type"]),
                    name=node["name"],
                    description=node["description"],
                    properties=json.loads(node["properties"]) if node["properties"] else {},
                    spatial_position=json.loads(node["spatial_position"]) if node["spatial_position"] else None,
                    confidence=node["confidence"],
                    created_at=datetime.fromisoformat(node["created_at"]),
                    updated_at=datetime.fromisoformat(node["updated_at"])
                )
                self.entities[entity_id] = entity
                self.query_time.labels(operation="get_entity").observe(time.time() - start_time)
                return entity
        
        self.query_time.labels(operation="get_entity").observe(time.time() - start_time)
        return None
    
    async def get_related_entities(self, entity_id: str, relation_type: Optional[RelationType] = None) -> List[Entity]:
        """Get entities related to a given entity"""
        import time
        start_time = time.time()
        
        related_entities = []
        
        async with self.driver.session() as session:
            if relation_type:
                result = await session.run(
                    """
                    MATCH (source:Entity {entity_id: $entity_id})-[r:RELATIONSHIP {relation_type: $relation_type}]->(target:Entity)
                    RETURN target
                    """,
                    entity_id=entity_id,
                    relation_type=relation_type.value
                )
            else:
                result = await session.run(
                    """
                    MATCH (source:Entity {entity_id: $entity_id})-[r:RELATIONSHIP]->(target:Entity)
                    RETURN target
                    """,
                    entity_id=entity_id
                )
            
            async for record in result:
                node = record["target"]
                entity = Entity(
                    entity_id=node["entity_id"],
                    entity_type=EntityType(node["entity_type"]),
                    name=node["name"],
                    description=node["description"],
                    properties=json.loads(node["properties"]) if node["properties"] else {},
                    spatial_position=json.loads(node["spatial_position"]) if node["spatial_position"] else None,
                    confidence=node["confidence"],
                    created_at=datetime.fromisoformat(node["created_at"]),
                    updated_at=datetime.fromisoformat(node["updated_at"])
                )
                related_entities.append(entity)
        
        self.query_time.labels(operation="get_related_entities").observe(time.time() - start_time)
        return related_entities
    
    async def get_nearby_entities(self, position: Tuple[float, float, float], radius: float = 5.0) -> List[Entity]:
        """Get entities within a radius of a position"""
        import time
        start_time = time.time()
        
        nearby_entities = []
        
        # Get grid positions within radius
        grid_positions = self._get_nearby_grid_positions(position, radius)
        
        # Collect entity IDs from nearby grid cells
        entity_ids = set()
        for grid_pos in grid_positions:
            if grid_pos in self.spatial_index:
                entity_ids.update(self.spatial_index[grid_pos])
        
        # Filter by actual distance
        for entity_id in entity_ids:
            if entity_id in self.entities:
                entity = self.entities[entity_id]
                if entity.spatial_position:
                    distance = self._calculate_distance(position, entity.spatial_position)
                    if distance <= radius:
                        nearby_entities.append(entity)
        
        self.query_time.labels(operation="get_nearby_entities").observe(time.time() - start_time)
        return nearby_entities
    
    async def get_recent_events(self, limit: int = 10, event_type: Optional[str] = None) -> List[WorldEvent]:
        """Get recent events from the timeline"""
        import time
        start_time = time.time()
        
        if event_type:
            events = [e for e in self.events if e.event_type == event_type]
        else:
            events = self.events
        
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        recent_events = events[:limit]
        
        self.query_time.labels(operation="get_recent_events").observe(time.time() - start_time)
        return recent_events
    
    async def query_graph(self, cypher_query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a custom Cypher query"""
        import time
        start_time = time.time()
        
        results = []
        async with self.driver.session() as session:
            result = await session.run(cypher_query, params or {})
            async for record in result:
                results.append(record.data())
        
        self.query_time.labels(operation="custom_query").observe(time.time() - start_time)
        return results
    
    def _get_grid_position(self, position: Tuple[float, float, float], grid_size: float = 1.0) -> Tuple[int, int, int]:
        """Get grid position for spatial indexing"""
        x, y, z = position
        return (int(x / grid_size), int(y / grid_size), int(z / grid_size))
    
    def _get_nearby_grid_positions(self, position: Tuple[float, float, float], radius: float, grid_size: float = 1.0) -> Set[Tuple[int, int, int]]:
        """Get grid positions within radius"""
        center_grid = self._get_grid_position(position, grid_size)
        grid_radius = int(radius / grid_size) + 1
        
        nearby_positions = set()
        for x in range(center_grid[0] - grid_radius, center_grid[0] + grid_radius + 1):
            for y in range(center_grid[1] - grid_radius, center_grid[1] + grid_radius + 1):
                for z in range(center_grid[2] - grid_radius, center_grid[2] + grid_radius + 1):
                    nearby_positions.add((x, y, z))
        
        return nearby_positions
    
    def _calculate_distance(self, pos1: Tuple[float, float, float], pos2: Tuple[float, float, float]) -> float:
        """Calculate Euclidean distance between two positions"""
        return sum((a - b) ** 2 for a, b in zip(pos1, pos2)) ** 0.5
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            await self.driver.close()


# FastAPI application
app = FastAPI(title="World Graph Service")
world_graph_service: Optional[WorldGraphService] = None


class EntityInput(BaseModel):
    """Input for creating an entity"""
    entity_type: str
    name: str
    description: str = ""
    properties: Dict[str, Any] = {}
    spatial_position: Optional[List[float]] = None
    confidence: float = 1.0


class RelationshipInput(BaseModel):
    """Input for creating a relationship"""
    source_id: str
    target_id: str
    relation_type: str
    properties: Dict[str, Any] = {}
    confidence: float = 1.0


class EventInput(BaseModel):
    """Input for creating an event"""
    event_type: str
    entities: List[str] = []
    properties: Dict[str, Any] = {}
    duration: Optional[float] = None
    confidence: float = 1.0


@app.on_event("startup")
async def startup_event():
    """Initialize world graph service on startup"""
    global world_graph_service
    world_graph_service = WorldGraphService()
    await world_graph_service.initialize()
    
    # Start metrics server
    start_http_server(8003)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup world graph service on shutdown"""
    if world_graph_service:
        await world_graph_service.cleanup()


@app.get("/status")
async def get_status():
    """Get world graph service status"""
    return {
        "status": "running",
        "entities_count": len(world_graph_service.entities) if world_graph_service else 0,
        "relationships_count": len(world_graph_service.relationships) if world_graph_service else 0,
        "events_count": len(world_graph_service.events) if world_graph_service else 0
    }


@app.post("/entities")
async def create_entity(entity_input: EntityInput):
    """Create a new entity"""
    if not world_graph_service:
        raise HTTPException(status_code=503, detail="World Graph service not initialized")
    
    entity = Entity(
        entity_type=EntityType(entity_input.entity_type),
        name=entity_input.name,
        description=entity_input.description,
        properties=entity_input.properties,
        spatial_position=tuple(entity_input.spatial_position) if entity_input.spatial_position else None,
        confidence=entity_input.confidence
    )
    
    entity_id = await world_graph_service.add_entity(entity)
    
    return {"entity_id": entity_id, "status": "created"}


@app.get("/entities/{entity_id}")
async def get_entity_endpoint(entity_id: str):
    """Get an entity by ID"""
    if not world_graph_service:
        raise HTTPException(status_code=503, detail="World Graph service not initialized")
    
    entity = await world_graph_service.get_entity(entity_id)
    
    if entity:
        return entity.to_dict()
    else:
        raise HTTPException(status_code=404, detail="Entity not found")


@app.post("/relationships")
async def create_relationship(relationship_input: RelationshipInput):
    """Create a new relationship"""
    if not world_graph_service:
        raise HTTPException(status_code=503, detail="World Graph service not initialized")
    
    relationship = Relationship(
        source_id=relationship_input.source_id,
        target_id=relationship_input.target_id,
        relation_type=RelationType(relationship_input.relation_type),
        properties=relationship_input.properties,
        confidence=relationship_input.confidence
    )
    
    relationship_id = await world_graph_service.add_relationship(relationship)
    
    return {"relationship_id": relationship_id, "status": "created"}


@app.get("/entities/{entity_id}/related")
async def get_related_entities_endpoint(entity_id: str, relation_type: Optional[str] = None):
    """Get entities related to a given entity"""
    if not world_graph_service:
        raise HTTPException(status_code=503, detail="World Graph service not initialized")
    
    rel_type = RelationType(relation_type) if relation_type else None
    entities = await world_graph_service.get_related_entities(entity_id, rel_type)
    
    return {"entities": [entity.to_dict() for entity in entities], "count": len(entities)}


@app.post("/events")
async def create_event(event_input: EventInput):
    """Create a new event"""
    if not world_graph_service:
        raise HTTPException(status_code=503, detail="World Graph service not initialized")
    
    event = WorldEvent(
        event_type=event_input.event_type,
        entities=event_input.entities,
        properties=event_input.properties,
        duration=timedelta(seconds=event_input.duration) if event_input.duration else None,
        confidence=event_input.confidence
    )
    
    event_id = await world_graph_service.add_event(event)
    
    return {"event_id": event_id, "status": "created"}


@app.get("/events/recent")
async def get_recent_events_endpoint(limit: int = 10, event_type: Optional[str] = None):
    """Get recent events"""
    if not world_graph_service:
        raise HTTPException(status_code=503, detail="World Graph service not initialized")
    
    events = await world_graph_service.get_recent_events(limit, event_type)
    
    return {"events": [event.to_dict() for event in events], "count": len(events)}


@app.post("/query")
async def query_graph_endpoint(query: str, params: Dict[str, Any] = None):
    """Execute a custom Cypher query"""
    if not world_graph_service:
        raise HTTPException(status_code=503, detail="World Graph service not initialized")
    
    results = await world_graph_service.query_graph(query, params)
    
    return {"results": results, "count": len(results)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)
