using UnityEngine;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace AICompanion.Interaction
{
    /// <summary>
    /// Base component for making objects interactable
    /// </summary>
    public class InteractableObject : MonoBehaviour, IInteractable
    {
        [Header("Interaction Settings")]
        [SerializeField] private string objectId;
        [SerializeField] private float interactionRange = 2f;
        [SerializeField] private Vector3 interactionOffset = Vector3.zero;
        [SerializeField] private InteractionType[] supportedInteractions = new InteractionType[] { InteractionType.Touch };

        [Header("Visual Feedback")]
        [SerializeField] private bool showHighlight = true;
        [SerializeField] private Color highlightColor = Color.yellow;
        [SerializeField] private GameObject highlightIndicator;

        [Header("Interaction State")]
        [SerializeField] private bool isInteracting = false;
        [SerializeField] private InteractionType currentInteractionType = InteractionType.None;

        // Original material color for highlighting
        private Renderer[] renderers;
        private Color[] originalColors;
        private bool isHighlighted = false;

        // Properties
        public string Id => objectId;
        public Transform Transform => transform;
        public bool IsInteracting => isInteracting;

        private void Awake()
        {
            // Generate ID if not set
            if (string.IsNullOrEmpty(objectId))
            {
                objectId = $"{gameObject.name}_{GetInstanceID()}";
            }

            // Cache renderers for highlighting
            renderers = GetComponentsInChildren<Renderer>();
            if (renderers.Length > 0)
            {
                originalColors = new Color[renderers.Length];
                for (int i = 0; i < renderers.Length; i++)
                {
                    originalColors[i] = renderers[i].material.color;
                }
            }

            // Create highlight indicator if needed
            if (showHighlight && highlightIndicator == null)
            {
                CreateHighlightIndicator();
            }
        }

        private void Start()
        {
            // Register with interaction manager if available
            InteractionManager interactionManager = FindObjectOfType<InteractionManager>();
            if (interactionManager != null)
            {
                interactionManager.RegisterInteractable(this);
            }
        }

        private void OnDestroy()
        {
            // Unregister from interaction manager
            InteractionManager interactionManager = FindObjectOfType<InteractionManager>();
            if (interactionManager != null)
            {
                interactionManager.UnregisterInteractable(this);
            }
        }

        /// <summary>
        /// Check if interaction is possible
        /// </summary>
        public bool CanInteract(InteractionType interactionType)
        {
            if (isInteracting)
            {
                return false;
            }

            foreach (InteractionType supported in supportedInteractions)
            {
                if (supported == interactionType)
                {
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// Start interaction
        /// </summary>
        public virtual async Task<bool> OnInteractionStart(InteractionType interactionType)
        {
            if (!CanInteract(interactionType))
            {
                return false;
            }

            isInteracting = true;
            currentInteractionType = interactionType;

            // Show visual feedback
            SetHighlight(true);

            Debug.Log($"Interaction started: {interactionType} on {objectId}");

            // Override in derived classes for specific interaction logic
            await Task.CompletedTask;
            return true;
        }

        /// <summary>
        /// Update interaction
        /// </summary>
        public virtual void OnInteractionUpdate(float deltaTime)
        {
            // Override in derived classes for continuous interaction logic
        }

        /// <summary>
        /// End interaction
        /// </summary>
        public virtual void OnInteractionEnd()
        {
            isInteracting = false;
            currentInteractionType = InteractionType.None;

            // Hide visual feedback
            SetHighlight(false);

            Debug.Log($"Interaction ended on {objectId}");
        }

        /// <summary>
        /// Get interaction point
        /// </summary>
        public virtual Vector3 GetInteractionPoint()
        {
            return transform.position + interactionOffset;
        }

        /// <summary>
        /// Get interaction range
        /// </summary>
        public float GetInteractionRange()
        {
            return interactionRange;
        }

        /// <summary>
        /// Set highlight state
        /// </summary>
        public void SetHighlight(bool highlight)
        {
            if (isHighlighted == highlight) return;

            isHighlighted = highlight;

            if (renderers != null && renderers.Length > 0)
            {
                for (int i = 0; i < renderers.Length; i++)
                {
                    if (renderers[i] != null && renderers[i].material != null)
                    {
                        renderers[i].material.color = highlight ? highlightColor : originalColors[i];
                    }
                }
            }

            if (highlightIndicator != null)
            {
                highlightIndicator.SetActive(highlight);
            }
        }

        /// <summary>
        /// Create highlight indicator
        /// </summary>
        private void CreateHighlightIndicator()
        {
            highlightIndicator = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            highlightIndicator.transform.SetParent(transform);
            highlightIndicator.transform.localPosition = interactionOffset;
            highlightIndicator.transform.localScale = Vector3.one * 0.2f;
            
            Renderer indicatorRenderer = highlightIndicator.GetComponent<Renderer>();
            if (indicatorRenderer != null)
            {
                indicatorRenderer.material.color = highlightColor;
            }

            // Remove collider
            Collider collider = highlightIndicator.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }

            highlightIndicator.SetActive(false);
        }

        /// <summary>
        /// Add supported interaction type
        /// </summary>
        public void AddSupportedInteraction(InteractionType interactionType)
        {
            List<InteractionType> interactions = new List<InteractionType>(supportedInteractions);
            if (!interactions.Contains(interactionType))
            {
                interactions.Add(interactionType);
                supportedInteractions = interactions.ToArray();
            }
        }

        /// <summary>
        /// Remove supported interaction type
        /// </summary>
        public void RemoveSupportedInteraction(InteractionType interactionType)
        {
            List<InteractionType> interactions = new List<InteractionType>(supportedInteractions);
            interactions.Remove(interactionType);
            supportedInteractions = interactions.ToArray();
        }

        private void OnDrawGizmos()
        {
            // Draw interaction point
            Gizmos.color = Color.cyan;
            Vector3 point = GetInteractionPoint();
            Gizmos.DrawWireSphere(point, 0.1f);
            Gizmos.DrawLine(transform.position, point);

            // Draw interaction range
            Gizmos.color = isInteracting ? Color.green : Color.yellow;
            Gizmos.DrawWireSphere(point, interactionRange);
        }
    }

    /// <summary>
    /// Specific interactable for grabbable objects
    /// </summary>
    public class GrabbableObject : InteractableObject
    {
        [Header("Grab Settings")]
        [SerializeField] private bool snapToHand = true;
        [SerializeField] private Vector3 grabOffset = Vector3.zero;
        [SerializeField] private Quaternion grabRotation = Quaternion.identity;

        private Transform originalParent;
        private Vector3 originalPosition;
        private Quaternion originalRotation;
        private Rigidbody rb;

        protected override void Awake()
        {
            base.Awake();
            
            // Add grab interaction if not already supported
            AddSupportedInteraction(InteractionType.Grab);
            AddSupportedInteraction(InteractionType.Hold);
            
            rb = GetComponent<Rigidbody>();
        }

        public override async Task<bool> OnInteractionStart(InteractionType interactionType)
        {
            bool success = await base.OnInteractionStart(interactionType);

            if (success && (interactionType == InteractionType.Grab || interactionType == InteractionType.Hold))
            {
                // Store original state
                originalParent = transform.parent;
                originalPosition = transform.localPosition;
                originalRotation = transform.localRotation;

                // Disable physics while grabbed
                if (rb != null)
                {
                    rb.isKinematic = true;
                }
            }

            return success;
        }

        public override void OnInteractionEnd()
        {
            if (currentInteractionType == InteractionType.Grab || currentInteractionType == InteractionType.Hold)
            {
                // Restore original state
                if (originalParent != null)
                {
                    transform.SetParent(originalParent);
                }
                
                transform.localPosition = originalPosition;
                transform.localRotation = originalRotation;

                // Re-enable physics
                if (rb != null)
                {
                    rb.isKinematic = false;
                }
            }

            base.OnInteractionEnd();
        }
    }

    /// <summary>
    /// Specific interactable for usable objects (doors, switches, etc.)
    /// </summary>
    public class UsableObject : InteractableObject
    {
        [Header("Use Settings")]
        [SerializeField] private bool singleUse = false;
        [SerializeField] private float useDuration = 1f;
        [SerializeField] private bool hasBeenUsed = false;

        private float useStartTime;

        protected override void Awake()
        {
            base.Awake();
            AddSupportedInteraction(InteractionType.Use);
        }

        public override async Task<bool> OnInteractionStart(InteractionType interactionType)
        {
            if (interactionType == InteractionType.Use)
            {
                if (singleUse && hasBeenUsed)
                {
                    Debug.Log($"{objectId} has already been used");
                    return false;
                }

                bool success = await base.OnInteractionStart(interactionType);
                
                if (success)
                {
                    useStartTime = Time.time;
                    
                    if (useDuration > 0)
                    {
                        // Wait for use duration
                        await System.Threading.Tasks.Task.Delay((int)(useDuration * 1000));
                    }

                    hasBeenUsed = true;
                    OnObjectUsed();
                }

                return success;
            }

            return await base.OnInteractionStart(interactionType);
        }

        public override void OnInteractionUpdate(float deltaTime)
        {
            base.OnInteractionUpdate(deltaTime);

            if (currentInteractionType == InteractionType.Use)
            {
                float progress = (Time.time - useStartTime) / useDuration;
                OnUseProgress(progress);
            }
        }

        /// <summary>
        /// Called when object is used
        /// </summary>
        protected virtual void OnObjectUsed()
        {
            Debug.Log($"{objectId} used");
            // Override in derived classes
        }

        /// <summary>
        /// Called during use progress
        /// </summary>
        protected virtual void OnUseProgress(float progress)
        {
            // Override in derived classes
        }

        /// <summary>
        /// Reset single-use state
        /// </summary>
        public void ResetUse()
        {
            hasBeenUsed = false;
        }
    }
}