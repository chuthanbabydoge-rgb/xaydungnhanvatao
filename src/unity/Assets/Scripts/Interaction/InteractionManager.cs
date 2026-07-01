using UnityEngine;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Linq;

namespace AICompanion.Interaction
{
    /// <summary>
    /// Manages character interactions with environment objects
    /// </summary>
    public class InteractionManager : MonoBehaviour, IInteractionManager
    {
        [Header("Interaction Settings")]
        [SerializeField] private float defaultInteractionRange = 2f;
        [SerializeField] private float interactionCooldown = 0.5f;
        [SerializeField] private bool showInteractionGizmos = true;

        [Header("Interaction State")]
        [SerializeField] private InteractionEvent currentInteraction;
        [SerializeField] private bool isInteracting = false;
        [SerializeField] private float lastInteractionTime = 0f;

        // Registered interactables
        private Dictionary<string, IInteractable> registeredInteractables = new Dictionary<string, IInteractable>();

        // Events
        public event Action<InteractionEvent> OnInteractionStarted;
        public event Action<InteractionEvent> OnInteractionEnded;
        public event Action<InteractionEvent> OnInteractionFailed;

        // Properties
        public bool IsInteracting => isInteracting;
        public InteractionEvent CurrentInteraction => currentInteraction;

        private void Update()
        {
            // Update current interaction if active
            if (isInteracting && currentInteraction != null && currentInteraction.interactable != null)
            {
                currentInteraction.duration = Time.time - currentInteraction.startTime;
                currentInteraction.interactable.OnInteractionUpdate(Time.deltaTime);
            }
        }

        private void OnDrawGizmos()
        {
            if (!showInteractionGizmos) return;

            // Draw interaction range for current transform
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(transform.position, defaultInteractionRange);

            // Draw interaction points for all registered interactables
            foreach (var interactable in registeredInteractables.Values)
            {
                if (interactable.Transform != null)
                {
                    Gizmos.color = Color.cyan;
                    Vector3 interactionPoint = interactable.GetInteractionPoint();
                    Gizmos.DrawWireSphere(interactionPoint, 0.1f);
                    Gizmos.DrawLine(interactable.Transform.position, interactionPoint);
                }
            }
        }

        /// <summary>
        /// Start interaction with an object
        /// </summary>
        public async Task<bool> StartInteractionAsync(IInteractable interactable, InteractionType interactionType)
        {
            if (interactable == null)
            {
                Debug.LogWarning("Cannot start interaction - null interactable");
                return false;
            }

            if (isInteracting)
            {
                Debug.LogWarning("Already interacting with another object");
                return false;
            }

            // Check cooldown
            if (Time.time - lastInteractionTime < interactionCooldown)
            {
                Debug.LogWarning("Interaction on cooldown");
                return false;
            }

            // Check if interaction is possible
            if (!interactable.CanInteract(interactionType))
            {
                Debug.LogWarning($"Interaction type {interactionType} not supported by {interactable.Id}");
                return false;
            }

            // Check range
            float distance = Vector3.Distance(transform.position, interactable.GetInteractionPoint());
            if (distance > interactable.GetInteractionRange())
            {
                Debug.LogWarning($"Object {interactable.Id} out of range");
                return false;
            }

            // Create interaction event
            currentInteraction = new InteractionEvent
            {
                interactable = interactable,
                interactionType = interactionType,
                interactionPoint = interactable.GetInteractionPoint(),
                startTime = Time.time,
                duration = 0f
            };

            isInteracting = true;
            lastInteractionTime = Time.time;

            try
            {
                Debug.Log($"Starting {interactionType} interaction with {interactable.Id}");

                // Call interaction start on the object
                bool success = await interactable.OnInteractionStart(interactionType);

                if (success)
                {
                    currentInteraction.isSuccess = true;
                    OnInteractionStarted?.Invoke(currentInteraction);
                    Debug.Log($"Interaction started successfully with {interactable.Id}");
                    return true;
                }
                else
                {
                    currentInteraction.isSuccess = false;
                    currentInteraction.errorMessage = "Interaction rejected by object";
                    OnInteractionFailed?.Invoke(currentInteraction);
                    EndInteraction();
                    return false;
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"Interaction start error: {ex.Message}");
                currentInteraction.isSuccess = false;
                currentInteraction.errorMessage = ex.Message;
                OnInteractionFailed?.Invoke(currentInteraction);
                EndInteraction();
                return false;
            }
        }

        /// <summary>
        /// End current interaction
        /// </summary>
        public void EndInteraction()
        {
            if (!isInteracting || currentInteraction == null)
            {
                return;
            }

            try
            {
                Debug.Log($"Ending interaction with {currentInteraction.interactable?.Id}");

                // Call interaction end on the object
                currentInteraction.interactable?.OnInteractionEnd();

                // Trigger event
                OnInteractionEnded?.Invoke(currentInteraction);
            }
            catch (Exception ex)
            {
                Debug.LogError($"Interaction end error: {ex.Message}");
            }
            finally
            {
                // Reset state
                currentInteraction = null;
                isInteracting = false;
            }
        }

        /// <summary>
        /// Cancel current interaction
        /// </summary>
        public void CancelInteraction()
        {
            if (!isInteracting)
            {
                return;
            }

            Debug.Log("Cancelling current interaction");
            
            if (currentInteraction != null)
            {
                currentInteraction.isSuccess = false;
                currentInteraction.errorMessage = "Interaction cancelled";
                OnInteractionFailed?.Invoke(currentInteraction);
            }

            EndInteraction();
        }

        /// <summary>
        /// Register interactable object
        /// </summary>
        public void RegisterInteractable(IInteractable interactable)
        {
            if (interactable == null)
            {
                Debug.LogWarning("Cannot register null interactable");
                return;
            }

            if (string.IsNullOrEmpty(interactable.Id))
            {
                Debug.LogWarning("Cannot register interactable with null or empty ID");
                return;
            }

            if (registeredInteractables.ContainsKey(interactable.Id))
            {
                Debug.LogWarning($"Interactable {interactable.Id} already registered");
                return;
            }

            registeredInteractables.Add(interactable.Id, interactable);
            Debug.Log($"Registered interactable: {interactable.Id}");
        }

        /// <summary>
        /// Unregister interactable object
        /// </summary>
        public void UnregisterInteractable(IInteractable interactable)
        {
            if (interactable == null)
            {
                Debug.LogWarning("Cannot unregister null interactable");
                return;
            }

            if (registeredInteractables.Remove(interactable.Id))
            {
                Debug.Log($"Unregistered interactable: {interactable.Id}");

                // End interaction if this is the current interaction
                if (isInteracting && currentInteraction?.interactable == interactable)
                {
                    EndInteraction();
                }
            }
            else
            {
                Debug.LogWarning($"Interactable {interactable.Id} not found in registry");
            }
        }

        /// <summary>
        /// Find nearest interactable within range
        /// </summary>
        public IInteractable FindNearestInteractable(Vector3 position, float range)
        {
            IInteractable nearest = null;
            float nearestDistance = range;

            foreach (var interactable in registeredInteractables.Values)
            {
                if (interactable.Transform == null) continue;

                float distance = Vector3.Distance(position, interactable.GetInteractionPoint());
                
                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearest = interactable;
                }
            }

            return nearest;
        }

        /// <summary>
        /// Get all interactables within range
        /// </summary>
        public IInteractable[] GetInteractablesInRange(Vector3 position, float range)
        {
            return registeredInteractables.Values
                .Where(i => i.Transform != null)
                .Where(i => Vector3.Distance(position, i.GetInteractionPoint()) <= range)
                .ToArray();
        }

        /// <summary>
        /// Get all registered interactables
        /// </summary>
        public IInteractable[] GetAllInteractables()
        {
            return registeredInteractables.Values.ToArray();
        }

        /// <summary>
        /// Get interactable by ID
        /// </summary>
        public IInteractable GetInteractable(string id)
        {
            registeredInteractables.TryGetValue(id, out IInteractable interactable);
            return interactable;
        }

        /// <summary>
        /// Clear all registered interactables
        /// </summary>
        public void ClearAllInteractables()
        {
            // End current interaction if active
            if (isInteracting)
            {
                EndInteraction();
            }

            registeredInteractables.Clear();
            Debug.Log("Cleared all interactables");
        }

        private void OnDestroy()
        {
            // End current interaction
            if (isInteracting)
            {
                EndInteraction();
            }

            // Clear all interactables
            ClearAllInteractables();
        }
    }
}