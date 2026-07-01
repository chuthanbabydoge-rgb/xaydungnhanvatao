using UnityEngine;
using System;
using System.Threading.Tasks;

namespace AICompanion.AI
{
    /// <summary>
    /// Interface for AI controller managing AI companion behavior and communication
    /// </summary>
    public interface IAIController
    {
        /// <summary>
        /// Event triggered when AI response is received
        /// </summary>
        event Action<AIResponse> OnAIResponse;

        /// <summary>
        /// Event triggered when AI emotion changes
        /// </summary>
        event Action<EmotionState> OnEmotionChanged;

        /// <summary>
        /// Event triggered when AI requests an animation
        /// </summary>
        event Action<string> OnAnimationRequested;

        /// <summary>
        /// Send user message to AI for processing
        /// </summary>
        /// <param name="message">User message text</param>
        /// <returns>AI response</returns>
        Task<AIResponse> SendMessageAsync(string message);

        /// <summary>
        /// Send user voice audio to AI for processing
        /// </summary>
        /// <param name="audioData">Audio data bytes</param>
        /// <returns>AI response</returns>
        Task<AIResponse> SendVoiceAsync(byte[] audioData);

        /// <summary>
        /// Send vision data to AI for processing
        /// </summary>
        /// <param name="imageData">Image data bytes</param>
        /// <returns>AI response</returns>
        Task<AIResponse> SendVisionAsync(byte[] imageData);

        /// <summary>
        /// Get current AI emotion state
        /// </summary>
        /// <returns>Current emotion state</returns>
        EmotionState GetCurrentEmotion();

        /// <summary>
        /// Set AI personality parameters
        /// </summary>
        /// <param name="personality">Personality configuration</param>
        void SetPersonality(PersonalityConfig personality);

        /// <summary>
        /// Initialize AI controller
        /// </summary>
        Task InitializeAsync();

        /// <summary>
        /// Shutdown AI controller
        /// </summary>
        Task ShutdownAsync();
    }

    /// <summary>
    /// AI response data structure
    /// </summary>
    [Serializable]
    public class AIResponse
    {
        public string text;
        public string emotion;
        public string animation;
        public string visemeData;
        public float confidence;
        public string[] suggestedActions;
        public long timestamp;
    }

    /// <summary>
    /// Emotion state enumeration
    /// </summary>
    public enum EmotionType
    {
        Neutral,
        Happy,
        Sad,
        Angry,
        Surprised,
        Fearful,
        Disgusted,
        Curious,
        Excited,
        Bored,
        Tired,
        Confused,
        Loving,
        Annoyed,
        Proud,
        Embarrassed
    }

    /// <summary>
    /// Emotion state data structure
    /// </summary>
    [Serializable]
    public class EmotionState
    {
        public EmotionType primaryEmotion;
        public float emotionIntensity;
        public float mood;
        public float energy;
        public float trust;
        public float affinity;
        public long timestamp;

        public EmotionState()
        {
            primaryEmotion = EmotionType.Neutral;
            emotionIntensity = 0.5f;
            mood = 0.5f;
            energy = 0.5f;
            trust = 0.5f;
            affinity = 0.5f;
            timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        }
    }

    /// <summary>
    /// Personality configuration
    /// </summary>
    [Serializable]
    public class PersonalityConfig
    {
        public float openness;      // Openness to experience
        public float conscientiousness; // Conscientiousness
        public float extraversion;  // Extraversion
        public float agreeableness; // Agreeableness
        public float neuroticism;   // Neuroticism
        public string[] quirks;     // Character quirks
        public string responseStyle; // Response style (formal, casual, playful, etc.)

        public PersonalityConfig()
        {
            openness = 0.5f;
            conscientiousness = 0.5f;
            extraversion = 0.5f;
            agreeableness = 0.5f;
            neuroticism = 0.5f;
            quirks = new string[0];
            responseStyle = "casual";
        }
    }
}