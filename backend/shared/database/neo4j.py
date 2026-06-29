"""
Neo4j graph database connection and management
"""
from neo4j import AsyncGraphDatabase
from typing import Optional, List, Dict, Any
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# Neo4j driver
neo4j_driver: Optional[AsyncGraphDatabase.driver] = None


async def init_neo4j():
    """
    Initialize Neo4j connection
    """
    global neo4j_driver
    
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_url,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        
        # Test connection
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN 1")
            await result.consume()
        
        logger.info("Neo4j connection initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j connection: {e}")
        raise


async def close_neo4j():
    """
    Close Neo4j connection
    """
    global neo4j_driver
    
    if neo4j_driver:
        await neo4j_driver.close()
        logger.info("Neo4j connection closed")


def get_neo4j():
    """
    Get Neo4j driver instance
    """
    if neo4j_driver is None:
        raise RuntimeError("Neo4j not initialized. Call init_neo4j() first.")
    return neo4j_driver


async def execute_query(
    query: str,
    parameters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Execute a Cypher query
    """
    driver = get_neo4j()
    
    try:
        async with driver.session() as session:
            result = await session.run(query, parameters or {})
            records = []
            async for record in result:
                records.append(record.data())
            return records
            
    except Exception as e:
        logger.error(f"Failed to execute query: {e}")
        raise


async def create_node(
    label: str,
    properties: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a node in the graph
    """
    query = f"""
    CREATE (n:{label} $properties)
    RETURN n
    """
    
    results = await execute_query(query, {"properties": properties})
    
    if results:
        return results[0]["n"]
    return None


async def create_relationship(
    from_node_label: str,
    from_node_id: str,
    to_node_label: str,
    to_node_id: str,
    relationship_type: str,
    properties: Optional[Dict[str, Any]] = None
):
    """
    Create a relationship between two nodes
    """
    query = f"""
    MATCH (a:{from_node_label} {{id: $from_id}})
    MATCH (b:{to_node_label} {{id: $to_id}})
    CREATE (a)-[r:{relationship_type} $properties]->(b)
    RETURN r
    """
    
    await execute_query(query, {
        "from_id": from_node_id,
        "to_id": to_node_id,
        "properties": properties or {}
    })


async def find_node(
    label: str,
    properties: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Find a node by properties
    """
    query = f"""
    MATCH (n:{label} $properties)
    RETURN n
    LIMIT 1
    """
    
    results = await execute_query(query, {"properties": properties})
    
    if results:
        return results[0]["n"]
    return None


async def find_related_nodes(
    node_label: str,
    node_id: str,
    relationship_type: Optional[str] = None,
    direction: str = "outgoing"
) -> List[Dict[str, Any]]:
    """
    Find nodes related to a given node
    """
    if direction == "outgoing":
        query = f"""
        MATCH (n:{node_label} {{id: $node_id}})-[r{f':{relationship_type}' if relationship_type else ''}]->(related)
        RETURN related, type(r) as relationship_type, r as relationship
        """
    elif direction == "incoming":
        query = f"""
        MATCH (n:{node_label} {{id: $node_id}})<-[r{f':{relationship_type}' if relationship_type else ''}]-(related)
        RETURN related, type(r) as relationship_type, r as relationship
        """
    else:  # both
        query = f"""
        MATCH (n:{node_label} {{id: $node_id}})-[r{f':{relationship_type}' if relationship_type else ''}]-(related)
        RETURN related, type(r) as relationship_type, r as relationship
        """
    
    return await execute_query(query, {"node_id": node_id})
