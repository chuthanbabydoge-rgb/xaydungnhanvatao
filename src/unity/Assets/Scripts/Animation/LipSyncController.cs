using UnityEngine;
using System;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Lip Sync Controller - follows Single Responsibility Principle
    /// Manages lip synchronization with audio speech
    /// </summary>
    public class LipSyncController : MonoBehaviour
    {
        [Header("Audio Source")]
        [SerializeField] private AudioSource audioSource;

        [Header("Lip Sync Settings")]
        [SerializeField] private float sensitivity = 1f;
        [SerializeField] private float smoothing = 0.1f;
        [SerializeField] private float volumeThreshold = 0.01f;

        [Header("Viseme Configuration")]
        [SerializeField] private List<VisemeMapping> visemeMappings = new List<VisemeMapping>();
        [SerializeField] private int visemeCount = 15;

        [Header("Mouth Components")]
        [SerializeField] private SkinnedMeshRenderer faceRenderer;
        [SerializeField] private FacialAnimationController facialController;

        private float[] audioSpectrum;
        private float currentVolume;
        private float smoothedVolume;
        private int currentViseme;
        private Dictionary<string, int> visemeBlendShapeIndices = new Dictionary<string, int>();
        private Dictionary<int, float> visemeWeights = new Dictionary<int, float>();

        public event Action OnSpeechStarted;
        public event Action OnSpeechEnded;

        [Serializable]
        public class VisemeMapping
        {
            public int visemeIndex;
            public string blendShapeName;
            public float weight = 1f;
        }

        private void Start()
        {
            InitializeAudioAnalysis();
            InitializeVisemeMappings();
        }

        private void InitializeAudioAnalysis()
        {
            if (audioSource == null)
            {
                audioSource = GetComponent<AudioSource>();
            }

            // Initialize spectrum analysis
            audioSpectrum = new float[256];
        }

        private void InitializeVisemeMappings()
        {
            if (faceRenderer == null)
            {
                faceRenderer = GetComponentInChildren<SkinnedMeshRenderer>();
            }

            if (faceRenderer == null) return;

            // Cache viseme blend shape indices
            foreach (var mapping in visemeMappings)
            {
                for (int i = 0; i < faceRenderer.sharedMesh.blendShapeCount; i++)
                {
                    string blendShapeName = faceRenderer.sharedMesh.GetBlendShapeName(i);
                    if (blendShapeName == mapping.blendShapeName)
                    {
                        visemeBlendShapeIndices[mapping.blendShapeName] = i;
                        break;
                    }
                }
            }

            // Initialize viseme weights
            for (int i = 0; i < visemeCount; i++)
            {
                visemeWeights[i] = 0f;
            }
        }

        private void Update()
        {
            if (audioSource == null || !audioSource.isPlaying) return;

            AnalyzeAudio();
            UpdateVisemes();
        }

        private void AnalyzeAudio()
        {
            // Get audio spectrum data
            audioSource.GetSpectrumData(audioSpectrum, 0, FFTWindow.BlackmanHarris);

            // Calculate volume
            float sum = 0f;
            for (int i = 0; i < audioSpectrum.Length; i++)
            {
                sum += audioSpectrum[i];
            }
            currentVolume = sum / audioSpectrum.Length;

            // Smooth volume
            smoothedVolume = Mathf.Lerp(smoothedVolume, currentVolume, smoothing);

            // Detect speech start/end
            DetectSpeechActivity();
        }

        private void DetectSpeechActivity()
        {
            bool isSpeaking = smoothedVolume > volumeThreshold;

            if (isSpeaking && currentViseme == 0)
            {
                OnSpeechStarted?.Invoke();
            }
            else if (!isSpeaking && currentViseme != 0)
            {
                OnSpeechEnded?.Invoke();
            }
        }

        private void UpdateVisemes()
        {
            if (smoothedVolume < volumeThreshold)
            {
                // Reset to neutral viseme
                SetViseme(0);
                return;
            }

            // Calculate viseme based on audio characteristics
            int newViseme = CalculateVisemeFromAudio();
            SetViseme(newViseme);
        }

        private int CalculateVisemeFromAudio()
        {
            // Simple viseme calculation based on audio spectrum
            // In production, this would use more sophisticated phoneme analysis
            
            float lowFreq = 0f;
            float midFreq = 0f;
            float highFreq = 0f;

            for (int i = 0; i < audioSpectrum.Length; i++)
            {
                if (i < audioSpectrum.Length / 3)
                {
                    lowFreq += audioSpectrum[i];
                }
                else if (i < 2 * audioSpectrum.Length / 3)
                {
                    midFreq += audioSpectrum[i];
                }
                else
                {
                    highFreq += audioSpectrum[i];
                }
            }

            // Map frequency distribution to visemes
            if (lowFreq > midFreq && lowFreq > highFreq)
            {
                // Low frequency dominant - open mouth sounds
                return 1; // "ah" sound
            }
            else if (midFreq > lowFreq && midFreq > highFreq)
            {
                // Mid frequency dominant - neutral sounds
                return 2; // "eh" sound
            }
            else if (highFreq > lowFreq && highFreq > midFreq)
            {
                // High frequency dominant - closed mouth sounds
                return 3; // "ee" sound
            }

            return 0; // Neutral
        }

        private void SetViseme(int visemeIndex)
        {
            currentViseme = visemeIndex;

            // Reset all viseme weights
            for (int i = 0; i < visemeCount; i++)
            {
                visemeWeights[i] = 0f;
            }

            // Set current viseme weight
            if (visemeWeights.ContainsKey(visemeIndex))
            {
                visemeWeights[visemeIndex] = smoothedVolume * sensitivity;
            }

            // Apply to blend shapes
            ApplyVisemeToBlendShapes();
        }

        private void ApplyVisemeToBlendShapes()
        {
            if (faceRenderer == null) return;

            foreach (var mapping in visemeMappings)
            {
                if (visemeWeights.ContainsKey(mapping.visemeIndex))
                {
                    float weight = visemeWeights[mapping.visemeIndex] * mapping.weight;

                    if (visemeBlendShapeIndices.ContainsKey(mapping.blendShapeName))
                    {
                        int index = visemeBlendShapeIndices[mapping.blendShapeName];
                        faceRenderer.SetBlendShapeWeight(index, weight * 100f);
                    }

                    // Also update facial controller if available
                    if (facialController != null)
                    {
                        facialController.SetBlendShapeValue(mapping.blendShapeName, weight);
                    }
                }
            }
        }

        // Public methods for external control
        public void PlaySpeech(AudioClip speechClip)
        {
            if (audioSource == null) return;

            audioSource.clip = speechClip;
            audioSource.Play();
        }

        public void StopSpeech()
        {
            if (audioSource == null) return;

            audioSource.Stop();
            SetViseme(0);
        }

        public void SetVisemeDirectly(int visemeIndex, float weight)
        {
            if (visemeWeights.ContainsKey(visemeIndex))
            {
                visemeWeights[visemeIndex] = weight;
                ApplyVisemeToBlendShapes();
            }
        }

        public void SetSensitivity(float sensitivity)
        {
            this.sensitivity = sensitivity;
        }

        public void SetSmoothing(float smoothing)
        {
            this.smoothing = smoothing;
        }

        public void SetVolumeThreshold(float threshold)
        {
            this.volumeThreshold = threshold;
        }

        public void AddVisemeMapping(int visemeIndex, string blendShapeName, float weight = 1f)
        {
            var mapping = new VisemeMapping
            {
                visemeIndex = visemeIndex,
                blendShapeName = blendShapeName,
                weight = weight
            };
            visemeMappings.Add(mapping);
            InitializeVisemeMappings();
        }

        public float GetCurrentVolume()
        {
            return smoothedVolume;
        }

        public int GetCurrentViseme()
        {
            return currentViseme;
        }
    }
}
