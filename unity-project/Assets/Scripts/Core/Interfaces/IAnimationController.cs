using UnityEngine;

namespace AICompanion.Core.Interfaces
{
    /// <summary>
    /// Interface for animation controller - follows Interface Segregation Principle
    /// </summary>
    public interface IAnimationController
    {
        void PlayAnimation(string animationName, float fadeDuration = 0.2f);
        void PlayAnimationByTrigger(string triggerName);
        void SetFloat(string parameterName, float value);
        void SetInteger(string parameterName, int value);
        void SetBool(string parameterName, bool value);
        void SetTrigger(string triggerName);
        bool IsPlayingAnimation(string animationName);
        float GetCurrentAnimationLength();
        AnimationState GetCurrentState();
    }

    public enum AnimationState
    {
        Idle,
        Walking,
        Running,
        Jumping,
        Falling,
        Landing,
        Interacting,
        Talking,
        Emotional
    }
}
