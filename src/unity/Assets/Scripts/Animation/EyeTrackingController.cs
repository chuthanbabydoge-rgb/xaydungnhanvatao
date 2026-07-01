using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Eye Tracking Controller - follows Single Responsibility Principle
    /// Manages eye movement, saccades, and gaze behavior
    /// </summary>
    public class EyeTrackingController : MonoBehaviour
    {
        [Header("Eye Components")]
        [SerializeField] private Transform leftEye;
        [SerializeField] private Transform rightEye;
        [SerializeField] private Transform headBone;

        [Header("Gaze Settings")]
        [SerializeField] private float gazeSpeed = 5f;
        [SerializeField] private float gazeSmoothness = 0.1f;
        [SerializeField] private float maxGazeAngle = 45f;
        [SerializeField] private bool enableIndependentEyeMovement = true;

        [Header("Saccade Settings")]
        [SerializeField] private float saccadeIntervalMin = 2f;
        [SerializeField] private float saccadeIntervalMax = 5f;
        [SerializeField] private float saccadeSpeed = 15f;
        [SerializeField] private float saccadeRange = 30f;

        [Header("Blink Integration")]
        [SerializeField] private bool coordinateBlinksWithSaccades = true;
        [SerializeField] private float blinkBeforeSaccadeChance = 0.3f;
        [SerializeField] private float blinkAfterSaccadeChance = 0.5f;

        [Header("Attention")]
        [SerializeField] private Transform gazeTarget;
        [SerializeField] private float attentionDuration = 3f;
        [SerializeField] private float attentionVariance = 1f;

        [Header("Procedural Behavior")]
        [SerializeField] private bool enableProceduralGaze = true;
        [SerializeField] private float idleGazeFrequency = 0.5f;
        [SerializeField] private float conversationGazeFrequency = 0.8f;

        private Vector3 currentGazeDirection;
        private Vector3 targetGazeDirection;
        private Vector3 leftEyeLocalPosition;
        private Vector3 rightEyeLocalPosition;
        private Quaternion leftEyeLocalRotation;
        private Quaternion rightEyeLocalRotation;
        private float lastSaccadeTime;
        private float nextSaccadeTime;
        private bool isPerformingSaccade;
        private Coroutine saccadeCoroutine;
        private Coroutine gazeCoroutine;

        public event Action<Vector3> OnGazeTargetChanged;
        public event Action OnSaccadeStarted;
        public event Action OnSaccadeCompleted;
        public event Action<Transform> OnAttentionFocusChanged;

        private void Start()
        {
            InitializeEyes();
            InitializeGaze();
            StartProceduralBehavior();
        }

        private void InitializeEyes()
        {
            if (leftEye != null)
            {
                leftEyeLocalPosition = leftEye.localPosition;
                leftEyeLocalRotation = leftEye.localRotation;
            }

            if (rightEye != null)
            {
                rightEyeLocalPosition = rightEye.localPosition;
                rightEyeLocalRotation = rightEye.localRotation;
            }

            if (headBone == null)
            {
                headBone = transform;
            }
        }

        private void InitializeGaze()
        {
            currentGazeDirection = headBone.forward;
            targetGazeDirection = headBone.forward;
            ScheduleNextSaccade();
        }

        private void StartProceduralBehavior()
        {
            if (enableProceduralGaze)
            {
                gazeCoroutine = StartCoroutine(ProceduralGazeCoroutine());
            }
        }

        private void Update()
        {
            UpdateGaze();
            CheckSaccadeTiming();
        }

        private void UpdateGaze()
        {
            if (gazeTarget != null)
            {
                // Track specific target
                Vector3 targetDirection = (gazeTarget.position - headBone.position).normalized;
                SetGazeDirection(targetDirection);
            }
            else if (!isPerformingSaccade)
            {
                // Smoothly interpolate current gaze
                currentGazeDirection = Vector3.Slerp(
                    currentGazeDirection,
                    targetGazeDirection,
                    Time.deltaTime * gazeSpeed
                );
            }

            ApplyGazeToEyes();
        }

        private void ApplyGazeToEyes()
        {
            // Calculate gaze rotation
            Quaternion gazeRotation = Quaternion.LookRotation(currentGazeDirection, headBone.up);

            // Clamp gaze angle
            Vector3 gazeEuler = gazeRotation.eulerAngles;
            gazeEuler.x = Mathf.Clamp(
                NormalizeAngle(gazeEuler.x),
                -maxGazeAngle,
                maxGazeAngle
            );
            gazeEuler.y = Mathf.Clamp(
                NormalizeAngle(gazeEuler.y),
                -maxGazeAngle,
                maxGazeAngle
            );
            gazeRotation = Quaternion.Euler(gazeEuler);

            // Apply to eyes
            if (leftEye != null)
            {
                if (enableIndependentEyeMovement)
                {
                    leftEye.localRotation = Quaternion.Slerp(
                        leftEyeLocalRotation,
                        gazeRotation,
                        gazeSmoothness
                    );
                }
                else
                {
                    leftEye.localRotation = gazeRotation;
                }
            }

            if (rightEye != null)
            {
                if (enableIndependentEyeMovement)
                {
                    rightEye.localRotation = Quaternion.Slerp(
                        rightEyeLocalRotation,
                        gazeRotation,
                        gazeSmoothness
                    );
                }
                else
                {
                    rightEye.localRotation = gazeRotation;
                }
            }
        }

        private float NormalizeAngle(float angle)
        {
            while (angle > 180f) angle -= 360f;
            while (angle < -180f) angle += 360f;
            return angle;
        }

        private void CheckSaccadeTiming()
        {
            if (Time.time >= nextSaccadeTime && !isPerformingSaccade && gazeTarget == null)
            {
                PerformSaccade();
            }
        }

        private void PerformSaccade()
        {
            if (saccadeCoroutine != null)
            {
                StopCoroutine(saccadeCoroutine);
            }

            saccadeCoroutine = StartCoroutine(SaccadeCoroutine());
        }

        private IEnumerator SaccadeCoroutine()
        {
            isPerformingSaccade = true;
            OnSaccadeStarted?.Invoke();

            // Optional blink before saccade
            if (coordinateBlinksWithSaccades && Random.value < blinkBeforeSaccadeChance)
            {
                yield return StartCoroutine(QuickBlink());
            }

            // Calculate random saccade target
            Vector3 saccadeDirection = GetRandomSaccadeDirection();
            targetGazeDirection = saccadeDirection;

            // Perform saccade movement
            float saccadeDuration = 0.1f;
            float elapsedTime = 0f;
            Vector3 startDirection = currentGazeDirection;

            while (elapsedTime < saccadeDuration)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / saccadeDuration;

                // Apply easing for natural saccade motion
                float easedT = SaccadeEasing(t);
                currentGazeDirection = Vector3.Slerp(startDirection, saccadeDirection, easedT);

                ApplyGazeToEyes();
                yield return null;
            }

            currentGazeDirection = saccadeDirection;

            // Optional blink after saccade
            if (coordinateBlinksWithSaccades && Random.value < blinkAfterSaccadeChance)
            {
                yield return StartCoroutine(QuickBlink());
            }

            isPerformingSaccade = false;
            lastSaccadeTime = Time.time;
            ScheduleNextSaccade();
            OnSaccadeCompleted?.Invoke();
        }

        private Vector3 GetRandomSaccadeDirection()
        {
            // Generate random direction within saccade range
            float horizontalAngle = Random.Range(-saccadeRange, saccadeRange);
            float verticalAngle = Random.Range(-saccadeRange * 0.5f, saccadeRange * 0.5f);

            Quaternion saccadeRotation = Quaternion.Euler(verticalAngle, horizontalAngle, 0f);
            return saccadeRotation * headBone.forward;
        }

        private float SaccadeEasing(float t)
        {
            // Sharp start and end for realistic saccade motion
            return t < 0.5f ? 2f * t * t : 1f - Mathf.Pow(-2f * t + 2f, 2f) / 2f;
        }

        private IEnumerator QuickBlink()
        {
            // Trigger quick blink through facial controller
            var facialController = GetComponent<FacialAnimationController>();
            if (facialController != null)
            {
                facialController.SetBlendShapeValue("EyesClosed", 1f);
                yield return new WaitForSeconds(0.05f);
                facialController.SetBlendShapeValue("EyesClosed", 0f);
            }
            else
            {
                yield return new WaitForSeconds(0.05f);
            }
        }

        private void ScheduleNextSaccade()
        {
            nextSaccadeTime = Time.time + Random.Range(saccadeIntervalMin, saccadeIntervalMax);
        }

        private IEnumerator ProceduralGazeCoroutine()
        {
            while (enableProceduralGaze)
            {
                if (gazeTarget == null && !isPerformingSaccade)
                {
                    // Randomly shift gaze during idle
                    if (Random.value < idleGazeFrequency * Time.deltaTime)
                    {
                        Vector3 randomGaze = GetRandomSaccadeDirection() * 0.5f;
                        targetGazeDirection = Vector3.Slerp(
                            currentGazeDirection,
                            randomGaze,
                            0.3f
                        );
                    }
                }

                yield return null;
            }
        }

        public void SetGazeTarget(Transform target)
        {
            gazeTarget = target;
            OnAttentionFocusChanged?.Invoke(target);
            OnGazeTargetChanged?.Invoke(target != null ? target.position : Vector3.zero);
        }

        public void SetGazePosition(Vector3 position)
        {
            gazeTarget = null;
            Vector3 direction = (position - headBone.position).normalized;
            targetGazeDirection = direction;
            OnGazeTargetChanged?.Invoke(position);
        }

        public void SetGazeDirection(Vector3 direction)
        {
            targetGazeDirection = direction.normalized;
        }

        public void ClearGazeTarget()
        {
            gazeTarget = null;
            targetGazeDirection = headBone.forward;
            OnAttentionFocusChanged?.Invoke(null);
        }

        public void SetGazeSpeed(float speed)
        {
            gazeSpeed = Mathf.Clamp(speed, 1f, 20f);
        }

        public void SetSaccadeParameters(float minInterval, float maxInterval, float range)
        {
            saccadeIntervalMin = minInterval;
            saccadeIntervalMax = maxInterval;
            saccadeRange = range;
        }

        public void SetProceduralGazeEnabled(bool enabled)
        {
            enableProceduralGaze = enabled;

            if (enabled && gazeCoroutine == null)
            {
                gazeCoroutine = StartCoroutine(ProceduralGazeCoroutine());
            }
            else if (!enabled && gazeCoroutine != null)
            {
                StopCoroutine(gazeCoroutine);
                gazeCoroutine = null;
            }
        }

        public Vector3 GetCurrentGazeDirection()
        {
            return currentGazeDirection;
        }

        public bool IsLookingAtTarget()
        {
            if (gazeTarget == null) return false;

            Vector3 toTarget = (gazeTarget.position - headBone.position).normalized;
            float angle = Vector3.Angle(currentGazeDirection, toTarget);
            return angle < 10f;
        }

        public void ForceSaccade()
        {
            if (!isPerformingSaccade)
            {
                PerformSaccade();
            }
        }
    }
}
