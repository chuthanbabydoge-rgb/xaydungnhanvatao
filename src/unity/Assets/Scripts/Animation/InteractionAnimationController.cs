using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Interaction Animation Controller - follows Single Responsibility Principle
    /// Manages procedural animations for object interactions and environmental responses
    /// </summary>
    public class InteractionAnimationController : MonoBehaviour
    {
        [Header("Interaction Components")]
        [SerializeField] private Transform leftHand;
        [SerializeField] private Transform rightHand;
        [SerializeField] private Transform headBone;
        [SerializeField] private Transform spineBone;

        [Header("Interaction Settings")]
        [SerializeField] private float interactionSpeed = 2f;
        [SerializeField] private float reachDistance = 1.5f;
        [SerializeField] private float grabDistance = 0.3f;
        [SerializeField] private bool enableProceduralReach = true;

        [Header("Animation States")]
        [SerializeField] private bool isInteracting;
        [SerializeField] private Transform currentInteractionTarget;
        [SerializeField] private InteractionType currentInteractionType;

        [Header("Reach Animation")]
        [SerializeField] private float reachSmoothness = 0.3f;
        [SerializeField] private float reach anticipation = 0.2f;
        [SerializeField] private float reachFollowThrough = 0.3f;

        [Header("Grab Animation")]
        [SerializeField] private float grabDuration = 0.5f;
        [SerializeField] private float grabStrength = 1f;
        [SerializeField] private bool enableFingerCurl = true;

        [Header("Release Animation")]
        [SerializeField] private float releaseDuration = 0.3f;
        [SerializeField] private float releaseSmoothness = 0.5f;

        [Header("Procedural Adjustments")]
        [SerializeField] private bool enableBodyLean = true;
        [SerializeField] private float bodyLeanAmount = 15f;
        [SerializeField] private bool enableHeadTracking = true;
        [SerializeField] private float headTrackingWeight = 0.8f;

        [Header("Integration")]
        [SerializeField] private IKController ikController;
        [SerializeField] private GestureController gestureController;
        [SerializeField] private ProceduralAnimationController proceduralController;

        private Dictionary<string, Vector3> initialPositions = new Dictionary<string, Vector3>();
        private Dictionary<string, Quaternion> initialRotations = new Dictionary<string, Quaternion>();
        private Coroutine interactionCoroutine;
        private Vector3 targetHandPosition;
        private Quaternion targetHandRotation;
        private bool isLeftHanded;

        public event Action<Transform, InteractionType> OnInteractionStarted;
        public event Action<Transform, InteractionType> OnInteractionCompleted;
        public event Action<Transform> OnObjectGrabbed;
        public event Action<Transform> OnObjectReleased;

        public enum InteractionType
        {
            Grab,
            Touch,
            Point,
            Push,
            Pull,
            Hold,
            Use,
            Examine,
            Give,
            Receive
        }

        private void Start()
        {
            InitializeBones();
            FindControllers();
        }

        private void InitializeBones()
        {
            // Store initial positions and rotations
            if (leftHand != null)
            {
                initialPositions["LeftHand"] = leftHand.localPosition;
                initialRotations["LeftHand"] = leftHand.localRotation;
            }

            if (rightHand != null)
            {
                initialPositions["RightHand"] = rightHand.localPosition;
                initialRotations["RightHand"] = rightHand.localRotation;
            }

            if (headBone != null)
            {
                initialRotations["Head"] = headBone.localRotation;
            }

            if (spineBone != null)
            {
                initialRotations["Spine"] = spineBone.localRotation;
            }
        }

        private void FindControllers()
        {
            if (ikController == null)
            {
                ikController = GetComponent<IKController>();
            }

            if (gestureController == null)
            {
                gestureController = GetComponent<GestureController>();
            }

            if (proceduralController == null)
            {
                proceduralController = GetComponent<ProceduralAnimationController>();
            }
        }

        public void StartInteraction(Transform target, InteractionType type, bool useLeftHand = false)
        {
            if (isInteracting)
            {
                CancelCurrentInteraction();
            }

            currentInteractionTarget = target;
            currentInteractionType = type;
            isLeftHanded = useLeftHand;
            isInteracting = true;

            OnInteractionStarted?.Invoke(target, type);

            if (interactionCoroutine != null)
            {
                StopCoroutine(interactionCoroutine);
            }

            interactionCoroutine = StartCoroutine(InteractionCoroutine(target, type, useLeftHand));
        }

        private IEnumerator InteractionCoroutine(Transform target, InteractionType type, bool useLeftHand)
        {
            // Calculate target hand position
            Transform activeHand = useLeftHand ? leftHand : rightHand;
            if (activeHand == null) yield break;

            Vector3 targetPosition = target.position;
            float distance = Vector3.Distance(activeHand.position, targetPosition);

            // Anticipation phase
            yield return StartCoroutine(AnticipationCoroutine(activeHand, targetPosition, type));

            // Reach phase
            yield return StartCoroutine(ReachCoroutine(activeHand, targetPosition, type));

            // Contact phase
            yield return StartCoroutine(ContactCoroutine(activeHand, target, type));

            // Follow-through phase
            yield return StartCoroutine(FollowThroughCoroutine(activeHand, type));

            // Reset phase
            yield return StartCoroutine(ResetCoroutine(activeHand));

            isInteracting = false;
            currentInteractionTarget = null;
            OnInteractionCompleted?.Invoke(target, type);
        }

        private IEnumerator AnticipationCoroutine(Transform hand, Vector3 targetPosition, InteractionType type)
        {
            float anticipationTime = reachAnticipation;
            float elapsedTime = 0f;

            Vector3 startPosition = hand.position;
            Vector3 anticipationOffset = (targetPosition - startPosition).normalized * 0.1f;
            Vector3 anticipationPosition = startPosition + anticipationOffset;

            while (elapsedTime < anticipationTime)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / anticipationTime;
                float easedT = AnticipationEasing(t);

                hand.position = Vector3.Lerp(startPosition, anticipationPosition, easedT);

                // Apply body lean
                if (enableBodyLean && spineBone != null)
                {
                    float leanAmount = bodyLeanAmount * easedT;
                    Vector3 leanDirection = (targetPosition - transform.position).normalized;
                    Quaternion leanRotation = Quaternion.FromToRotation(Vector3.up, leanDirection + Vector3.up * 0.5f);
                    spineBone.localRotation = Quaternion.Slerp(
                        initialRotations["Spine"],
                        initialRotations["Spine"] * leanRotation,
                        easedT * 0.3f
                    );
                }

                // Apply head tracking
                if (enableHeadTracking && headBone != null)
                {
                    Vector3 lookDirection = (targetPosition - headBone.position).normalized;
                    Quaternion lookRotation = Quaternion.LookRotation(lookDirection);
                    headBone.localRotation = Quaternion.Slerp(
                        headBone.localRotation,
                        lookRotation,
                        Time.deltaTime * headTrackingWeight
                    );
                }

                yield return null;
            }
        }

        private IEnumerator ReachCoroutine(Transform hand, Vector3 targetPosition, InteractionType type)
        {
            float reachTime = CalculateReachDuration(hand.position, targetPosition);
            float elapsedTime = 0f;

            Vector3 startPosition = hand.position;
            Quaternion startRotation = hand.rotation;

            // Calculate target rotation based on interaction type
            Quaternion targetRotation = CalculateTargetRotation(targetPosition, type);

            while (elapsedTime < reachTime)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / reachTime;
                float easedT = ReachEasing(t);

                hand.position = Vector3.Lerp(startPosition, targetPosition, easedT);
                hand.rotation = Quaternion.Slerp(startRotation, targetRotation, easedT);

                // Update IK target
                if (ikController != null)
                {
                    if (isLeftHanded)
                    {
                        ikController.SetLeftHandTarget(hand);
                    }
                    else
                    {
                        ikController.SetRightHandTarget(hand);
                    }
                }

                yield return null;
            }
        }

        private IEnumerator ContactCoroutine(Transform hand, Transform target, InteractionType type)
        {
            float contactDuration = CalculateContactDuration(type);
            float elapsedTime = 0f;

            while (elapsedTime < contactDuration)
            {
                elapsedTime += Time.deltaTime;

                // Apply contact-specific animations
                switch (type)
                {
                    case InteractionType.Grab:
                        yield return StartCoroutine(GrabCoroutine(hand, target));
                        break;
                    case InteractionType.Touch:
                        yield return StartCoroutine(TouchCoroutine(hand, target));
                        break;
                    case InteractionType.Push:
                        yield return StartCoroutine(PushCoroutine(hand, target));
                        break;
                    case InteractionType.Pull:
                        yield return StartCoroutine(PullCoroutine(hand, target));
                        break;
                    case InteractionType.Hold:
                        yield return StartCoroutine(HoldCoroutine(hand, target));
                        break;
                    default:
                        yield return null;
                        break;
                }

                yield return null;
            }
        }

        private IEnumerator GrabCoroutine(Transform hand, Transform target)
        {
            float grabTime = grabDuration;
            float elapsedTime = 0f;

            Vector3 startPosition = hand.position;
            Vector3 grabPosition = target.position;

            while (elapsedTime < grabTime)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / grabTime;
                float easedT = GrabEasing(t);

                hand.position = Vector3.Lerp(startPosition, grabPosition, easedT);

                // Apply finger curl
                if (enableFingerCurl)
                {
                    float fingerCurl = easedT * grabStrength;
                    // In a real implementation, this would animate individual finger bones
                    hand.localRotation *= Quaternion.Euler(fingerCurl * 30f, 0, 0);
                }

                yield return null;
            }

            OnObjectGrabbed?.Invoke(target);
        }

        private IEnumerator TouchCoroutine(Transform hand, Transform target)
        {
            // Brief touch animation
            float touchDuration = 0.2f;
            float elapsedTime = 0f;

            Vector3 touchPosition = target.position;
            Vector3 retreatPosition = hand.position;

            while (elapsedTime < touchDuration)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / touchDuration;

                if (t < 0.5f)
                {
                    // Move to touch
                    hand.position = Vector3.Lerp(retreatPosition, touchPosition, t * 2f);
                }
                else
                {
                    // Retreat
                    hand.position = Vector3.Lerp(touchPosition, retreatPosition, (t - 0.5f) * 2f);
                }

                yield return null;
            }
        }

        private IEnumerator PushCoroutine(Transform hand, Transform target)
        {
            float pushDuration = 0.5f;
            float elapsedTime = 0f;

            Vector3 startPosition = hand.position;
            Vector3 pushDirection = (target.position - hand.position).normalized;
            Vector3 pushPosition = target.position + pushDirection * 0.2f;

            while (elapsedTime < pushDuration)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / pushDuration;
                float easedT = PushEasing(t);

                hand.position = Vector3.Lerp(startPosition, pushPosition, easedT);

                yield return null;
            }
        }

        private IEnumerator PullCoroutine(Transform hand, Transform target)
        {
            float pullDuration = 0.5f;
            float elapsedTime = 0f;

            Vector3 startPosition = hand.position;
            Vector3 pullPosition = transform.position + (target.position - transform.position).normalized * 0.5f;

            while (elapsedTime < pullDuration)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / pullDuration;
                float easedT = PullEasing(t);

                hand.position = Vector3.Lerp(startPosition, pullPosition, easedT);

                yield return null;
            }
        }

        private IEnumerator HoldCoroutine(Transform hand, Transform target)
        {
            // Hold animation - maintain position
            float holdDuration = 1f;
            float elapsedTime = 0f;

            while (elapsedTime < holdDuration)
            {
                elapsedTime += Time.deltaTime;
                hand.position = target.position;

                // Add subtle holding motion
                float holdMotion = Mathf.Sin(elapsedTime * 2f) * 0.01f;
                hand.position += Vector3.up * holdMotion;

                yield return null;
            }
        }

        private IEnumerator FollowThroughCoroutine(Transform hand, InteractionType type)
        {
            float followThroughTime = reachFollowThrough;
            float elapsedTime = 0f;

            Vector3 startPosition = hand.position;
            Vector3 followThroughOffset = Vector3.forward * 0.1f;
            Vector3 followThroughPosition = startPosition + followThroughOffset;

            while (elapsedTime < followThroughTime)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / followThroughTime;
                float easedT = FollowThroughEasing(t);

                hand.position = Vector3.Lerp(startPosition, followThroughPosition, easedT);

                yield return null;
            }
        }

        private IEnumerator ResetCoroutine(Transform hand)
        {
            float resetTime = releaseDuration;
            float elapsedTime = 0f;

            Vector3 startPosition = hand.position;
            Quaternion startRotation = hand.rotation;

            string handName = isLeftHanded ? "LeftHand" : "RightHand";
            Vector3 targetPosition = initialPositions.ContainsKey(handName) ? 
                transform.TransformPoint(initialPositions[handName]) : hand.position;
            Quaternion targetRotation = initialRotations.ContainsKey(handName) ? 
                initialRotations[handName] : hand.rotation;

            while (elapsedTime < resetTime)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / resetTime;
                float easedT = ResetEasing(t);

                hand.position = Vector3.Lerp(startPosition, targetPosition, easedT);
                hand.rotation = Quaternion.Slerp(startRotation, targetRotation, easedT);

                // Clear IK targets
                if (ikController != null)
                {
                    if (isLeftHanded)
                    {
                        ikController.SetLeftHandTarget(null);
                    }
                    else
                    {
                        ikController.SetRightHandTarget(null);
                    }
                }

                yield return null;
            }

            // Reset body and head
            if (enableBodyLean && spineBone != null)
            {
                spineBone.localRotation = initialRotations["Spine"];
            }

            if (enableHeadTracking && headBone != null)
            {
                headBone.localRotation = initialRotations["Head"];
            }

            OnObjectReleased?.Invoke(currentInteractionTarget);
        }

        private float CalculateReachDuration(Vector3 start, Vector3 end)
        {
            float distance = Vector3.Distance(start, end);
            return Mathf.Clamp(distance / interactionSpeed, 0.2f, 1f);
        }

        private float CalculateContactDuration(InteractionType type)
        {
            switch (type)
            {
                case InteractionType.Grab:
                    return grabDuration;
                case InteractionType.Touch:
                    return 0.2f;
                case InteractionType.Push:
                    return 0.5f;
                case InteractionType.Pull:
                    return 0.5f;
                case InteractionType.Hold:
                    return 1f;
                default:
                    return 0.3f;
            }
        }

        private Quaternion CalculateTargetRotation(Vector3 targetPosition, InteractionType type)
        {
            Vector3 toTarget = (targetPosition - transform.position).normalized;

            switch (type)
            {
                case InteractionType.Grab:
                    return Quaternion.LookRotation(toTarget, Vector3.up) * Quaternion.Euler(-90, 0, 0);
                case InteractionType.Point:
                    return Quaternion.LookRotation(toTarget, Vector3.up) * Quaternion.Euler(-90, 0, 0);
                case InteractionType.Push:
                    return Quaternion.LookRotation(toTarget, Vector3.up) * Quaternion.Euler(-90, 0, 0);
                case InteractionType.Pull:
                    return Quaternion.LookRotation(-toTarget, Vector3.up) * Quaternion.Euler(-90, 0, 0);
                default:
                    return Quaternion.LookRotation(toTarget, Vector3.up);
            }
        }

        private float AnticipationEasing(float t)
        {
            return t * t;
        }

        private float ReachEasing(float t)
        {
            return t < 0.5f ? 2f * t * t : 1f - Mathf.Pow(-2f * t + 2f, 2f) / 2f;
        }

        private float GrabEasing(float t)
        {
            return t < 0.3f ? t / 0.3f : 1f;
        }

        private float PushEasing(float t)
        {
            return 1f - Mathf.Pow(1f - t, 3);
        }

        private float PullEasing(float t)
        {
            return t < 0.5f ? 2f * t * t : 1f - Mathf.Pow(-2f * t + 2f, 2f) / 2f;
        }

        private float FollowThroughEasing(float t)
        {
            return 1f - t;
        }

        private float ResetEasing(float t)
        {
            return t < 0.5f ? 2f * t * t : 1f - Mathf.Pow(-2f * t + 2f, 2f) / 2f;
        }

        public void CancelCurrentInteraction()
        {
            if (interactionCoroutine != null)
            {
                StopCoroutine(interactionCoroutine);
                interactionCoroutine = null;
            }

            isInteracting = false;
            currentInteractionTarget = null;

            // Reset hand positions
            if (leftHand != null && initialPositions.ContainsKey("LeftHand"))
            {
                leftHand.localPosition = initialPositions["LeftHand"];
                leftHand.localRotation = initialRotations["LeftHand"];
            }

            if (rightHand != null && initialPositions.ContainsKey("RightHand"))
            {
                rightHand.localPosition = initialPositions["RightHand"];
                rightHand.localRotation = initialRotations["RightHand"];
            }

            // Clear IK targets
            if (ikController != null)
            {
                ikController.ClearIKTargets();
            }
        }

        public void SetInteractionSpeed(float speed)
        {
            interactionSpeed = Mathf.Clamp(speed, 0.5f, 5f);
        }

        public void SetReachDistance(float distance)
        {
            reachDistance = Mathf.Clamp(distance, 0.5f, 3f);
        }

        public void SetGrabStrength(float strength)
        {
            grabStrength = Mathf.Clamp01(strength);
        }

        public bool IsInteracting()
        {
            return isInteracting;
        }

        public Transform GetCurrentInteractionTarget()
        {
            return currentInteractionTarget;
        }

        public InteractionType GetCurrentInteractionType()
        {
            return currentInteractionType;
        }
    }
}
