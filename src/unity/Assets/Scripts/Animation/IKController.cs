using UnityEngine;
using System;

namespace AICompanion.Animation
{
    /// <summary>
    /// IK Controller - follows Single Responsibility Principle
    /// Handles inverse kinematics for character limbs and head tracking
    /// </summary>
    public class IKController : MonoBehaviour
    {
        [Header("IK Settings")]
        [SerializeField] private float ikWeight = 1f;
        [SerializeField] private float ikLookWeight = 1f;
        [SerializeField] private float bodyWeight = 0.5f;
        [SerializeField] private float headWeight = 1f;
        [SerializeField] private float eyesWeight = 1f;
        [SerializeField] private float clampWeight = 0.5f;

        [Header("Target Tracking")]
        [SerializeField] private Transform lookTarget;
        [SerializeField] private Transform leftHandTarget;
        [SerializeField] private Transform rightHandTarget;
        [SerializeField] private Transform leftFootTarget;
        [SerializeField] private Transform rightFootTarget;

        [Header("IK Smoothing")]
        [SerializeField] private float lookSlerpSpeed = 5f;
        [SerializeField] private float handLerpSpeed = 10f;
        [SerializeField] private float footLerpSpeed = 10f;

        private Animator animator;
        private Vector3 currentLookPosition;
        private bool hasLookTarget;

        public event Action<Transform> OnLookTargetChanged;

        private void Awake()
        {
            animator = GetComponent<Animator>();
            if (animator == null)
            {
                animator = GetComponentInChildren<Animator>();
            }
        }

        private void Start()
        {
            if (lookTarget != null)
            {
                currentLookPosition = lookTarget.position;
                hasLookTarget = true;
            }
        }

        private void Update()
        {
            UpdateLookTarget();
        }

        private void UpdateLookTarget()
        {
            if (lookTarget != null)
            {
                // Smoothly interpolate look position
                currentLookPosition = Vector3.Lerp(
                    currentLookPosition,
                    lookTarget.position,
                    Time.deltaTime * lookSlerpSpeed
                );
            }
        }

        private void OnAnimatorIK(int layerIndex)
        {
            if (animator == null) return;

            // Handle look-at IK
            HandleLookAtIK();

            // Handle hand IK
            HandleHandIK();

            // Handle foot IK
            HandleFootIK();
        }

        private void HandleLookAtIK()
        {
            if (!hasLookTarget) return;

            // Set look-at target
            animator.SetLookAtWeight(ikLookWeight, bodyWeight, headWeight, eyesWeight, clampWeight);
            animator.SetLookAtPosition(currentLookPosition);
        }

        private void HandleHandIK()
        {
            // Left hand IK
            if (leftHandTarget != null)
            {
                animator.SetIKPositionWeight(AvatarIKGoal.LeftHand, ikWeight);
                animator.SetIKRotationWeight(AvatarIKGoal.LeftHand, ikWeight);
                
                Vector3 targetPosition = Vector3.Lerp(
                    animator.GetIKPosition(AvatarIKGoal.LeftHand),
                    leftHandTarget.position,
                    Time.deltaTime * handLerpSpeed
                );
                
                Quaternion targetRotation = Quaternion.Slerp(
                    animator.GetIKRotation(AvatarIKGoal.LeftHand),
                    leftHandTarget.rotation,
                    Time.deltaTime * handLerpSpeed
                );

                animator.SetIKPosition(AvatarIKGoal.LeftHand, targetPosition);
                animator.SetIKRotation(AvatarIKGoal.LeftHand, targetRotation);
            }
            else
            {
                animator.SetIKPositionWeight(AvatarIKGoal.LeftHand, 0f);
                animator.SetIKRotationWeight(AvatarIKGoal.LeftHand, 0f);
            }

            // Right hand IK
            if (rightHandTarget != null)
            {
                animator.SetIKPositionWeight(AvatarIKGoal.RightHand, ikWeight);
                animator.SetIKRotationWeight(AvatarIKGoal.RightHand, ikWeight);
                
                Vector3 targetPosition = Vector3.Lerp(
                    animator.GetIKPosition(AvatarIKGoal.RightHand),
                    rightHandTarget.position,
                    Time.deltaTime * handLerpSpeed
                );
                
                Quaternion targetRotation = Quaternion.Slerp(
                    animator.GetIKRotation(AvatarIKGoal.RightHand),
                    rightHandTarget.rotation,
                    Time.deltaTime * handLerpSpeed
                );

                animator.SetIKPosition(AvatarIKGoal.RightHand, targetPosition);
                animator.SetIKRotation(AvatarIKGoal.RightHand, targetRotation);
            }
            else
            {
                animator.SetIKPositionWeight(AvatarIKGoal.RightHand, 0f);
                animator.SetIKRotationWeight(AvatarIKGoal.RightHand, 0f);
            }
        }

        private void HandleFootIK()
        {
            // Left foot IK
            if (leftFootTarget != null)
            {
                animator.SetIKPositionWeight(AvatarIKGoal.LeftFoot, ikWeight);
                animator.SetIKRotationWeight(AvatarIKGoal.LeftFoot, ikWeight);
                
                Vector3 targetPosition = Vector3.Lerp(
                    animator.GetIKPosition(AvatarIKGoal.LeftFoot),
                    leftFootTarget.position,
                    Time.deltaTime * footLerpSpeed
                );
                
                Quaternion targetRotation = Quaternion.Slerp(
                    animator.GetIKRotation(AvatarIKGoal.LeftFoot),
                    leftFootTarget.rotation,
                    Time.deltaTime * footLerpSpeed
                );

                animator.SetIKPosition(AvatarIKGoal.LeftFoot, targetPosition);
                animator.SetIKRotation(AvatarIKGoal.LeftFoot, targetRotation);
            }
            else
            {
                animator.SetIKPositionWeight(AvatarIKGoal.LeftFoot, 0f);
                animator.SetIKRotationWeight(AvatarIKGoal.LeftFoot, 0f);
            }

            // Right foot IK
            if (rightFootTarget != null)
            {
                animator.SetIKPositionWeight(AvatarIKGoal.RightFoot, ikWeight);
                animator.SetIKRotationWeight(AvatarIKGoal.RightFoot, ikWeight);
                
                Vector3 targetPosition = Vector3.Lerp(
                    animator.GetIKPosition(AvatarIKGoal.RightFoot),
                    rightFootTarget.position,
                    Time.deltaTime * footLerpSpeed
                );
                
                Quaternion targetRotation = Quaternion.Slerp(
                    animator.GetIKRotation(AvatarIKGoal.RightFoot),
                    rightFootTarget.rotation,
                    Time.deltaTime * footLerpSpeed
                );

                animator.SetIKPosition(AvatarIKGoal.RightFoot, targetPosition);
                animator.SetIKRotation(AvatarIKGoal.RightFoot, targetRotation);
            }
            else
            {
                animator.SetIKPositionWeight(AvatarIKGoal.RightFoot, 0f);
                animator.SetIKRotationWeight(AvatarIKGoal.RightFoot, 0f);
            }
        }

        // Public methods to set IK targets
        public void SetLookTarget(Transform target)
        {
            lookTarget = target;
            hasLookTarget = target != null;
            OnLookTargetChanged?.Invoke(target);
        }

        public void SetLookTargetPosition(Vector3 position)
        {
            currentLookPosition = position;
            hasLookTarget = true;
        }

        public void SetLeftHandTarget(Transform target)
        {
            leftHandTarget = target;
        }

        public void SetRightHandTarget(Transform target)
        {
            rightHandTarget = target;
        }

        public void SetLeftFootTarget(Transform target)
        {
            leftFootTarget = target;
        }

        public void SetRightFootTarget(Transform target)
        {
            rightFootTarget = target;
        }

        public void SetIKWeight(float weight)
        {
            ikWeight = Mathf.Clamp01(weight);
        }

        public void SetLookIKWeight(float weight)
        {
            ikLookWeight = Mathf.Clamp01(weight);
        }

        public void ClearIKTargets()
        {
            lookTarget = null;
            leftHandTarget = null;
            rightHandTarget = null;
            leftFootTarget = null;
            rightFootTarget = null;
            hasLookTarget = false;
        }
    }
}
