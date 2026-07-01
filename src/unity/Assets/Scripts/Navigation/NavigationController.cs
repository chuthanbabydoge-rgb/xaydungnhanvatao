using UnityEngine;
using UnityEngine.AI;
using System.Collections.Generic;
using System;

namespace AICompanion.Navigation
{
    /// <summary>
    /// Navigation Controller - follows Single Responsibility Principle
    /// Manages character navigation using NavMesh and custom pathfinding
    /// </summary>
    public class NavigationController : MonoBehaviour
    {
        [Header("Navigation Components")]
        [SerializeField] private NavMeshAgent navMeshAgent;
        [SerializeField] private WorldGraph worldGraph;

        [Header("Navigation Settings")]
        [SerializeField] private float stoppingDistance = 0.5f;
        [SerializeField] private float acceleration = 8f;
        [SerializeField] private float angularSpeed = 120f;
        [SerializeField] private bool autoBraking = true;

        [Header("Path Following")]
        [SerializeField] private float pathRecalculateInterval = 0.5f;
        [SerializeField] private float cornerReachedDistance = 0.2f;

        private Vector3 currentDestination;
        private List<WorldNode> currentPath;
        private int currentPathIndex;
        private float lastPathRecalculateTime;
        private bool isNavigating;

        public event Action OnDestinationReached;
        public event Action OnPathInvalid;
        public event Action<Vector3> OnNavigationStarted;

        public bool IsNavigating => isNavigating;
        public Vector3 CurrentDestination => currentDestination;

        private void Start()
        {
            InitializeNavMeshAgent();
        }

        private void InitializeNavMeshAgent()
        {
            if (navMeshAgent == null)
            {
                navMeshAgent = GetComponent<NavMeshAgent>();
            }

            if (navMeshAgent == null)
            {
                navMeshAgent = gameObject.AddComponent<NavMeshAgent>();
            }

            // Configure NavMesh agent
            navMeshAgent.stoppingDistance = stoppingDistance;
            navMeshAgent.acceleration = acceleration;
            navMeshAgent.angularSpeed = angularSpeed;
            navMeshAgent.autoBraking = autoBraking;
            navMeshAgent.updateRotation = true;
            navMeshAgent.updatePosition = true;
        }

        private void Update()
        {
            if (!isNavigating) return;

            UpdateNavigation();
        }

        private void UpdateNavigation()
        {
            // Check if destination reached
            if (navMeshAgent.remainingDistance <= stoppingDistance)
            {
                ReachDestination();
                return;
            }

            // Recalculate path periodically
            if (Time.time - lastPathRecalculateTime >= pathRecalculateInterval)
            {
                RecalculatePath();
                lastPathRecalculateTime = Time.time;
            }

            // Follow custom path if available
            if (currentPath != null && currentPath.Count > 0)
            {
                FollowCustomPath();
            }
        }

        public void SetDestination(Vector3 destination)
        {
            currentDestination = destination;
            
            if (navMeshAgent.SetDestination(destination))
            {
                isNavigating = true;
                OnNavigationStarted?.Invoke(destination);
            }
            else
            {
                // Try custom pathfinding
                if (worldGraph != null)
                {
                    currentPath = worldGraph.FindPath(transform.position, destination);
                    if (currentPath.Count > 0)
                    {
                        currentPathIndex = 0;
                        isNavigating = true;
                        OnNavigationStarted?.Invoke(destination);
                    }
                    else
                    {
                        OnPathInvalid?.Invoke();
                    }
                }
                else
                {
                    OnPathInvalid?.Invoke();
                }
            }
        }

        public void SetDestination(GameObject target)
        {
            if (target != null)
            {
                SetDestination(target.transform.position);
            }
        }

        private void RecalculatePath()
        {
            if (navMeshAgent.hasPath)
            {
                navMeshAgent.SetDestination(currentDestination);
            }
        }

        private void FollowCustomPath()
        {
            if (currentPathIndex >= currentPath.Count)
            {
                ReachDestination();
                return;
            }

            WorldNode targetNode = currentPath[currentPathIndex];
            Vector3 targetPosition = targetNode.position;

            // Check if reached current waypoint
            if (Vector3.Distance(transform.position, targetPosition) <= cornerReachedDistance)
            {
                currentPathIndex++;
                
                if (currentPathIndex >= currentPath.Count)
                {
                    ReachDestination();
                    return;
                }
            }

            // Move towards target
            Vector3 direction = (targetPosition - transform.position).normalized;
            transform.position += direction * navMeshAgent.speed * Time.deltaTime;
            
            // Rotate towards target
            Quaternion targetRotation = Quaternion.LookRotation(direction);
            transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * angularSpeed);
        }

        private void ReachDestination()
        {
            isNavigating = false;
            currentPath = null;
            currentPathIndex = 0;
            navMeshAgent.ResetPath();
            OnDestinationReached?.Invoke();
        }

        public void StopNavigation()
        {
            isNavigating = false;
            currentPath = null;
            navMeshAgent.ResetPath();
        }

        public void PauseNavigation()
        {
            if (navMeshAgent != null)
            {
                navMeshAgent.isStopped = true;
            }
        }

        public void ResumeNavigation()
        {
            if (navMeshAgent != null)
            {
                navMeshAgent.isStopped = false;
            }
        }

        public void SetNavigationSpeed(float speed)
        {
            if (navMeshAgent != null)
            {
                navMeshAgent.speed = speed;
            }
        }

        public void SetStoppingDistance(float distance)
        {
            stoppingDistance = distance;
            if (navMeshAgent != null)
            {
                navMeshAgent.stoppingDistance = distance;
            }
        }

        public void SetWorldGraph(WorldGraph graph)
        {
            worldGraph = graph;
        }

        public bool CanReachDestination(Vector3 destination)
        {
            NavMeshPath path = new NavMeshPath();
            return navMeshAgent.CalculatePath(destination, path);
        }

        public float GetRemainingDistance()
        {
            if (navMeshAgent.hasPath)
            {
                return navMeshAgent.remainingDistance;
            }
            return 0f;
        }

        public Vector3 GetNextWaypoint()
        {
            if (navMeshAgent.hasPath && navMeshAgent.path.corners.Length > 1)
            {
                return navMeshAgent.path.corners[1];
            }
            return currentDestination;
        }
    }
}
