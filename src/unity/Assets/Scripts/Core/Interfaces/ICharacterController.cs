using UnityEngine;

namespace AICompanion.Core.Interfaces
{
    /// <summary>
    /// Interface for character controller - follows Interface Segregation Principle
    /// </summary>
    public interface ICharacterController
    {
        void Move(Vector3 direction);
        void Rotate(Quaternion rotation);
        void Jump();
        void SetMovementSpeed(float speed);
        Vector3 Position { get; }
        Quaternion Rotation { get; }
        bool IsGrounded { get; }
    }
}
