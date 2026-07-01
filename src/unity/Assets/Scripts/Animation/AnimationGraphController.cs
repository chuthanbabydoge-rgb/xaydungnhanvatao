using UnityEngine;
using AICompanion.Core.Interfaces;

namespace AICompanion.Animation
{
    /// <summary>
    /// Animation Graph Controller - follows Single Responsibility Principle
    /// Manages animation state machine and transitions
    /// </summary>
    public class AnimationGraphController : MonoBehaviour, IAnimationController
    {
        [Header("Animator Components")]
        [SerializeField] private Animator animator;

        [Header("Animation Parameters")]
        [SerializeField] private float movementSpeedThreshold = 0.1f;
        [SerializeField] private float jumpForce = 5f;

        [Header("Current State")]
        [SerializeField] private AnimationState currentState = AnimationState.Idle;

        // Hash parameters for optimization
        private int speedHash;
        private int jumpHash;
        private int groundHash;
        private int emotionHash;
        private int interactionHash;

        private void Awake()
        {
            InitializeAnimator();
            CacheAnimationParameters();
        }

        private void InitializeAnimator()
        {
            if (animator == null)
            {
                animator = GetComponent<Animator>();
            }

            if (animator == null)
            {
                animator = GetComponentInChildren<Animator>();
            }

            if (animator == null)
            {
                animator = gameObject.AddComponent<Animator>();
            }
        }

        private void CacheAnimationParameters()
        {
            // Cache parameter hashes for performance
            speedHash = Animator.StringToHash("Speed");
            jumpHash = Animator.StringToHash("Jump");
            groundHash = Animator.StringToHash("Ground");
            emotionHash = Animator.StringToHash("Emotion");
            interactionHash = Animator.StringToHash("Interaction");
        }

        public void PlayAnimation(string animationName, float fadeDuration = 0.2f)
        {
            if (animator == null) return;

            animator.CrossFade(animationName, fadeDuration);
        }

        public void PlayAnimationByTrigger(string triggerName)
        {
            if (animator == null) return;

            int triggerHash = Animator.StringToHash(triggerName);
            animator.SetTrigger(triggerHash);
        }

        public void SetFloat(string parameterName, float value)
        {
            if (animator == null) return;

            animator.SetFloat(parameterName, value);
        }

        public void SetInteger(string parameterName, int value)
        {
            if (animator == null) return;

            animator.SetInteger(parameterName, value);
        }

        public void SetBool(string parameterName, bool value)
        {
            if (animator == null) return;

            animator.SetBool(parameterName, value);
        }

        public void SetTrigger(string triggerName)
        {
            if (animator == null) return;

            animator.SetTrigger(triggerName);
        }

        public bool IsPlayingAnimation(string animationName)
        {
            if (animator == null) return false;

            AnimatorStateInfo stateInfo = animator.GetCurrentAnimatorStateInfo(0);
            return stateInfo.IsName(animationName);
        }

        public float GetCurrentAnimationLength()
        {
            if (animator == null) return 0f;

            AnimatorStateInfo stateInfo = animator.GetCurrentAnimatorStateInfo(0);
            return stateInfo.length;
        }

        public AnimationState GetCurrentState()
        {
            return currentState;
        }

        // Convenience methods for common animations
        public void SetMovementSpeed(float speed)
        {
            SetFloat(speedHash, speed);
            UpdateMovementState(speed);
        }

        public void SetJump(bool isJumping)
        {
            SetBool(jumpHash, isJumping);
            if (isJumping)
            {
                currentState = AnimationState.Jumping;
            }
        }

        public void SetGrounded(bool isGrounded)
        {
            SetBool(groundHash, isGrounded);
            if (!isGrounded)
            {
                currentState = AnimationState.Falling;
            }
        }

        public void SetEmotion(int emotionValue)
        {
            SetInteger(emotionHash, emotionValue);
            currentState = AnimationState.Emotional;
        }

        public void SetInteraction(int interactionValue)
        {
            SetInteger(interactionHash, interactionValue);
            currentState = AnimationState.Interacting;
        }

        private void UpdateMovementState(float speed)
        {
            if (speed < movementSpeedThreshold)
            {
                currentState = AnimationState.Idle;
            }
            else if (speed < 3f)
            {
                currentState = AnimationState.Walking;
            }
            else
            {
                currentState = AnimationState.Running;
            }
        }

        private void OnAnimatorMove()
        {
            // Handle root motion if needed
            if (animator.applyRootMotion)
            {
                transform.position += animator.deltaPosition;
                transform.rotation *= animator.deltaRotation;
            }
        }
    }
}
