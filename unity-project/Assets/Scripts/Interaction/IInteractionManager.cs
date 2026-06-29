using UnityEngine;
using System;
using System.Threading.Tasks;

namespace AICompanion.Interaction
{
    /// <summary>
    /// Interface for interaction manager handling character-environment interactions
    /// </summary>
    public interface IInteractionManager
    {
        /// <summary>
        /// Event triggered when interaction starts
        /// </summary>
        event Action<InteractionEvent> OnInteractionStarted;

        /// <summary>
        /// Event triggered when interaction ends
        /// </summary>
        event Action<InteractionEvent> OnInteractionEnded;

        /// <summary>
        /// Event triggered when interaction fails
        /// </summary>
        event Action<InteractionEvent> OnInteractionFailed;

        /// <summary>
        /// Start interaction with an object
        /// </summary>
        /// <param name="interactable">Target interactable object</param>
        /// <param name="interactionType">Type of interaction</param>
        /// <returns>Success status</returns>
        Task<bool> StartInteractionAsync(IInteractable interactable, InteractionType interactionType);

        /// <summary>
        /// End current interaction
        /// </summary>
        void EndInteraction();

        /// <summary>
        /// Cancel current interaction
        /// </summary>
        void CancelInteraction();

        /// <summary>
        /// Check if currently interacting
        /// </summary>
        bool IsInteracting { get; }

        /// <summary>
        /// Get current interaction
        /// </summary>
        InteractionEvent CurrentInteraction { get; }

        /// <summary>
        /// Register interactable object
        /// </summary>
        void RegisterInteractable(IInteractable interactable);

        /// <summary>
        /// Unregister interactable object
        /// </summary>
        void UnregisterInteractable(IInteractable interactable);

        /// <summary>
        /// Find nearest interactable within range
        /// </summary>
        IInteractable FindNearestInteractable(Vector3 position, float range);

        /// <summary>
        /// Get all interactables within range
        /// </summary>
        IInteractable[] GetInteractablesInRange(Vector3 position, float range);
    }

    /// <summary>
    /// Interface for interactable objects
    /// </summary>
    public interface IInteractable
    {
        /// <summary>
        /// Unique identifier for the interactable
        /// </summary>
        string Id { get; }

        /// <summary>
        /// Transform of the interactable
        /// </summary>
        Transform Transform { get; }

        /// <summary>
        /// Check if interaction is possible
        /// </summary>
        bool CanInteract(InteractionType interactionType);

        /// <summary>
        /// Start interaction
        /// </summary>
        Task<bool> OnInteractionStart(InteractionType interactionType);

        /// <summary>
        /// Update interaction
        /// </summary>
        void OnInteractionUpdate(float deltaTime);

        /// <summary>
        /// End interaction
        /// </summary>
        void OnInteractionEnd();

        /// <summary>
        /// Get interaction point
        /// </summary>
        Vector3 GetInteractionPoint();

        /// <summary>
        /// Get interaction range
        /// </summary>
        float GetInteractionRange();
    }

    /// <summary>
    /// Interaction type enumeration
    /// </summary>
    public enum InteractionType
    {
        None,
        Touch,
        Grab,
        Hold,
        Use,
        Inspect,
        Talk,
        Gesture,
        Custom
    }

    /// <summary>
    /// Interaction event data structure
    /// </summary>
    [Serializable]
    public class InteractionEvent
    {
        public IInteractable interactable;
        public InteractionType interactionType;
        public Vector3 interactionPoint;
        public float startTime;
        public float duration;
        public bool isSuccess;
        public string errorMessage;

        public InteractionEvent()
        {
            interactionType = InteractionType.None;
            interactionPoint = Vector3.zero;
            startTime = Time.time;
            duration = 0f;
            isSuccess = false;
        }
    }
}