"""
Behavior Tree System - Hierarchical Behavior Management
Local behavior tree execution, not LLM-dependent
"""

from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import asyncio
from datetime import datetime
import uuid


class NodeStatus(Enum):
    """Behavior tree node status"""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    PENDING = "pending"


class NodeType(Enum):
    """Behavior tree node types"""
    SEQUENCE = "sequence"  # Execute children in sequence
    SELECTOR = "selector"  # Execute children until one succeeds
    PARALLEL = "parallel"  # Execute children in parallel
    CONDITION = "condition"  # Check a condition
    ACTION = "action"  # Execute an action
    DECORATOR = "decorator"  # Modify child behavior


class BehaviorNode:
    """Represents a node in the behavior tree"""
    def __init__(
        self,
        node_id: str,
        node_type: NodeType,
        name: str,
        children: Optional[List['BehaviorNode']] = None,
        condition: Optional[Callable] = None,
        action: Optional[Callable] = None
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.name = name
        self.children = children or []
        self.condition = condition
        self.action = action
        self.status = NodeStatus.PENDING
        self.last_execution = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "children": [child.to_dict() for child in self.children],
            "status": self.status.value,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None
        }


class BehaviorTree:
    """
    Behavior tree for hierarchical behavior management
    Local behavior execution, not LLM-dependent
    """
    
    def __init__(self):
        self.trees: Dict[str, BehaviorNode] = {}  # character_id -> root_node
        self.active_nodes: Dict[str, BehaviorNode] = {}  # character_id -> currently executing node
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize behavior tree system"""
        self.is_initialized = True
        print("Behavior Tree initialized")
    
    async def shutdown(self):
        """Shutdown behavior tree system"""
        self.is_initialized = False
        print("Behavior Tree shutdown")
    
    async def create_tree(
        self,
        character_id: str,
        tree_definition: Dict[str, Any]
    ) -> BehaviorNode:
        """Create a behavior tree from definition"""
        
        root_node = await self._build_node(tree_definition)
        self.trees[character_id] = root_node
        return root_node
    
    async def _build_node(self, node_def: Dict[str, Any]) -> BehaviorNode:
        """Build a node from definition"""
        
        node_id = node_def.get("node_id", str(uuid.uuid4()))
        node_type = NodeType(node_def.get("type", "sequence"))
        name = node_def.get("name", "unnamed")
        
        # Build children recursively
        children = []
        if "children" in node_def:
            for child_def in node_def["children"]:
                child = await self._build_node(child_def)
                children.append(child)
        
        # Create node
        node = BehaviorNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            children=children
        )
        
        return node
    
    async def execute_tree(
        self,
        character_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the behavior tree for a character"""
        
        if character_id not in self.trees:
            # Create default tree
            await self.create_default_tree(character_id)
        
        root_node = self.trees[character_id]
        result = await self._execute_node(root_node, context)
        
        return {
            "status": result.value,
            "executed_node": root_node.node_id,
            "context": context
        }
    
    async def _execute_node(
        self,
        node: BehaviorNode,
        context: Dict[str, Any]
    ) -> NodeStatus:
        """Execute a single node"""
        
        node.last_execution = datetime.utcnow()
        
        if node.node_type == NodeType.SEQUENCE:
            return await self._execute_sequence(node, context)
        elif node.node_type == NodeType.SELECTOR:
            return await self._execute_selector(node, context)
        elif node.node_type == NodeType.PARALLEL:
            return await self._execute_parallel(node, context)
        elif node.node_type == NodeType.CONDITION:
            return await self._execute_condition(node, context)
        elif node.node_type == NodeType.ACTION:
            return await self._execute_action(node, context)
        elif node.node_type == NodeType.DECORATOR:
            return await self._execute_decorator(node, context)
        else:
            return NodeStatus.FAILURE
    
    async def _execute_sequence(
        self,
        node: BehaviorNode,
        context: Dict[str, Any]
    ) -> NodeStatus:
        """Execute sequence node (all children must succeed)"""
        
        for child in node.children:
            result = await self._execute_node(child, context)
            if result == NodeStatus.FAILURE:
                node.status = NodeStatus.FAILURE
                return NodeStatus.FAILURE
            elif result == NodeStatus.RUNNING:
                node.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
        
        node.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS
    
    async def _execute_selector(
        self,
        node: BehaviorNode,
        context: Dict[str, Any]
    ) -> NodeStatus:
        """Execute selector node (one child must succeed)"""
        
        for child in node.children:
            result = await self._execute_node(child, context)
            if result == NodeStatus.SUCCESS:
                node.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            elif result == NodeStatus.RUNNING:
                node.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
        
        node.status = NodeStatus.FAILURE
        return NodeStatus.FAILURE
    
    async def _execute_parallel(
        self,
        node: BehaviorNode,
        context: Dict[str, Any]
    ) -> NodeStatus:
        """Execute parallel node (all children execute simultaneously)"""
        
        # Execute all children
        results = await asyncio.gather(
            *[self._execute_node(child, context) for child in node.children],
            return_exceptions=True
        )
        
        # Check results
        success_count = sum(1 for r in results if r == NodeStatus.SUCCESS)
        failure_count = sum(1 for r in results if r == NodeStatus.FAILURE)
        running_count = sum(1 for r in results if r == NodeStatus.RUNNING)
        
        if running_count > 0:
            node.status = NodeStatus.RUNNING
            return NodeStatus.RUNNING
        elif success_count > 0:
            node.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        else:
            node.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
    
    async def _execute_condition(
        self,
        node: BehaviorNode,
        context: Dict[str, Any]
    ) -> NodeStatus:
        """Execute condition node"""
        
        # Evaluate condition
        if node.condition:
            result = node.condition(context)
            node.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
        else:
            # Default condition: always true
            node.status = NodeStatus.SUCCESS
        
        return node.status
    
    async def _execute_action(
        self,
        node: BehaviorNode,
        context: Dict[str, Any]
    ) -> NodeStatus:
        """Execute action node"""
        
        if node.action:
            result = await node.action(context)
            node.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
        else:
            # Default action: succeed
            node.status = NodeStatus.SUCCESS
        
        return node.status
    
    async def _execute_decorator(
        self,
        node: BehaviorNode,
        context: Dict[str, Any]
    ) -> NodeStatus:
        """Execute decorator node (modifies child behavior)"""
        
        if not node.children:
            return NodeStatus.FAILURE
        
        child = node.children[0]
        child_result = await self._execute_node(child, context)
        
        # Decorator can modify the result
        # For now, just pass through
        node.status = child_result
        return child_result
    
    async def create_default_tree(self, character_id: str):
        """Create a default behavior tree for a character"""
        
        tree_definition = {
            "type": "selector",
            "name": "Root",
            "children": [
                {
                    "type": "sequence",
                    "name": "Emergency_Response",
                    "children": [
                        {
                            "type": "condition",
                            "name": "Is_In_Danger",
                            "condition": lambda ctx: ctx.get("emotions", {}).get("fear", 0) > 0.7
                        },
                        {
                            "type": "action",
                            "name": "Seek_Safety",
                            "action": lambda ctx: True  # Placeholder
                        }
                    ]
                },
                {
                    "type": "sequence",
                    "name": "Social_Interaction",
                    "children": [
                        {
                            "type": "condition",
                            "name": "Has_Social_Stimulus",
                            "condition": lambda ctx: ctx.get("stimulus_type") in ["text", "voice"]
                        },
                        {
                            "type": "action",
                            "name": "Respond",
                            "action": lambda ctx: True  # Placeholder
                        }
                    ]
                },
                {
                    "type": "sequence",
                    "name": "Exploration",
                    "children": [
                        {
                            "type": "condition",
                            "name": "Is_Curious",
                            "condition": lambda ctx: ctx.get("emotions", {}).get("curiosity", 0) > 0.6
                        },
                        {
                            "type": "action",
                            "name": "Explore",
                            "action": lambda ctx: True  # Placeholder
                        }
                    ]
                },
                {
                    "type": "action",
                    "name": "Idle",
                    "action": lambda ctx: True  # Placeholder
                }
            ]
        }
        
        await self.create_tree(character_id, tree_definition)
    
    def get_active_tree(self, character_id: str) -> Optional[BehaviorNode]:
        """Get the active behavior tree for a character"""
        return self.trees.get(character_id)
    
    def get_tree_structure(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get the structure of the behavior tree"""
        if character_id in self.trees:
            return self.trees[character_id].to_dict()
        return None
    
    async def update_tree_node(
        self,
        character_id: str,
        node_id: str,
        update_data: Dict[str, Any]
    ):
        """Update a node in the behavior tree"""
        
        if character_id not in self.trees:
            return
        
        def update_node(node: BehaviorNode):
            if node.node_id == node_id:
                if "condition" in update_data:
                    node.condition = update_data["condition"]
                if "action" in update_data:
                    node.action = update_data["action"]
                return True
            
            for child in node.children:
                if update_node(child):
                    return True
            
            return False
        
        update_node(self.trees[character_id])