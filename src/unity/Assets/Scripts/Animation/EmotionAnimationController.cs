using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Emotion Animation Controller - follows Single Responsibility Principle
    /// Manages emotional state transitions and blended emotion animations
    /// </summary>
    public class EmotionAnimationController : MonoBehaviour
    {
        [Header("Face Components")]
        [SerializeField] private SkinnedMeshRenderer faceRenderer;
        [SerializeField] private FacialAnimationController facialController;
        [SerializeField] private MicroExpressionController microExpressionController;

        [Header("Emotion Settings")]
        [SerializeField] private float emotionTransitionSpeed = 2f;
        [SerializeField] private float emotionBlendSpeed = 1f;
        [SerializeField] private bool enableEmotionBlending = true;
        [SerializeField] private bool enableEmotionDecay = true;
        [SerializeField] private float emotionDecayRate = 0.5f;

        [Header("Emotion States")]
        [SerializeField] private EmotionState currentEmotion;
        [SerializeField] private EmotionState targetEmotion;
        [SerializeField] private List<EmotionLayer> emotionLayers = new List<EmotionLayer>();

        [Header("Emotion Presets")]
        [SerializeField] private List<EmotionPreset> emotionPresets = new List<EmotionPreset>();

        [Header("Dynamic Responses")]
        [SerializeField] private bool enableDynamicResponses = true;
        [SerializeField] private float responseIntensity = 0.8f;
        [SerializeField] private float responseDuration = 1.5f;

        [Header("Body Integration")]
        [SerializeField] private ProceduralAnimationController proceduralController;
        [SerializeField] private GestureController gestureController;
        [SerializeField] private EyeTrackingController eyeTrackingController;

        private Dictionary<string, int> blendShapeIndices = new Dictionary<string, int>();
        private Dictionary<string, float> currentEmotionValues = new Dictionary<string, float>();
        private Dictionary<string, float> targetEmotionValues = new Dictionary<string, float>();
        private Coroutine emotionTransitionCoroutine;
        private Coroutine emotionDecayCoroutine;

        public event Action<EmotionType> OnEmotionChanged;
        public event Action<EmotionType, float> OnEmotionIntensityChanged;
        public event Action<EmotionLayer> OnEmotionLayerAdded;
        public event Action<EmotionLayer> OnEmotionLayerRemoved;

        public enum EmotionType
        {
            Neutral,
            Happy,
            Sad,
            Angry,
            Fearful,
            Surprised,
            Disgusted,
            Contemptuous,
            Excited,
            Calm,
            Confused,
            Proud,
            Ashamed,
            Loving,
            Hostile
        }

        [Serializable]
        public class EmotionState
        {
            public EmotionType primaryEmotion;
            public float primaryIntensity = 1f;
            public Dictionary<EmotionType, float> secondaryEmotions = new Dictionary<EmotionType, float>();
        }

        [Serializable]
        public class EmotionLayer
        {
            public EmotionType emotionType;
            public float intensity;
            public float duration;
            public float elapsedTime;
            public bool isTemporary;
            public bool isActive;
        }

        [Serializable]
        public class EmotionPreset
        {
            public EmotionType emotionType;
            public List<BlendShapeValue> blendShapeValues = new List<BlendShapeValue>();
            public List<BodyPostureAdjustment> postureAdjustments = new List<BodyPostureAdjustment>();
            public float defaultTransitionSpeed = 2f;
        }

        [Serializable]
        public class BlendShapeValue
        {
            public string blendShapeName;
            public float value;
        }

        [Serializable]
        public class BodyPostureAdjustment
        {
            public string boneName;
            public Vector3 positionOffset;
            public Vector3 rotationOffset;
            public float weight = 1f;
        }

        private void Start()
        {
            InitializeBlendShapes();
            InitializePresets();
            InitializeControllers();
            SetEmotion(EmotionType.Neutral);
        }

        private void InitializeBlendShapes()
        {
            if (faceRenderer == null)
            {
                faceRenderer = GetComponentInChildren<SkinnedMeshRenderer>();
            }

            if (faceRenderer == null) return;

            // Cache blend shape indices
            for (int i = 0; i < faceRenderer.sharedMesh.blendShapeCount; i++)
            {
                string blendShapeName = faceRenderer.sharedMesh.GetBlendShapeName(i);
                blendShapeIndices[blendShapeName] = i;
                currentEmotionValues[blendShapeName] = 0f;
                targetEmotionValues[blendShapeName] = 0f;
            }
        }

        private void InitializePresets()
        {
            // Create default emotion presets if none are defined
            if (emotionPresets.Count == 0)
            {
                CreateDefaultPresets();
            }
        }

        private void CreateDefaultPresets()
        {
            // Happy preset
            emotionPresets.Add(new EmotionPreset
            {
                emotionType = EmotionType.Happy,
                blendShapeValues = new List<BlendShapeValue>
                {
                    new BlendShapeValue { blendShapeName = "MouthSmile_L", value = 0.8f },
                    new BlendShapeValue { blendShapeName = "MouthSmile_R", value = 0.8f },
                    new BlendShapeValue { blendShapeName = "CheekSquint_L", value = 0.5f },
                    new BlendShapeValue { blendShapeName = "CheekSquint_R", value = 0.5f },
                    new BlendShapeValue { blendShapeName = "EyeSquint_L", value = 0.3f },
                    new BlendShapeValue { blendShapeName = "EyeSquint_R", value = 0.3f }
                },
                defaultTransitionSpeed = 2f
            });

            // Sad preset
            emotionPresets.Add(new EmotionPreset
            {
                emotionType = EmotionType.Sad,
                blendShapeValues = new List<BlendShapeValue>
                {
                    new BlendShapeValue { blendShapeName = "MouthFrown_L", value = 0.6f },
                    new BlendShapeValue { blendShapeName = "MouthFrown_R", value = 0.6f },
                    new BlendShapeValue { blendShapeName = "BrowDown_L", value = 0.4f },
                    new BlendShapeValue { blendShapeName = "BrowDown_R", value = 0.4f },
                    new BlendShapeValue { blendShapeName = "EyeWide_L", value = 0.2f },
                    new BlendShapeValue { blendShapeName = "EyeWide_R", value = 0.2f }
                },
                defaultTransitionSpeed = 2.5f
            });

            // Angry preset
            emotionPresets.Add(new EmotionPreset
            {
                emotionType = EmotionType.Angry,
                blendShapeValues = new List<BlendShapeValue>
                {
                    new BlendShapeValue { blendShapeName = "BrowDown_L", value = 0.8f },
                    new BlendShapeValue { blendShapeName = "BrowDown_R", value = 0.8f },
                    new BlendShapeValue { blendShapeName = "EyeSquint_L", value = 0.7f },
                    new BlendShapeValue { blendShapeName = "EyeSquint_R", value = 0.7f },
                    new BlendShapeValue { blendShapeName = "MouthFrown_L", value = 0.5f },
                    new BlendShapeValue { blendShapeName = "MouthFrown_R", value = 0.5f },
                    new BlendShapeValue { blendShapeName = "JawOpen", value = 0.3f }
                },
                defaultTransitionSpeed = 1.5f
            });

            // Surprised preset
            emotionPresets.Add(new EmotionPreset
            {
                emotionType = EmotionType.Surprised,
                blendShapeValues = new List<BlendShapeValue>
                {
                    new BlendShapeValue { blendShapeName = "BrowOuterUp_L", value = 0.7f },
                    new BlendShapeValue { blendShapeName = "BrowOuterUp_R", value = 0.7f },
                    new BlendShapeValue { blendShapeName = "EyeWide_L", value = 0.8f },
                    new BlendShapeValue { blendShapeName = "EyeWide_R", value = 0.8f },
                    new BlendShapeValue { blendShapeName = "JawOpen", value = 0.6f },
                    new BlendShapeValue { blendShapeName = "MouthOpen", value = 0.5f }
                },
                defaultTransitionSpeed = 1f
            });

            // Fearful preset
            emotionPresets.Add(new EmotionPreset
            {
                emotionType = EmotionType.Fearful,
                blendShapeValues = new List<BlendShapeValue>
                {
                    new BlendShapeValue { blendShapeName = "BrowOuterUp_L", value = 0.5f },
                    new BlendShapeValue { blendShapeName = "BrowOuterUp_R", value = 0.5f },
                    new BlendShapeValue { blendShapeName = "BrowDown_L", value = 0.3f },
                    new BlendShapeValue { blendShapeName = "BrowDown_R", value = 0.3f },
                    new BlendShapeValue { blendShapeName = "EyeWide_L", value = 0.6f },
                    new BlendShapeValue { blendShapeName = "EyeWide_R", value = 0.6f },
                    new BlendShapeValue { blendShapeName = "MouthFrown_L", value = 0.4f },
                    new BlendShapeValue { blendShapeName = "MouthFrown_R", value = 0.4f }
                },
                defaultTransitionSpeed = 1.2f
            });
        }

        private void InitializeControllers()
        {
            if (facialController == null)
            {
                facialController = GetComponent<FacialAnimationController>();
            }

            if (microExpressionController == null)
            {
                microExpressionController = GetComponent<MicroExpressionController>();
            }

            if (proceduralController == null)
            {
                proceduralController = GetComponent<ProceduralAnimationController>();
            }

            if (gestureController == null)
            {
                gestureController = GetComponent<GestureController>();
            }

            if (eyeTrackingController == null)
            {
                eyeTrackingController = GetComponent<EyeTrackingController>();
            }
        }

        private void Update()
        {
            UpdateEmotionLayers();
            UpdateEmotionBlendShapes();
            UpdateBodyIntegration();
        }

        private void UpdateEmotionLayers()
        {
            for (int i = emotionLayers.Count - 1; i >= 0; i--)
            {
                EmotionLayer layer = emotionLayers[i];
                layer.elapsedTime += Time.deltaTime;

                if (layer.isTemporary && layer.elapsedTime >= layer.duration)
                {
                    // Remove temporary emotion layer
                    RemoveEmotionLayer(layer);
                    emotionLayers.RemoveAt(i);
                }
            }
        }

        private void UpdateEmotionBlendShapes()
        {
            if (faceRenderer == null) return;

            // Calculate target values from emotion layers
            foreach (var kvp in targetEmotionValues)
            {
                targetEmotionValues[kvp.Key] = 0f;
            }

            // Apply primary emotion
            EmotionPreset primaryPreset = GetPresetForType(currentEmotion.primaryEmotion);
            if (primaryPreset != null)
            {
                foreach (var blendShapeValue in primaryPreset.blendShapeValues)
                {
                    AddBlendShapeTarget(blendShapeValue.blendShapeName, blendShapeValue.value * currentEmotion.primaryIntensity);
                }
            }

            // Apply secondary emotions with blending
            foreach (var kvp in currentEmotion.secondaryEmotions)
            {
                EmotionType emotionType = kvp.Key;
                float intensity = kvp.Value;

                EmotionPreset preset = GetPresetForType(emotionType);
                if (preset != null)
                {
                    foreach (var blendShapeValue in preset.blendShapeValues)
                    {
                        AddBlendShapeTarget(blendShapeValue.blendShapeName, blendShapeValue.value * intensity * 0.5f);
                    }
                }
            }

            // Apply emotion layers
            foreach (var layer in emotionLayers)
            {
                if (!layer.isActive) continue;

                EmotionPreset layerPreset = GetPresetForType(layer.emotionType);
                if (layerPreset != null)
                {
                    float layerIntensity = CalculateLayerIntensity(layer);
                    foreach (var blendShapeValue in layerPreset.blendShapeValues)
                    {
                        AddBlendShapeTarget(blendShapeValue.blendShapeName, blendShapeValue.value * layerIntensity);
                    }
                }
            }

            // Smoothly interpolate to target values
            foreach (var kvp in targetEmotionValues)
            {
                string blendShapeName = kvp.Key;
                float targetValue = kvp.Value;

                if (currentEmotionValues.ContainsKey(blendShapeName))
                {
                    float currentValue = currentEmotionValues[blendShapeName];
                    float newValue = Mathf.Lerp(
                        currentValue,
                        targetValue,
                        Time.deltaTime * emotionBlendSpeed
                    );

                    currentEmotionValues[blendShapeName] = newValue;

                    // Apply to renderer
                    if (blendShapeIndices.ContainsKey(blendShapeName))
                    {
                        int index = blendShapeIndices[blendShapeName];
                        faceRenderer.SetBlendShapeWeight(index, newValue * 100f);
                    }

                    // Sync with facial controller
                    if (facialController != null)
                    {
                        facialController.SetBlendShapeValue(blendShapeName, newValue);
                    }
                }
            }
        }

        private void AddBlendShapeTarget(string blendShapeName, float value)
        {
            if (targetEmotionValues.ContainsKey(blendShapeName))
            {
                if (enableEmotionBlending)
                {
                    // Blend emotions using max for more pronounced effects
                    targetEmotionValues[blendShapeName] = Mathf.Max(
                        targetEmotionValues[blendShapeName],
                        value
                    );
                }
                else
                {
                    // Override (no blending)
                    targetEmotionValues[blendShapeName] = value;
                }
            }
        }

        private float CalculateLayerIntensity(EmotionLayer layer)
        {
            if (!layer.isTemporary) return layer.intensity;

            float progress = layer.elapsedTime / layer.duration;
            if (progress < 0.2f)
            {
                // Rise
                return layer.intensity * (progress / 0.2f);
            }
            else if (progress > 0.8f)
            {
                // Fall
                return layer.intensity * (1f - (progress - 0.8f) / 0.2f);
            }
            else
            {
                // Sustain
                return layer.intensity;
            }
        }

        private void UpdateBodyIntegration()
        {
            // Update breathing based on emotion
            if (proceduralController != null)
            {
                float breathingSpeed = 1f;
                float breathingAmplitude = 0.02f;

                switch (currentEmotion.primaryEmotion)
                {
                    case EmotionType.Angry:
                        breathingSpeed = 1.5f;
                        breathingAmplitude = 0.03f;
                        break;
                    case EmotionType.Fearful:
                        breathingSpeed = 2f;
                        breathingAmplitude = 0.025f;
                        break;
                    case EmotionType.Sad:
                        breathingSpeed = 0.8f;
                        breathingAmplitude = 0.015f;
                        break;
                    case EmotionType.Calm:
                        breathingSpeed = 0.7f;
                        breathingAmplitude = 0.015f;
                        break;
                }

                proceduralController.SetBreathingParameters(breathingSpeed, breathingAmplitude);
            }

            // Update eye tracking based on emotion
            if (eyeTrackingController != null)
            {
                switch (currentEmotion.primaryEmotion)
                {
                    case EmotionType.Fearful:
                        eyeTrackingController.SetSaccadeParameters(1f, 2f, 40f);
                        break;
                    case EmotionType.Angry:
                        eyeTrackingController.SetSaccadeParameters(3f, 5f, 20f);
                        break;
                    case EmotionType.Sad:
                        eyeTrackingController.SetSaccadeParameters(4f, 6f, 15f);
                        break;
                    default:
                        eyeTrackingController.SetSaccadeParameters(2f, 5f, 30f);
                        break;
                }
            }
        }

        public void SetEmotion(EmotionType emotion, float intensity = 1f, float transitionSpeed = -1f)
        {
            if (emotionTransitionCoroutine != null)
            {
                StopCoroutine(emotionTransitionCoroutine);
            }

            float actualTransitionSpeed = transitionSpeed > 0 ? transitionSpeed : emotionTransitionSpeed;
            emotionTransitionCoroutine = StartCoroutine(EmotionTransitionCoroutine(emotion, intensity, actualTransitionSpeed));
        }

        private IEnumerator EmotionTransitionCoroutine(EmotionType targetEmotionType, float targetIntensity, float speed)
        {
            EmotionType startEmotion = currentEmotion.primaryEmotion;
            float startIntensity = currentEmotion.primaryIntensity;
            float elapsedTime = 0f;
            float duration = 1f / speed;

            while (elapsedTime < duration)
            {
                elapsedTime += Time.deltaTime;
                float t = elapsedTime / duration;
                float easedT = EmotionEasing(t);

                currentEmotion.primaryEmotion = targetEmotionType;
                currentEmotion.primaryIntensity = Mathf.Lerp(startIntensity, targetIntensity, easedT);

                OnEmotionIntensityChanged?.Invoke(targetEmotionType, currentEmotion.primaryIntensity);

                yield return null;
            }

            currentEmotion.primaryEmotion = targetEmotionType;
            currentEmotion.primaryIntensity = targetIntensity;
            OnEmotionChanged?.Invoke(targetEmotionType);

            // Start emotion decay if enabled
            if (enableEmotionDecay)
            {
                StartEmotionDecay();
            }
        }

        private float EmotionEasing(float t)
        {
            // Smooth easing for emotion transitions
            return t < 0.5f ? 2f * t * t : 1f - Mathf.Pow(-2f * t + 2f, 2f) / 2f;
        }

        private void StartEmotionDecay()
        {
            if (emotionDecayCoroutine != null)
            {
                StopCoroutine(emotionDecayCoroutine);
            }

            emotionDecayCoroutine = StartCoroutine(EmotionDecayCoroutine());
        }

        private IEnumerator EmotionDecayCoroutine()
        {
            while (currentEmotion.primaryIntensity > 0.1f)
            {
                currentEmotion.primaryIntensity -= Time.deltaTime * emotionDecayRate;
                currentEmotion.primaryIntensity = Mathf.Max(0.1f, currentEmotion.primaryIntensity);

                OnEmotionIntensityChanged?.Invoke(currentEmotion.primaryEmotion, currentEmotion.primaryIntensity);

                yield return null;
            }
        }

        public void AddEmotionLayer(EmotionType emotion, float intensity, float duration = 0f, bool temporary = true)
        {
            EmotionLayer layer = new EmotionLayer
            {
                emotionType = emotion,
                intensity = intensity,
                duration = duration,
                elapsedTime = 0f,
                isTemporary = temporary,
                isActive = true
            };

            emotionLayers.Add(layer);
            OnEmotionLayerAdded?.Invoke(layer);

            // Trigger corresponding body responses
            if (enableDynamicResponses)
            {
                TriggerEmotionalResponse(emotion, intensity);
            }
        }

        public void RemoveEmotionLayer(EmotionLayer layer)
        {
            layer.isActive = false;
            OnEmotionLayerRemoved?.Invoke(layer);
        }

        private void TriggerEmotionalResponse(EmotionType emotion, float intensity)
        {
            // Trigger gesture response
            if (gestureController != null)
            {
                string emotionName = emotion.ToString();
                gestureController.TriggerEmotionalGesture(emotionName, intensity * responseIntensity);
            }

            // Update micro-expression controller
            if (microExpressionController != null)
            {
                var emotionalState = new MicroExpressionController.EmotionalState();
                switch (emotion)
                {
                    case EmotionType.Happy:
                        emotionalState.happiness = intensity;
                        break;
                    case EmotionType.Sad:
                        emotionalState.sadness = intensity;
                        break;
                    case EmotionType.Angry:
                        emotionalState.anger = intensity;
                        break;
                    case EmotionType.Fearful:
                        emotionalState.fear = intensity;
                        break;
                    case EmotionType.Surprised:
                        emotionalState.surprise = intensity;
                        break;
                }
                microExpressionController.SetEmotionalState(emotionalState);
            }
        }

        private EmotionPreset GetPresetForType(EmotionType type)
        {
            foreach (var preset in emotionPresets)
            {
                if (preset.emotionType == type)
                {
                    return preset;
                }
            }
            return null;
        }

        public void SetSecondaryEmotion(EmotionType emotion, float intensity)
        {
            currentEmotion.secondaryEmotions[emotion] = Mathf.Clamp01(intensity);
        }

        public void RemoveSecondaryEmotion(EmotionType emotion)
        {
            if (currentEmotion.secondaryEmotions.ContainsKey(emotion))
            {
                currentEmotion.secondaryEmotions.Remove(emotion);
            }
        }

        public void ClearSecondaryEmotions()
        {
            currentEmotion.secondaryEmotions.Clear();
        }

        public void SetEmotionTransitionSpeed(float speed)
        {
            emotionTransitionSpeed = Mathf.Clamp(speed, 0.5f, 5f);
        }

        public void SetEmotionDecayRate(float rate)
        {
            emotionDecayRate = Mathf.Clamp(rate, 0.1f, 2f);
        }

        public void SetEmotionBlendingEnabled(bool enabled)
        {
            enableEmotionBlending = enabled;
        }

        public EmotionType GetCurrentEmotion()
        {
            return currentEmotion.primaryEmotion;
        }

        public float GetCurrentEmotionIntensity()
        {
            return currentEmotion.primaryIntensity;
        }

        public void ClearEmotionLayers()
        {
            foreach (var layer in emotionLayers)
            {
                layer.isActive = false;
            }
            emotionLayers.Clear();
        }
    }
}
