using UnityEngine;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Procedural Animation Controller - follows Single Responsibility Principle
    /// Handles procedural animations for dynamic character movements
    /// </summary>
    public class ProceduralAnimationController : MonoBehaviour
    {
        [Header("Breathing Animation")]
        [SerializeField] private bool enableBreathing = true;
        [SerializeField] private float breathingSpeed = 1f;
        [SerializeField] private float breathingAmplitude = 0.02f;
        [SerializeField] private Transform chestBone;

        [Header("Idle Animation")]
        [SerializeField] private bool enableIdleAnimation = true;
        [SerializeField] private float idleAnimationSpeed = 0.5f;
        [SerializeField] private float idleAmplitude = 0.01f;
        [SerializeField] private List<Transform> idleBones = new List<Transform>();

        [Header("Balance")]
        [SerializeField] private bool enableBalance = true;
        [SerializeField] private float balanceStrength = 10f;
        [SerializeField] private float balanceDamping = 0.5f;

        [Header("Looking Around")]
        [SerializeField] private bool enableLookingAround = true;
        [SerializeField] private float lookAroundSpeed = 0.3f;
        [SerializeField] private float lookAroundRange = 30f;
        [SerializeField] private Transform headBone;

        private Vector3 initialChestPosition;
        private List<Vector3> initialBonePositions = new List<Vector3>();
        private Quaternion initialHeadRotation;
        private float randomLookOffset;
        private float timeOffset;

        private void Start()
        {
            InitializeBones();
            randomLookOffset = Random.Range(0f, 100f);
            timeOffset = Time.time;
        }

        private void InitializeBones()
        {
            // Store initial positions for procedural animations
            if (chestBone != null)
            {
                initialChestPosition = chestBone.localPosition;
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
        }

        private void UpdateBreathing(float time)
        {
            if (chestBone == null) return;

            // Sinusoidal breathing motion
            float breathingOffset = Mathf.Sin(time * breathingSpeed) * breathingAmplitude;
            chestBone.localPosition = initialChestPosition + Vector3.up * breathingOffset;
        }

        private void UpdateIdleAnimation(float time)
        {
            for (int i = 0; i < idleBones.Count; i++)
            {
                if (idleBones[i] == null || i >= initialBonePositions.Count) continue;

                // Per-bone random idle motion
                float boneOffset = Mathf.Sin(time * idleAnimationSpeed + i) * idleAmplitude;
                idleBones[i].localPosition = initialBonePositions[i] + 
                    Vector3.up * boneOffset;
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

            // Subtle random head movement
            float lookX = Mathf.PerlinNoise(time * lookAroundSpeed + randomLookOffset, 0f) * 2f - 1f;
            float lookY = Mathf.PerlinNoise(0f, time * lookAroundSpeed + randomLookOffset) * 2f - 1f;

            Vector3 lookEuler = new Vector3(
                lookY * lookAroundRange,
                lookX * lookAroundRange,
                0f
            );

            Quaternion targetRotation = initialHeadRotation * Quaternion.Euler(lookEuler);
            headBone.localRotation = Quaternion.Slerp(
                headBone.localRotation,
                targetRotation,
                Time.deltaTime * lookAroundSpeed
            );
        }

        // Public methods for external control
        public void SetBreathingEnabled(bool enabled)
        {
            enableBreathing = enabled;
        }

        public void SetBreathingParameters(float speed, float amplitude)
        {
            breathingSpeed = speed;
            breathingAmplitude = amplitude;
        }

        public void SetIdleAnimationEnabled(bool enabled)
        {
            enableIdleAnimation = enabled;
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
    }
}
