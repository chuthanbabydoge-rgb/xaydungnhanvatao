using UnityEngine;
using System;
using System.Threading.Tasks;

namespace AICompanion.Physics
{
    /// <summary>
    /// Interface for physics controller managing character physics and collisions
    /// </summary>
    public interface IPhysicsController
    {
        /// <summary>
        /// Event triggered when collision occurs
        /// </summary>
        event Action<CollisionEvent> OnCollision;

        /// <summary>
        /// Event triggered when trigger occurs
        /// </summary>
        event Action<TriggerEvent> OnTrigger;

        /// <summary>
        /// Event triggered when ground state changes
        /// </summary>
        event Action<bool> OnGroundStateChanged;

        /// <summary>
        /// Check if character is grounded
        /// </summary>
        bool IsGrounded { get; }

        /// <summary>
        /// Get current velocity
        /// </summary>
        Vector3 Velocity { get; }

        /// <summary>
        /// Get current angular velocity
        /// </summary>
        Vector3 AngularVelocity { get; }

        /// <summary>
        /// Apply force to character
        /// </summary>
        /// <param name="force">Force vector</param>
        /// <param name="mode">Force mode</param>
        void ApplyForce(Vector3 force, ForceMode mode = ForceMode.Force);

        /// <summary>
        /// Apply torque to character
        /// </summary>
        /// <param name="torque">Torque vector</param>
        /// <param name="mode">Force mode</param>
        void ApplyTorque(Vector3 torque, ForceMode mode = ForceMode.Force);

        /// <summary>
        /// Set character velocity
        /// </summary>
        /// <param name="velocity">Target velocity</param>
        void SetVelocity(Vector3 velocity);

        /// <summary>
        /// Set character angular velocity
        /// </summary>
        /// <param name="angularVelocity">Target angular velocity</param>
        void SetAngularVelocity(Vector3 angularVelocity);

        /// <summary>
        /// Move character to position
        /// </summary>
        /// <param name="position">Target position</param>
        /// <param name="checkCollision">Whether to check for collisions</param>
        /// <returns>Move success status</returns>
        bool MoveTo(Vector3 position, bool checkCollision = true);

        /// <summary>
        /// Rotate character to rotation
        /// </summary>
        /// <param name="rotation">Target rotation</param>
        void RotateTo(Quaternion rotation);

        /// <summary>
        /// Jump with specified force
        /// </summary>
        /// <param name="jumpForce">Jump force magnitude</param>
        void Jump(float jumpForce);

        /// <summary>
        /// Check if position is valid (not colliding)
        /// </summary>
        /// <param name="position">Position to check</param>
        /// <returns>Validity status</returns>
        bool IsPositionValid(Vector3 position);

        /// <summary>
        /// Get ground height at position
        /// </summary>
        /// <param name="position">Position to check</param>
        /// <returns>Ground height</returns>
        float GetGroundHeight(Vector3 position);

        /// <summary>
        /// Enable/disable physics
        /// </summary>
        void SetPhysicsEnabled(bool enabled);

        /// <summary>
        /// Initialize physics controller
        /// </summary>
        Task InitializeAsync();

        /// <summary>
        /// Shutdown physics controller
        /// </summary>
        Task ShutdownAsync();
    }

    /// <summary>
    /// Collision event data structure
    /// </summary>
    [Serializable]
    public class CollisionEvent
    {
        public Collider collider;
        public Vector3 contactPoint;
        public Vector3 contactNormal;
        public float relativeVelocity;
        public float impactForce;
        public float timestamp;

        public CollisionEvent()
        {
            contactPoint = Vector3.zero;
            contactNormal = Vector3.up;
            relativeVelocity = 0f;
            impactForce = 0f;
            timestamp = Time.time;
        }
    }

    /// <summary>
    /// Trigger event data structure
    /// </summary>
    [Serializable]
    public class TriggerEvent
    {
        public Collider collider;
        public bool enter; // true for enter, false for exit
        public Vector3 position;
        public float timestamp;

        public TriggerEvent()
        {
            enter = true;
            position = Vector3.zero;
            timestamp = Time.time;
        }
    }
}