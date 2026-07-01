using UnityEngine;
using System.Collections.Generic;
using System;

namespace AICompanion.Navigation
{
    /// <summary>
    /// World Graph - follows Single Responsibility Principle
    /// Manages spatial representation of the environment for navigation
    /// </summary>
    public class WorldGraph : MonoBehaviour
    {
        [Header("Graph Configuration")]
        [SerializeField] private float nodeSpacing = 1f;
        [SerializeField] private float connectionDistance = 2f;
        [SerializeField] private float maxSlope = 45f;
        [SerializeField] private LayerMask walkableLayers = -1;

        [Header("Debug Visualization")]
        [SerializeField] private bool showNodes = true;
        [SerializeField] private bool showConnections = true;
        [SerializeField] private Color nodeColor = Color.green;
        [SerializeField] private Color connectionColor = Color.blue;

        private List<WorldNode> nodes = new List<WorldNode>();
        private Dictionary<Vector3Int, WorldNode> nodeGrid = new Dictionary<Vector3Int, WorldNode>();
        private Bounds worldBounds;

        public event Action OnWorldGraphUpdated;

        [Serializable]
        public class WorldNode
        {
            public Vector3 position;
            public List<WorldNode> neighbors = new List<WorldNode>();
            public bool isWalkable;
            public float height;
            public float slope;

            public WorldNode(Vector3 pos)
            {
                position = pos;
                isWalkable = true;
                height = pos.y;
                slope = 0f;
            }
        }

        private void Start()
        {
            InitializeWorldGraph();
        }

        private void InitializeWorldGraph()
        {
            // Define world bounds based on AR plane detection
            worldBounds = new Bounds(transform.position, new Vector3(10f, 5f, 10f));
            
            GenerateWorldGraph();
        }

        private void GenerateWorldGraph()
        {
            nodes.Clear();
            nodeGrid.Clear();

            // Generate nodes in a grid pattern
            Vector3 min = worldBounds.min;
            Vector3 max = worldBounds.max;

            for (float x = min.x; x <= max.x; x += nodeSpacing)
            {
                for (float z = min.z; z <= max.z; z += nodeSpacing)
                {
                    Vector3 nodePosition = new Vector3(x, 0f, z);
                    
                    // Raycast down to find ground height
                    RaycastHit hit;
                    if (Physics.Raycast(nodePosition + Vector3.up * 10f, Vector3.down, out hit, 20f, walkableLayers))
                    {
                        nodePosition.y = hit.point.y;
                        
                        // Check if walkable
                        bool isWalkable = CheckWalkability(hit);
                        
                        if (isWalkable)
                        {
                            WorldNode node = new WorldNode(nodePosition);
                            node.isWalkable = isWalkable;
                            node.height = hit.point.y;
                            
                            nodes.Add(node);
                            
                            // Add to grid for spatial lookup
                            Vector3Int gridPos = WorldToGridPosition(nodePosition);
                            nodeGrid[gridPos] = node;
                        }
                    }
                }
            }

            // Connect nodes
            ConnectNodes();

            OnWorldGraphUpdated?.Invoke();
        }

        private bool CheckWalkability(RaycastHit hit)
        {
            // Check slope
            float slope = Vector3.Angle(hit.normal, Vector3.up);
            if (slope > maxSlope)
            {
                return false;
            }

            // Check if valid walkable layer
            if (!IsInLayerMask(hit.collider.gameObject.layer, walkableLayers))
            {
                return false;
            }

            return true;
        }

        private bool IsInLayerMask(int layer, LayerMask layerMask)
        {
            return layerMask == (layerMask | (1 << layer));
        }

        private void ConnectNodes()
        {
            foreach (WorldNode node in nodes)
            {
                node.neighbors.Clear();

                // Find nearby nodes
                foreach (WorldNode otherNode in nodes)
                {
                    if (node == otherNode) continue;

                    float distance = Vector3.Distance(node.position, otherNode.position);
                    
                    if (distance <= connectionDistance)
                    {
                        // Check if connection is valid (no obstacles)
                        if (IsValidConnection(node.position, otherNode.position))
                        {
                            node.neighbors.Add(otherNode);
                        }
                    }
                }
            }
        }

        private bool IsValidConnection(Vector3 from, Vector3 to)
        {
            // Check for obstacles between nodes
            Vector3 direction = (to - from).normalized;
            float distance = Vector3.Distance(from, to);

            RaycastHit hit;
            if (Physics.Raycast(from + Vector3.up * 0.5f, direction, out hit, distance, walkableLayers))
            {
                return false;
            }

            return true;
        }

        private Vector3Int WorldToGridPosition(Vector3 worldPosition)
        {
            return new Vector3Int(
                Mathf.RoundToInt(worldPosition.x / nodeSpacing),
                Mathf.RoundToInt(worldPosition.y / nodeSpacing),
                Mathf.RoundToInt(worldPosition.z / nodeSpacing)
            );
        }

        public WorldNode GetNearestNode(Vector3 position)
        {
            WorldNode nearestNode = null;
            float nearestDistance = float.MaxValue;

            foreach (WorldNode node in nodes)
            {
                float distance = Vector3.Distance(position, node.position);
                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearestNode = node;
                }
            }

            return nearestNode;
        }

        public List<WorldNode> FindPath(Vector3 startPosition, Vector3 endPosition)
        {
            WorldNode startNode = GetNearestNode(startPosition);
            WorldNode endNode = GetNearestNode(endPosition);

            if (startNode == null || endNode == null)
            {
                return new List<WorldNode>();
            }

            return FindPathAStar(startNode, endNode);
        }

        private List<WorldNode> FindPathAStar(WorldNode startNode, WorldNode endNode)
        {
            // A* pathfinding implementation
            List<WorldNode> openSet = new List<WorldNode>();
            HashSet<WorldNode> closedSet = new HashSet<WorldNode>();
            Dictionary<WorldNode, WorldNode> cameFrom = new Dictionary<WorldNode, WorldNode>();
            Dictionary<WorldNode, float> gScore = new Dictionary<WorldNode, float>();
            Dictionary<WorldNode, float> fScore = new Dictionary<WorldNode, float>();

            openSet.Add(startNode);
            gScore[startNode] = 0f;
            fScore[startNode] = HeuristicCostEstimate(startNode, endNode);

            while (openSet.Count > 0)
            {
                WorldNode current = GetLowestFScoreNode(openSet, fScore);

                if (current == endNode)
                {
                    return ReconstructPath(cameFrom, current);
                }

                openSet.Remove(current);
                closedSet.Add(current);

                foreach (WorldNode neighbor in current.neighbors)
                {
                    if (closedSet.Contains(neighbor)) continue;

                    float tentativeGScore = gScore[current] + Vector3.Distance(current.position, neighbor.position);

                    if (!openSet.Contains(neighbor))
                    {
                        openSet.Add(neighbor);
                    }
                    else if (tentativeGScore >= gScore[neighbor])
                    {
                        continue;
                    }

                    cameFrom[neighbor] = current;
                    gScore[neighbor] = tentativeGScore;
                    fScore[neighbor] = gScore[neighbor] + HeuristicCostEstimate(neighbor, endNode);
                }
            }

            return new List<WorldNode>(); // No path found
        }

        private WorldNode GetLowestFScoreNode(List<WorldNode> openSet, Dictionary<WorldNode, float> fScore)
        {
            WorldNode lowestNode = null;
            float lowestScore = float.MaxValue;

            foreach (WorldNode node in openSet)
            {
                float score = fScore.ContainsKey(node) ? fScore[node] : float.MaxValue;
                if (score < lowestScore)
                {
                    lowestScore = score;
                    lowestNode = node;
                }
            }

            return lowestNode;
        }

        private float HeuristicCostEstimate(WorldNode from, WorldNode to)
        {
            return Vector3.Distance(from.position, to.position);
        }

        private List<WorldNode> ReconstructPath(Dictionary<WorldNode, WorldNode> cameFrom, WorldNode current)
        {
            List<WorldNode> path = new List<WorldNode> { current };

            while (cameFrom.ContainsKey(current))
            {
                current = cameFrom[current];
                path.Add(current);
            }

            path.Reverse();
            return path;
        }

        public void UpdateWorldBounds(Bounds newBounds)
        {
            worldBounds = newBounds;
            GenerateWorldGraph();
        }

        public void RegenerateGraph()
        {
            GenerateWorldGraph();
        }

        private void OnDrawGizmos()
        {
            if (!showNodes && !showConnections) return;

            // Draw nodes
            if (showNodes)
            {
                Gizmos.color = nodeColor;
                foreach (WorldNode node in nodes)
                {
                    Gizmos.DrawSphere(node.position, 0.1f);
                }
            }

            // Draw connections
            if (showConnections)
            {
                Gizmos.color = connectionColor;
                foreach (WorldNode node in nodes)
                {
                    foreach (WorldNode neighbor in node.neighbors)
                    {
                        Gizmos.DrawLine(node.position, neighbor.position);
                    }
                }
            }
        }
    }
}
