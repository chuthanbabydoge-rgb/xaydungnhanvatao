using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Procedural Animation Controller - follows Single Responsibility Principle
    /// Handles procedural animations for dynamic character movements
    /// Enhanced with advanced breathing, idle variations, body posture, and emotional integration
    /// </summary>
    public class ProceduralAnimationController : MonoBehaviour
    {
        [Header("Breathing Animation")]
        [SerializeField] private bool enableBreathing = true;
        [SerializeField] private float breathingSpeed = 1f;
        [SerializeField] private float breathingAmplitude = 0.02f;
        [SerializeField] private bool enableVariableBreathing = true;
        [SerializeField] private float breathingVariability = 0.2f;
        [SerializeField] private Transform chestBone;
        [SerializeField] private Transform spineBone;

        [Header("Idle Animation")]
        [SerializeField] private bool enableIdleAnimation = true;
        [SerializeField] private float idleAnimationSpeed = 0.5f;
        [SerializeField] private float idleAmplitude = 0.01f;
        [SerializeField] private bool enableComplexIdle = true;
        [SerializeField] private List<Transform> idleBones = new List<Transform>();

        [Header("Balance")]
        [SerializeField] private bool enableBalance = true;
        [SerializeField] private float balanceStrength = 10f;
        [SerializeField] private float balanceDamping = 0.5f;

        [Header("Head Look")]
        [SerializeField] private bool enableLookingAround = true;
        [SerializeField] private float lookAroundSpeed = 0.3f;
        [SerializeField] private float lookAroundRange = 30f;
        [SerializeField] private Transform headBone;

        [Header("Body Posture")]
        [SerializeField] private bool enablePostureAdjustment = true;
        [SerializeField] private float postureAdjustmentSpeed = 1f;
        [SerializeField] private float defaultPostureForwardLean = 0f;
        [SerializeField] private float defaultPostureSideLean = 0f;

        [Header("Weight Shift")]
        [SerializeField] private bool enableWeightShift = true;
        [SerializeField] private float weightShiftInterval = 3f;
        [SerializeField] private float weightShiftAmount = 0.05f;
        [SerializeField] private Transform hipsBone;

        [Header("Emotional Integration")]
        [SerializeField] private bool enableEmotionalBreathing = true;
        [SerializeField] private bool enableEmotionalPosture = true;

        private Vector3 initialChestPosition;
        private Vector3 initialSpinePosition;
        private List<Vector3> initialBonePositions = new List<Vector3>();
        private Quaternion initialHeadRotation;
        private Quaternion initialSpineRotation;
        private float randomLookOffset;
        private float timeOffset;
        private float lastWeightShiftTime;
        private float weightShiftDirection;
        private float breathingPhaseOffset;

        public event Action OnBreathCycle;
        public event Action OnWeightShift;

        private void Start()
        {
            InitializeBones();
            randomLookOffset = Random.Range(0f, 100f);
            timeOffset = Time.time;
            breathingPhaseOffset = Random.Range(0f, Mathf.PI * 2f);
            weightShiftDirection = Random.value > 0.5f ? 1f : -1f;
        }

        private void InitializeBones()
        {
            // Store initial positions for procedural animations
            if (chestBone != null)
            {
                initialChestPosition = chestBone.localPosition;
            }

            if (spineBone != null)
            {
                initialSpinePosition = spineBone.localPosition;
                initialSpineRotation = spineBone.localRotation;
            }

            foreach (Transform bone in idleBones)
            {
                if (bone != null)
                {
                    initialBonePositions.Add(bone.localPosition);
                }
            }

            if (headBone != null)
            {
                initialHeadRotation = headBone.localRotation;
            }
        }

        private void Update()
        {
            float time = Time.time - timeOffset;

            if (enableBreathing)
            {
                UpdateBreathing(time);
            }

            if (enableIdleAnimation)
            {
                UpdateIdleAnimation(time);
            }

            if (enableBalance)
            {
                UpdateBalance();
            }

            if (enableLookingAround)
            {
                UpdateLookingAround(time);
            }

            if (enablePostureAdjustment)
            {
                UpdatePosture();
            }

            if (enableWeightShift)
            {
                UpdateWeightShift(time);
            }
        }

        private void UpdateBreathing(float time)
        {
            if (chestBone == null) return;

            // Enhanced breathing with variability
            float effectiveSpeed = breathingSpeed;
            float effectiveAmplitude = breathingAmplitude;

            if (enableVariableBreathing)
            {
                // Add natural variability to breathing
                float variability = Mathf.PerlinNoise(time * 0.5f, breathingPhaseOffset) * breathingVariability;
                effectiveSpeed *= (1f + variability);
                effectiveAmplitude *= (1f + variability * 0.5f);
            }

            // Sinusoidal breathing motion with chest expansion
            float breathingPhase = time * effectiveSpeed + breathingPhaseOffset;
            float breathingOffset = Mathf.Sin(breathingPhase) * effectiveAmplitude;

            // Apply to chest
            chestBone.localPosition = initialChestPosition + Vector3.up * breathingOffset;

            // Apply subtle spine movement for natural breathing
            if (spineBone != null)
            {
                float spineOffset = Mathf.Sin(breathingPhase) * effectiveAmplitude * 0.5f;
                spineBone.localPosition = initialSpinePosition + Vector3.up * spineOffset;
            }

            // Trigger breath cycle event
            if (Mathf.Sin(breathingPhase) > 0.95f && Mathf.Sin(breathingPhase - Time.deltaTime * effectiveSpeed) <= 0.95f)
            {
                OnBreathCycle?.Invoke();
            }
        }

        private void UpdateIdleAnimation(float time)
        {
            for (int i = 0; i < idleBones.Count; i++)
            {
                if (idleBones[i] == null || i >= initialBonePositions.Count) continue;

                Vector3 idleOffset = Vector3.zero;

                if (enableComplexIdle)
                {
                    // Complex idle with multiple frequency components
                    float primaryOffset = Mathf.Sin(time * idleAnimationSpeed + i) * idleAmplitude;
                    float secondaryOffset = Mathf.Sin(time * idleAnimationSpeed * 2.3f + i * 1.5f) * idleAmplitude * 0.5f;
                    float tertiaryOffset = Mathf.PerlinNoise(time * idleAnimationSpeed + i, i * 0.5f) * idleAmplitude * 0.3f;

                    idleOffset = Vector3.up * (primaryOffset + secondaryOffset + tertiaryOffset);

                    // Add subtle horizontal movement
                    idleOffset.x += Mathf.Sin(time * idleAnimationSpeed * 0.7f + i) * idleAmplitude * 0.3f;
                }
                else
                {
                    // Simple idle motion
                    float boneOffset = Mathf.Sin(time * idleAnimationSpeed + i) * idleAmplitude;
                    idleOffset = Vector3.up * boneOffset;
                }

                idleBones[i].localPosition = initialBonePositions[i] + idleOffset;
            }
        }

        private void UpdateBalance()
        {
            if (!enableBalance) return;

            // Apply subtle balance adjustments based on character velocity
            Vector3 velocity = GetComponent<Rigidbody>()?.velocity ?? Vector3.zero;
            Vector3 balanceTarget = -velocity.normalized * balanceStrength;

            // Apply balance with damping
            Quaternion targetRotation = Quaternion.Euler(balanceTarget);
            transform.rotation = Quaternion.Slerp(
                transform.rotation,
                targetRotation,
                Time.deltaTime * balanceDamping
            );
        }

        private void UpdateLookingAround(float time)
        {
            if (headBone == null) return;

            // Enhanced procedural head movement with more natural patterns
            float lookX = Mathf.PerlinNoise(time * lookAroundSpeed + randomLookOffset, 0f) * 2f - 1f;
            float lookY = Mathf.PerlinNoise(0f, time * lookAroundSpeed + randomLookOffset) * 2f - 1f;

            // Add subtle head tilt
            float lookZ = Mathf.PerlinNoise(time * lookAroundSpeed * 0.5f + randomLookOffset, time * lookAroundSpeed * 0.5f) * 2f - 1f;

            Vector3 lookEuler = new Vector3(
                lookY * lookAroundRange,
                lookX * lookAroundRange,
                lookZ * (lookAroundRange * 0.3f)
            );

            Quaternion targetRotation = initialHeadRotation * Quaternion.Euler(lookEuler);
            headBone.localRotation = Quaternion.Slerp(
                headBone.localRotation,
                targetRotation,
                Time.deltaTime * lookAroundSpeed
            );
        }

        private void UpdatePosture()
        {
            if (spineBone == null) return;

            // Apply default posture adjustments
            Vector3 postureEuler = new Vector3(
                defaultPostureForwardLean,
                defaultPostureSideLean,
                0f
            );

            Quaternion targetPosture = initialSpineRotation * Quaternion.Euler(postureEuler);
            spineBone.localRotation = Quaternion.Slerp(
                spineBone.localRotation,
                targetPosture,
                Time.deltaTime * postureAdjustmentSpeed
            );
        }

        private void UpdateWeightShift(float time)
        {
            if (hipsBone == null || !enableWeightShift) return;

            // Periodic weight shifting between legs
            if (time - lastWeightShiftTime > weightShiftInterval)
            {
                weightShiftDirection *= -1f;
                lastWeightShiftTime = time;
                OnWeightShift?.Invoke();
            }

            // Smooth weight shift interpolation
            float shiftProgress = (time - lastWeightShiftTime) / weightShiftInterval;
            float currentShift = Mathf.Lerp(0f, weightShiftAmount * weightShiftDirection, shiftProgress);

            hipsBone.localPosition = hipsBone.localPosition + Vector3.right * currentShift * Time.deltaTime;
        }

        // Public methods for external control
        public void SetBreathingEnabled(bool enabled)
        {
            enableBreathing = enabled;
        }

        public void SetBreathingParameters(float speed, float amplitude)
        {
            breathingSpeed = Mathf.Clamp(speed, 0.5f, 3f);
            breathingAmplitude = Mathf.Clamp(amplitude, 0.005f, 0.1f);
        }

        public void SetVariableBreathingEnabled(bool enabled)
        {
            enableVariableBreathing = enabled;
        }

        public void SetBreathingVariability(float variability)
        {
            breathingVariability = Mathf.Clamp01(variability);
        }

        public void SetIdleAnimationEnabled(bool enabled)
        {
            enableIdleAnimation = enabled;
        }

        public void SetComplexIdleEnabled(bool enabled)
        {
            enableComplexIdle = enabled;
        }

        public void SetLookingAroundEnabled(bool enabled)
        {
            enableLookingAround = enabled;
        }

        public void SetLookTarget(Transform target)
        {
            if (headBone != null && target != null)
            {
                Vector3 lookDirection = (target.position - headBone.position).normalized;
                Quaternion targetRotation = Quaternion.LookRotation(lookDirection);
                headBone.rotation = Quaternion.Slerp(
                    headBone.rotation,
                    targetRotation,
                    Time.deltaTime * lookAroundSpeed
                );
            }
        }

        public void SetPostureAdjustments(float forwardLean, float sideLean)
        {
            defaultPostureForwardLean = Mathf.Clamp(forwardLean, -20f, 20f);
            defaultPostureSideLean = Mathf.Clamp(sideLean, -15f, 15f);
        }

        public void SetWeightShiftParameters(float interval, float amount)
        {
            weightShiftInterval = Mathf.Clamp(interval, 1f, 10f);
            weightShiftAmount = Mathf.Clamp(amount, 0.01f, 0.2f);
        }

        public void SetEmotionalBreathingParameters(string emotion, float intensity)
        {
            if (!enableEmotionalBreathing) return;

            switch (emotion.ToLower())
            {
                case "anger":
                case "fear":
                    SetBreathingParameters(1.8f, 0.03f * intensity);
                    break;
                case "sadness":
                    SetBreathingParameters(0.7f, 0.015f * intensity);
                    break;
                case "calm":
                    SetBreathingParameters(0.6f, 0.012f * intensity);
                    break;
                case "excitement":
                    SetBreathingParameters(1.4f, 0.025f * intensity);
                    break;
                default:
                    SetBreathingParameters(1f, 0.02f);
                    break;
            }
        }

        public void SetEmotionalPosture(string emotion, float intensity)
        {
            if (!enableEmotionalPosture) return;

            switch (emotion.ToLower())
            {
                case "sadness":
                    SetPostureAdjustments(5f * intensity, 0f);
                    break;
                case "anger":
                    SetPostureAdjustments(-3f * intensity, 0f);
                    break;
                case "fear":
                    SetPostureAdjustments(-2f * intensity, 0f);
                    break;
                case "confidence":
                    SetPostureAdjustments(-2f * intensity, 0f);
                    break;
                case "submission":
                    SetPostureAdjustments(8f * intensity, 0f);
                    break;
                default:
                    SetPostureAdjustments(0f, 0f);
                    break;
            }
        }

        public void AddIdleBone(Transform bone)
        {
            if (bone != null && !idleBones.Contains(bone))
            {
                idleBones.Add(bone);
                initialBonePositions.Add(bone.localPosition);
            }
        }

        public void RemoveIdleBone(Transform bone)
        {
            int index = idleBones.IndexOf(bone);
            if (index >= 0)
            {
                idleBones.RemoveAt(index);
                initialBonePositions.RemoveAt(index);
            }
        }

        public void TriggerBreathHold(float duration)
        {
            StartCoroutine(BreathHoldCoroutine(duration));
        }

        private IEnumerator BreathHoldCoroutine(float duration)
        {
            bool wasEnabled = enableBreathing;
            enableBreathing = false;

            yield return new WaitForSeconds(duration);

            enableBreathing = wasEnabled;
        }

        public void TriggerSigh()
        {
            StartCoroutine(SighCoroutine());
        }

        private IEnumerator SighCoroutine()
        {
            float originalSpeed = breathingSpeed;
            float originalAmplitude = breathingAmplitude;

            // Deep breath in
            breathingSpeed = 0.5f;
            breathingAmplitude = 0.05f;

            yield return new WaitForSeconds(1f);

            // Slow breath out
            breathingSpeed = 0.3f;
            breathingAmplitude = 0.04f;

            yield return new WaitForSeconds(1.5f);

            // Return to normal
            breathingSpeed = originalSpeed;
            breathingAmplitude = originalAmplitude;
        }
    }
}
