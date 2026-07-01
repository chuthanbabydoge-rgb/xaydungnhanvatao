using UnityEngine;
using System;
using System.Threading.Tasks;
using System.Collections.Generic;

namespace AICompanion.Physics
{
    /// <summary>
    /// Manages character physics including movement, collisions, and forces
    /// </summary>
    public class PhysicsController : MonoBehaviour, IPhysicsController
    {
        [Header("Physics Configuration")]
        [SerializeField] private float mass = 70f;
        [SerializeField] private float drag = 0f;
        [SerializeField] private float angularDrag = 0.05f;
        [SerializeField] private bool useGravity = true;
        [SerializeField] private bool isKinematic = false;

        [Header("Ground Detection")]
        [SerializeField] private float groundCheckDistance = 0.1f;
        [SerializeField] private LayerMask groundLayer = 1;
        [SerializeField] private Vector3 groundCheckOffset = Vector3.zero;
        [SerializeField] private bool showGroundCheckGizmos = true;

        [Header("Movement Settings")]
        [SerializeField] private float maxVelocity = 10f;
        [SerializeField] private float maxAngularVelocity = 10f;
        [SerializeField] private bool constrainPositionX = false;
        [SerializeField] private bool constrainPositionY = false;
        [SerializeField] private bool constrainPositionZ = false;

        [Header("Physics State")]
        [SerializeField] private bool isGrounded = false;
        [SerializeField] private bool isPhysicsEnabled = true;
        [SerializeField] private Vector3 currentVelocity = Vector3.zero;
        [SerializeField] private Vector3 currentAngularVelocity = Vector3.zero;

        // Components
        private Rigidbody rb;
        private CapsuleCollider capsuleCollider;
        private List<Collider> ignoredColliders = new List<Collider>();

        // Events
        public event Action<CollisionEvent> OnCollision;
        public event Action<TriggerEvent> OnTrigger;
        public event Action<bool> OnGroundStateChanged;

        // Properties
        public bool IsGrounded => isGrounded;
        public Vector3 Velocity => currentVelocity;
        public Vector3 AngularVelocity => currentAngularVelocity;

        private void Awake()
        {
            InitializeComponents();
        }

        private void Start()
        {
            InitializeAsync().ContinueWith(task =>
            {
                if (task.IsFaulted)
                {
                    Debug.LogError($"Physics Controller initialization failed: {task.Exception}");
                }
            });
        }

        private void FixedUpdate()
        {
            if (!isPhysicsEnabled) return;

            UpdatePhysicsState();
            CheckGrounded();
            ApplyConstraints();
        }

        private void OnCollisionEnter(Collision collision)
        {
            HandleCollision(collision, true);
        }

        private void OnCollisionStay(Collision collision)
        {
            HandleCollision(collision, false);
        }

        private void OnTriggerEnter(Collider other)
        {
            HandleTrigger(other, true);
        }

        private void OnTriggerExit(Collider other)
        {
            HandleTrigger(other, false);
        }

        private void OnDrawGizmos()
        {
            if (!showGroundCheckGizmos) return;

            // Draw ground check
            Gizmos.color = isGrounded ? Color.green : Color.red;
            Vector3 checkPosition = transform.position + groundCheckOffset;
            Gizmos.DrawWireSphere(checkPosition, groundCheckDistance);
        }

        /// <summary>
        /// Initialize physics components
        /// </summary>
        private void InitializeComponents()
        {
            // Get or add Rigidbody
            rb = GetComponent<Rigidbody>();
            if (rb == null)
            {
                rb = gameObject.AddComponent<Rigidbody>();
            }

            // Configure Rigidbody
            rb.mass = mass;
            rb.drag = drag;
            rb.angularDrag = angularDrag;
            rb.useGravity = useGravity;
            rb.isKinematic = isKinematic;
            rb.interpolation = RigidbodyInterpolation.Interpolate;
            rb.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;

            // Get or add CapsuleCollider
            capsuleCollider = GetComponent<CapsuleCollider>();
            if (capsuleCollider == null)
            {
                capsuleCollider = gameObject.AddComponent<CapsuleCollider>();
            }

            Debug.Log("Physics components initialized");
        }

        /// <summary>
        /// Initialize physics controller
        /// </summary>
        public async Task InitializeAsync()
        {
            try
            {
                Debug.Log("Initializing Physics Controller...");

                // Wait for physics system to be ready
                await Task.Yield();

                // Initial ground check
                CheckGrounded();

                isPhysicsEnabled = true;
                Debug.Log("Physics Controller initialized successfully");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Physics Controller initialization error: {ex.Message}");
                throw;
            }
        }

        /// <summary>
        /// Shutdown physics controller
        /// </summary>
        public async Task ShutdownAsync()
        {
            try
            {
                Debug.Log("Shutting down Physics Controller...");

                isPhysicsEnabled = false;

                // Clear ignored colliders
                ignoredColliders.Clear();

                Debug.Log("Physics Controller shutdown complete");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Physics Controller shutdown error: {ex.Message}");
            }

            await Task.CompletedTask;
        }

        /// <summary>
        /// Update physics state
        /// </summary>
        private void UpdatePhysicsState()
        {
            if (rb != null)
            {
                currentVelocity = rb.velocity;
                currentAngularVelocity = rb.angularVelocity;
            }
        }

        /// <summary>
        /// Check if character is grounded
        /// </summary>
        private void CheckGrounded()
        {
            bool wasGrounded = isGrounded;

            Vector3 checkPosition = transform.position + groundCheckOffset;
            isGrounded = Physics.CheckSphere(checkPosition, groundCheckDistance, groundLayer);

            if (isGrounded != wasGrounded)
            {
                OnGroundStateChanged?.Invoke(isGrounded);
                Debug.Log($"Ground state changed: {isGrounded}");
            }
        }

        /// <summary>
        /// Handle collision
        /// </summary>
        private void HandleCollision(Collision collision, bool isEnter)
        {
            if (ignoredColliders.Contains(collision.collider))
            {
                return;
            }

            CollisionEvent collisionEvent = new CollisionEvent
            {
                collider = collision.collider,
                contactPoint = collision.contacts[0].point,
                contactNormal = collision.contacts[0].normal,
                relativeVelocity = collision.relativeVelocity.magnitude,
                impactForce = collision.impulse.magnitude / Time.fixedDeltaTime,
                timestamp = Time.time
            };

            OnCollision?.Invoke(collisionEvent);

            if (isEnter)
            {
                Debug.Log($"Collision entered with {collision.collider.name}");
            }
        }

        /// <summary>
        /// Handle trigger
        /// </summary>
        private void HandleTrigger(Collider other, bool enter)
        {
            if (ignoredColliders.Contains(other))
            {
                return;
            }

            TriggerEvent triggerEvent = new TriggerEvent
            {
                collider = other,
                enter = enter,
                position = other.transform.position,
                timestamp = Time.time
            };

            OnTrigger?.Invoke(triggerEvent);

            Debug.Log($"Trigger { (enter ? "entered" : "exited") } with {other.name}");
        }

        /// <summary>
        /// Apply constraints
        /// </summary>
        private void ApplyConstraints()
        {
            if (rb == null) return;

            // Position constraints
            if (constrainPositionX)
            {
                rb.constraints |= RigidbodyConstraints.FreezePositionX;
            }
            else
            {
                rb.constraints &= ~RigidbodyConstraints.FreezePositionX;
            }

            if (constrainPositionY)
            {
                rb.constraints |= RigidbodyConstraints.FreezePositionY;
            }
            else
            {
                rb.constraints &= ~RigidbodyConstraints.FreezePositionY;
            }

            if (constrainPositionZ)
            {
                rb.constraints |= RigidbodyConstraints.FreezePositionZ;
            }
            else
            {
                rb.constraints &= ~RigidbodyConstraints.FreezePositionZ;
            }

            // Velocity constraints
            if (rb.velocity.magnitude > maxVelocity)
            {
                rb.velocity = rb.velocity.normalized * maxVelocity;
            }

            if (rb.angularVelocity.magnitude > maxAngularVelocity)
            {
                rb.angularVelocity = rb.angularVelocity.normalized * maxAngularVelocity;
            }
        }

        /// <summary>
        /// Apply force to character
        /// </summary>
        public void ApplyForce(Vector3 force, ForceMode mode = ForceMode.Force)
        {
            if (!isPhysicsEnabled || rb == null) return;

            rb.AddForce(force, mode);
        }

        /// <summary>
        /// Apply torque to character
        /// </summary>
        public void ApplyTorque(Vector3 torque, ForceMode mode = ForceMode.Force)
        {
            if (!isPhysicsEnabled || rb == null) return;

            rb.AddTorque(torque, mode);
        }

        /// <summary>
        /// Set character velocity
        /// </summary>
        public void SetVelocity(Vector3 velocity)
        {
            if (!isPhysicsEnabled || rb == null) return;

            rb.velocity = velocity;
        }

        /// <summary>
        /// Set character angular velocity
        /// </summary>
        public void SetAngularVelocity(Vector3 angularVelocity)
        {
            if (!isPhysicsEnabled || rb == null) return;

            rb.angularVelocity = angularVelocity;
        }

        /// <summary>
        /// Move character to position
        /// </summary>
        public bool MoveTo(Vector3 position, bool checkCollision = true)
        {
            if (!isPhysicsEnabled) return false;

            if (checkCollision && !IsPositionValid(position))
            {
                Debug.LogWarning("Cannot move to invalid position");
                return false;
            }

            if (rb != null)
            {
                rb.MovePosition(position);
            }
            else
            {
                transform.position = position;
            }

            return true;
        }

        /// <summary>
        /// Rotate character to rotation
        /// </summary>
        public void RotateTo(Quaternion rotation)
        {
            if (!isPhysicsEnabled) return;

            if (rb != null)
            {
                rb.MoveRotation(rotation);
            }
            else
            {
                transform.rotation = rotation;
            }
        }

        /// <summary>
        /// Jump with specified force
        /// </summary>
        public void Jump(float jumpForce)
        {
            if (!isGrounded || !isPhysicsEnabled)
            {
                Debug.LogWarning("Cannot jump - not grounded or physics disabled");
                return;
            }

            if (rb != null)
            {
                rb.AddForce(Vector3.up * jumpForce, ForceMode.Impulse);
                Debug.Log($"Jumping with force: {jumpForce}");
            }
        }

        /// <summary>
        /// Check if position is valid (not colliding)
        /// </summary>
        public bool IsPositionValid(Vector3 position)
        {
            if (capsuleCollider == null) return true;

            // Check if position would cause collision
            Vector3 originalPosition = transform.position;
            transform.position = position;

            bool isValid = !capsuleCollider.isTrigger;

            transform.position = originalPosition;

            return isValid;
        }

        /// <summary>
        /// Get ground height at position
        /// </summary>
        public float GetGroundHeight(Vector3 position)
        {
            RaycastHit hit;
            if (Physics.Raycast(position + Vector3.up * 10f, Vector3.down, out hit, 20f, groundLayer))
            {
                return hit.point.y;
            }

            return position.y;
        }

        /// <summary>
        /// Enable/disable physics
        /// </summary>
        public void SetPhysicsEnabled(bool enabled)
        {
            isPhysicsEnabled = enabled;

            if (rb != null)
            {
                rb.isKinematic = !enabled;
            }

            Debug.Log($"Physics {(enabled ? "enabled" : "disabled")}");
        }

        /// <summary>
        /// Ignore collision with collider
        /// </summary>
        public void IgnoreCollision(Collider collider, bool ignore = true)
        {
            if (collider == null) return;

            if (ignore)
            {
                if (!ignoredColliders.Contains(collider))
                {
                    ignoredColliders.Add(collider);
                }

                if (capsuleCollider != null)
                {
                    Physics.IgnoreCollision(capsuleCollider, collider, true);
                }
            }
            else
            {
                ignoredColliders.Remove(collider);

                if (capsuleCollider != null)
                {
                    Physics.IgnoreCollision(capsuleCollider, collider, false);
                }
            }
        }

        /// <summary>
        /// Set mass
        /// </summary>
        public void SetMass(float newMass)
        {
            mass = newMass;
            if (rb != null)
            {
                rb.mass = mass;
            }
        }

        /// <summary>
        /// Set drag
        /// </summary>
        public void SetDrag(float newDrag)
        {
            drag = newDrag;
            if (rb != null)
            {
                rb.drag = drag;
            }
        }

        /// <summary>
        /// Set ground check distance
        /// </summary>
        public void SetGroundCheckDistance(float distance)
        {
            groundCheckDistance = distance;
        }

        /// <summary>
        /// Set ground layer
        /// </summary>
        public void SetGroundLayer(LayerMask layer)
        {
            groundLayer = layer;
        }
    }
}