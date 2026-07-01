using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Speech Controller - follows Single Responsibility Principle
    /// Manages text-to-speech synthesis and speech animation coordination
    /// </summary>
    public class SpeechController : MonoBehaviour
    {
        [Header("Audio Components")]
        [SerializeField] private AudioSource speechAudioSource;
        [SerializeField] private AudioSource voiceAudioSource;

        [Header("Speech Settings")]
        [SerializeField] private float speechRate = 1f;
        [SerializeField] private float speechPitch = 1f;
        [SerializeField] private float speechVolume = 1f;
        [SerializeField] private bool enableProceduralProsody = true;

        [Header("Voice Characteristics")]
        [SerializeField] private VoiceType voiceType = VoiceType.Neutral;
        [SerializeField] private float voiceWarmth = 0.5f;
        [SerializeField] private float voiceEnergy = 0.5f;

        [Header("Animation Integration")]
        [SerializeField] private LipSyncController lipSyncController;
        [SerializeField] private FacialAnimationController facialController;
        [SerializeField] private ProceduralAnimationController proceduralController;

        [Header("Speech Queue")]
        [SerializeField] private int maxQueueSize = 10;
        [SerializeField] private bool prioritizeInterruptions = true;

        private Queue<SpeechRequest> speechQueue = new Queue<SpeechRequest>();
        private SpeechRequest currentSpeech;
        private bool isSpeaking;
        private Coroutine speechCoroutine;

        public event Action<string> OnSpeechStarted;
        public event Action<string> OnSpeechCompleted;
        public event Action<string> OnSpeechInterrupted;
        public event Action<float> OnSpeechProgress;

        public enum VoiceType
        {
            Neutral,
            Warm,
            Energetic,
            Calm,
            Authoritative,
            Friendly,
            Serious,
            Playful
        }

        [Serializable]
        public class SpeechRequest
        {
            public string text;
            public float priority = 1f;
            public VoiceType? overrideVoiceType;
            public float? overridePitch;
            public float? overrideRate;
            public bool interruptCurrent = false;
            public Dictionary<string, float> emotionModifiers = new Dictionary<string, float>();
        }

        private void Awake()
        {
            InitializeAudioSources();
        }

        private void InitializeAudioSources()
        {
            if (speechAudioSource == null)
            {
                speechAudioSource = gameObject.AddComponent<AudioSource>();
            }

            if (voiceAudioSource == null)
            {
                voiceAudioSource = gameObject.AddComponent<AudioSource>();
            }

            speechAudioSource.playOnAwake = false;
            voiceAudioSource.playOnAwake = false;
        }

        private void Start()
        {
            FindAnimationControllers();
        }

        private void FindAnimationControllers()
        {
            if (lipSyncController == null)
            {
                lipSyncController = GetComponent<LipSyncController>();
            }

            if (facialController == null)
            {
                facialController = GetComponent<FacialAnimationController>();
            }

            if (proceduralController == null)
            {
                proceduralController = GetComponent<ProceduralAnimationController>();
            }
        }

        public void Speak(string text, bool interrupt = false)
        {
            Speak(text, voiceType, interrupt);
        }

        public void Speak(string text, VoiceType voice, bool interrupt = false)
        {
            var request = new SpeechRequest
            {
                text = text,
                overrideVoiceType = voice,
                interruptCurrent = interrupt
            };

            EnqueueSpeech(request);
        }

        public void SpeakWithEmotion(string text, Dictionary<string, float> emotionModifiers, bool interrupt = false)
        {
            var request = new SpeechRequest
            {
                text = text,
                emotionModifiers = emotionModifiers,
                interruptCurrent = interrupt
            };

            EnqueueSpeech(request);
        }

        private void EnqueueSpeech(SpeechRequest request)
        {
            if (request.interruptCurrent && isSpeaking)
            {
                InterruptCurrentSpeech();
            }

            if (speechQueue.Count >= maxQueueSize)
            {
                speechQueue.Dequeue();
            }

            speechQueue.Enqueue(request);

            if (!isSpeaking)
            {
                ProcessNextSpeech();
            }
        }

        private void ProcessNextSpeech()
        {
            if (speechQueue.Count == 0)
            {
                isSpeaking = false;
                return;
            }

            currentSpeech = speechQueue.Dequeue();
            speechCoroutine = StartCoroutine(SpeechCoroutine(currentSpeech));
        }

        private IEnumerator SpeechCoroutine(SpeechRequest request)
        {
            isSpeaking = true;
            OnSpeechStarted?.Invoke(request.text);

            // Apply voice characteristics
            ApplyVoiceCharacteristics(request);

            // Start animation
            StartSpeechAnimation();

            // Simulate speech synthesis (in production, this would use TTS API)
            float speechDuration = EstimateSpeechDuration(request.text);
            float elapsedTime = 0f;

            while (elapsedTime < speechDuration)
            {
                elapsedTime += Time.deltaTime;
                float progress = elapsedTime / speechDuration;
                OnSpeechProgress?.Invoke(progress);

                // Update procedural prosody
                if (enableProceduralProsody)
                {
                    UpdateProceduralProsody(progress, request);
                }

                yield return null;
            }

            // End animation
            EndSpeechAnimation();

            isSpeaking = false;
            OnSpeechCompleted?.Invoke(request.text);

            // Process next speech
            ProcessNextSpeech();
        }

        private void ApplyVoiceCharacteristics(SpeechRequest request)
        {
            VoiceType effectiveVoiceType = request.overrideVoiceType ?? voiceType;
            float effectivePitch = request.overridePitch ?? speechPitch;
            float effectiveRate = request.overrideRate ?? speechRate;

            // Apply voice type characteristics
            switch (effectiveVoiceType)
            {
                case VoiceType.Warm:
                    effectivePitch *= 0.95f;
                    voiceWarmth = 0.8f;
                    voiceEnergy = 0.6f;
                    break;
                case VoiceType.Energetic:
                    effectivePitch *= 1.1f;
                    effectiveRate *= 1.2f;
                    voiceWarmth = 0.7f;
                    voiceEnergy = 0.9f;
                    break;
                case VoiceType.Calm:
                    effectivePitch *= 0.9f;
                    effectiveRate *= 0.8f;
                    voiceWarmth = 0.6f;
                    voiceEnergy = 0.3f;
                    break;
                case VoiceType.Authoritative:
                    effectivePitch *= 0.95f;
                    effectiveRate *= 0.9f;
                    voiceWarmth = 0.4f;
                    voiceEnergy = 0.7f;
                    break;
                case VoiceType.Friendly:
                    effectivePitch *= 1.05f;
                    voiceWarmth = 0.9f;
                    voiceEnergy = 0.6f;
                    break;
                case VoiceType.Serious:
                    effectivePitch *= 0.9f;
                    effectiveRate *= 0.85f;
                    voiceWarmth = 0.3f;
                    voiceEnergy = 0.5f;
                    break;
                case VoiceType.Playful:
                    effectivePitch *= 1.15f;
                    effectiveRate *= 1.1f;
                    voiceWarmth = 0.8f;
                    voiceEnergy = 0.8f;
                    break;
                default:
                    voiceWarmth = 0.5f;
                    voiceEnergy = 0.5f;
                    break;
            }

            // Apply emotion modifiers
            foreach (var modifier in request.emotionModifiers)
            {
                ApplyEmotionModifier(modifier.Key, modifier.Value);
            }

            // In production, these would be applied to the TTS engine
            speechAudioSource.pitch = effectivePitch;
        }

        private void ApplyEmotionModifier(string emotion, float intensity)
        {
            switch (emotion.ToLower())
            {
                case "happiness":
                    speechPitch *= (1f + intensity * 0.1f);
                    voiceWarmth += intensity * 0.2f;
                    break;
                case "sadness":
                    speechPitch *= (1f - intensity * 0.1f);
                    speechRate *= (1f - intensity * 0.2f);
                    voiceEnergy -= intensity * 0.3f;
                    break;
                case "anger":
                    speechPitch *= (1f + intensity * 0.15f);
                    speechRate *= (1f + intensity * 0.3f);
                    voiceEnergy += intensity * 0.4f;
                    break;
                case "fear":
                    speechPitch *= (1f + intensity * 0.2f);
                    speechRate *= (1f + intensity * 0.4f);
                    voiceEnergy += intensity * 0.3f;
                    break;
                case "surprise":
                    speechPitch *= (1f + intensity * 0.25f);
                    voiceEnergy += intensity * 0.3f;
                    break;
            }
        }

        private void StartSpeechAnimation()
        {
            // Trigger lip sync
            if (lipSyncController != null)
            {
                lipSyncController.SetSensitivity(1.2f);
            }

            // Set speaking expression
            if (facialController != null)
            {
                facialController.SetExpression(FacialAnimationController.ExpressionType.Neutral);
            }

            // Adjust breathing for speech
            if (proceduralController != null)
            {
                proceduralController.SetBreathingParameters(1.5f, 0.015f);
            }
        }

        private void EndSpeechAnimation()
        {
            // Reset lip sync
            if (lipSyncController != null)
            {
                lipSyncController.SetSensitivity(1f);
            }

            // Reset breathing
            if (proceduralController != null)
            {
                proceduralController.SetBreathingParameters(1f, 0.02f);
            }
        }

        private void UpdateProceduralProsody(float progress, SpeechRequest request)
        {
            // Add subtle pitch variations based on sentence structure
            float pitchVariation = Mathf.Sin(progress * Mathf.PI * 2f) * 0.05f;
            speechAudioSource.pitch = speechPitch + pitchVariation;

            // Add energy variations based on speech progress
            float energyVariation = Mathf.PerlinNoise(progress * 10f, Time.time) * 0.1f;
            float currentVolume = speechVolume + energyVariation * voiceEnergy;
            speechAudioSource.volume = Mathf.Clamp01(currentVolume);
        }

        private float EstimateSpeechDuration(string text)
        {
            // Simple estimation based on character count
            // In production, this would use the TTS API's duration estimation
            float baseRate = 0.1f; // seconds per character
            float wordCount = text.Split(' ').Length;
            return Mathf.Max(1f, text.Length * baseRate / speechRate + wordCount * 0.1f);
        }

        public void InterruptCurrentSpeech()
        {
            if (speechCoroutine != null)
            {
                StopCoroutine(speechCoroutine);
                speechCoroutine = null;
            }

            if (currentSpeech != null)
            {
                OnSpeechInterrupted?.Invoke(currentSpeech.text);
            }

            isSpeaking = false;
            EndSpeechAnimation();

            // Clear queue if prioritizing interruptions
            if (prioritizeInterruptions)
            {
                speechQueue.Clear();
            }
        }

        public void StopSpeaking()
        {
            InterruptCurrentSpeech();
            speechQueue.Clear();
        }

        public void SetVoiceType(VoiceType type)
        {
            voiceType = type;
        }

        public void SetSpeechRate(float rate)
        {
            speechRate = Mathf.Clamp(rate, 0.5f, 2f);
        }

        public void SetSpeechPitch(float pitch)
        {
            speechPitch = Mathf.Clamp(pitch, 0.5f, 2f);
        }

        public void SetSpeechVolume(float volume)
        {
            speechVolume = Mathf.Clamp01(volume);
        }

        public bool IsSpeaking()
        {
            return isSpeaking;
        }

        public int GetQueueCount()
        {
            return speechQueue.Count;
        }

        public void ClearQueue()
        {
            speechQueue.Clear();
        }
    }
}
