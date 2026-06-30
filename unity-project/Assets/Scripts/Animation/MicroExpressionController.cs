using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Micro Expression Controller - follows Single Responsibility Principle
    /// Manages subtle facial micro-expressions for emotional realism
    /// </summary>
    public class MicroExpressionController : MonoBehaviour
    {
        [Header("Face Components")]
        [SerializeField] private SkinnedMeshRenderer faceRenderer;
        [SerializeField] private FacialAnimationController facialController;

        [Header("Micro Expression Settings")]
        [SerializeField] private bool enableMicroExpressions = true;
        [SerializeField] private float expressionIntensity = 0.3f;
        [SerializeField] private float expressionDuration = 0.5f;
        [SerializeField] private float expressionInterval = 2f;

        [Header("Expression Types")]
        [SerializeField] private List<MicroExpressionPreset> microExpressionPresets = new List<MicroExpressionPreset>();

        [Header("Procedural Generation")]
        [SerializeField] private bool enableProceduralExpressions = true;
        [SerializeField] private float proceduralExpressionChance = 0.3f;
        [SerializeField] private float expressionComplexity = 0.5f;

        [Header("Emotional Context")]
        [SerializeField] private EmotionalState currentEmotionalState;
        [SerializeField] private float emotionalInfluence = 0.7f;

        [Header("Subtle Movements")]
        [SerializeField] private bool enableSubtleMuscleMovements = true;
        [SerializeField] private float muscleMovementSpeed = 2f;
        [SerializeField] private float muscleMovementAmplitude = 0.05f;

        private Dictionary<string, int> blendShapeIndices = new Dictionary<string, int>();
        private Dictionary<string, float> currentMicroValues = new Dictionary<string, float>();
        private Dictionary<string, float> targetMicroValues = new Dictionary<string, float>();
        private List<MicroExpression> activeExpressions = new List<MicroExpression>();
        private Coroutine expressionCoroutine;
        private Coroutine proceduralCoroutine;
        private float lastExpressionTime;

        public event Action<MicroExpressionType> OnMicroExpressionTriggered;
        public event Action<EmotionalState> OnEmotionalStateChanged;

        public enum MicroExpressionType
        {
            EyebrowRaise,
            EyebrowFurrow,
            EyeSquint,
            EyeWiden,
            NoseWrinkle,
            LipCornerUp,
            LipCornerDown,
            LipPress,
            JawClench,
            CheekRaise,
            ForeheadRaise,
            ChinRaise
        }

        [Serializable]
        public class MicroExpressionPreset
        {
            public MicroExpressionType expressionType;
            public List<BlendShapeInfluence> blendShapeInfluences = new List<BlendShapeInfluence>();
            public float defaultIntensity = 0.5f;
            public float defaultDuration = 0.5f;
        }

        [Serializable]
        public class BlendShapeInfluence
        {
            public string blendShapeName;
            public float weight = 1f;
        }

        [Serializable]
        public class EmotionalState
        {
            public float happiness = 0.5f;
            public float sadness = 0f;
            public float anger = 0f;
            public float fear = 0f;
            public float surprise = 0f;
            public float disgust = 0f;
            public float contempt = 0f;
        }

        private class MicroExpression
        {
            public MicroExpressionType type;
            public float intensity;
            public float duration;
            public float elapsedTime;
            public List<BlendShapeInfluence> influences;
            public bool isActive;
        }

        private void Start()
        {
            InitializeBlendShapes();
            InitializePresets();
            StartProceduralGeneration();
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
                currentMicroValues[blendShapeName] = 0f;
                targetMicroValues[blendShapeName] = 0f;
            }
        }

        private void InitializePresets()
        {
            // Initialize default presets if none are defined
            if (microExpressionPresets.Count == 0)
            {
                CreateDefaultPresets();
            }
        }

        private void CreateDefaultPresets()
        {
            // Eyebrow Raise
            microExpressionPresets.Add(new MicroExpressionPreset
            {
                expressionType = MicroExpressionType.EyebrowRaise,
                blendShapeInfluences = new List<BlendShapeInfluence>
                {
                    new BlendShapeInfluence { blendShapeName = "BrowOuterUp_L", weight = 1f },
                    new BlendShapeInfluence { blendShapeName = "BrowOuterUp_R", weight = 1f }
                },
                defaultIntensity = 0.4f,
                defaultDuration = 0.3f
            });

            // Eyebrow Furrow
            microExpressionPresets.Add(new MicroExpressionPreset
            {
                expressionType = MicroExpressionType.EyebrowFurrow,
                blendShapeInfluences = new List<BlendShapeInfluence>
                {
                    new BlendShapeInfluence { blendShapeName = "BrowDown_L", weight = 1f },
                    new BlendShapeInfluence { blendShapeName = "BrowDown_R", weight = 1f }
                },
                defaultIntensity = 0.3f,
                defaultDuration = 0.4f
            });

            // Eye Squint
            microExpressionPresets.Add(new MicroExpressionPreset
            {
                expressionType = MicroExpressionType.EyeSquint,
                blendShapeInfluences = new List<BlendShapeInfluence>
                {
                    new BlendShapeInfluence { blendShapeName = "EyeSquint_L", weight = 1f },
                    new BlendShapeInfluence { blendShapeName = "EyeSquint_R", weight = 1f }
                },
                defaultIntensity = 0.5f,
                defaultDuration = 0.2f
            });

            // Lip Corner Up (Smile)
            microExpressionPresets.Add(new MicroExpressionPreset
            {
                expressionType = MicroExpressionType.LipCornerUp,
                blendShapeInfluences = new List<BlendShapeInfluence>
                {
                    new BlendShapeInfluence { blendShapeName = "MouthSmile_L", weight = 1f },
                    new BlendShapeInfluence { blendShapeName = "MouthSmile_R", weight = 1f }
                },
                defaultIntensity = 0.3f,
                defaultDuration = 0.4f
            });

            // Lip Corner Down (Frown)
            microExpressionPresets.Add(new MicroExpressionPreset
            {
                expressionType = MicroExpressionType.LipCornerDown,
                blendShapeInfluences = new List<BlendShapeInfluence>
                {
                    new BlendShapeInfluence { blendShapeName = "MouthFrown_L", weight = 1f },
                    new BlendShapeInfluence { blendShapeName = "MouthFrown_R", weight = 1f }
                },
                defaultIntensity = 0.3f,
                defaultDuration = 0.3f
            });
        }

        private void StartProceduralGeneration()
        {
            if (enableProceduralExpressions)
            {
                proceduralCoroutine = StartCoroutine(ProceduralExpressionCoroutine());
            }
        }

        private void Update()
        {
            UpdateActiveExpressions();
            UpdateMicroBlendShapes();
            UpdateSubtleMovements();
        }

        private void UpdateActiveExpressions()
        {
            for (int i = activeExpressions.Count - 1; i >= 0; i--)
            {
                MicroExpression expression = activeExpressions[i];
                expression.elapsedTime += Time.deltaTime;

                if (expression.elapsedTime >= expression.duration)
                {
                    // Remove completed expression
                    RemoveExpression(expression);
                    activeExpressions.RemoveAt(i);
                }
            }
        }

        private void UpdateMicroBlendShapes()
        {
            if (faceRenderer == null) return;

            // Calculate target values from active expressions
            foreach (var kvp in targetMicroValues)
            {
                targetMicroValues[kvp.Key] = 0f;
            }

            foreach (var expression in activeExpressions)
            {
                if (!expression.isActive) continue;

                float progress = expression.elapsedTime / expression.duration;
                float intensity = CalculateExpressionIntensity(progress, expression.intensity);

                foreach (var influence in expression.influences)
                {
                    string blendShapeName = influence.blendShapeName;
                    float weight = influence.weight * intensity * expressionIntensity;

                    if (targetMicroValues.ContainsKey(blendShapeName))
                    {
                        targetMicroValues[blendShapeName] = Mathf.Max(
                            targetMicroValues[blendShapeName],
                            weight
                        );
                    }
                }
            }

            // Apply emotional context
            ApplyEmotionalContext();

            // Smoothly interpolate to target values
            foreach (var kvp in targetMicroValues)
            {
                string blendShapeName = kvp.Key;
                float targetValue = kvp.Value;

                if (currentMicroValues.ContainsKey(blendShapeName))
                {
                    float currentValue = currentMicroValues[blendShapeName];
                    float newValue = Mathf.Lerp(
                        currentValue,
                        targetValue,
                        Time.deltaTime * 10f
                    );

                    currentMicroValues[blendShapeName] = newValue;

                    // Apply to renderer
                    if (blendShapeIndices.ContainsKey(blendShapeName))
                    {
                        int index = blendShapeIndices[blendShapeName];
                        faceRenderer.SetBlendShapeWeight(index, newValue * 100f);
                    }
                }
            }
        }

        private float CalculateExpressionIntensity(float progress, float baseIntensity)
        {
            // Apply easing for natural expression rise and fall
            if (progress < 0.2f)
            {
                // Rise
                return baseIntensity * (progress / 0.2f);
            }
            else if (progress > 0.8f)
            {
                // Fall
                return baseIntensity * (1f - (progress - 0.8f) / 0.2f);
            }
            else
            {
                // Sustain
                return baseIntensity;
            }
        }

        private void ApplyEmotionalContext()
        {
            // Apply emotional state influences
            if (currentEmotionalState.happiness > 0.5f)
            {
                AddEmotionalInfluence("MouthSmile_L", currentEmotionalState.happiness * 0.2f * emotionalInfluence);
                AddEmotionalInfluence("MouthSmile_R", currentEmotionalState.happiness * 0.2f * emotionalInfluence);
            }

            if (currentEmotionalState.sadness > 0.5f)
            {
                AddEmotionalInfluence("MouthFrown_L", currentEmotionalState.sadness * 0.15f * emotionalInfluence);
                AddEmotionalInfluence("MouthFrown_R", currentEmotionalState.sadness * 0.15f * emotionalInfluence);
                AddEmotionalInfluence("BrowDown_L", currentEmotionalState.sadness * 0.1f * emotionalInfluence);
                AddEmotionalInfluence("BrowDown_R", currentEmotionalState.sadness * 0.1f * emotionalInfluence);
            }

            if (currentEmotionalState.anger > 0.5f)
            {
                AddEmotionalInfluence("BrowDown_L", currentEmotionalState.anger * 0.2f * emotionalInfluence);
                AddEmotionalInfluence("BrowDown_R", currentEmotionalState.anger * 0.2f * emotionalInfluence);
                AddEmotionalInfluence("EyeSquint_L", currentEmotionalState.anger * 0.15f * emotionalInfluence);
                AddEmotionalInfluence("EyeSquint_R", currentEmotionalState.anger * 0.15f * emotionalInfluence);
            }

            if (currentEmotionalState.surprise > 0.5f)
            {
                AddEmotionalInfluence("BrowOuterUp_L", currentEmotionalState.surprise * 0.25f * emotionalInfluence);
                AddEmotionalInfluence("BrowOuterUp_R", currentEmotionalState.surprise * 0.25f * emotionalInfluence);
                AddEmotionalInfluence("EyeWide_L", currentEmotionalState.surprise * 0.2f * emotionalInfluence);
                AddEmotionalInfluence("EyeWide_R", currentEmotionalState.surprise * 0.2f * emotionalInfluence);
            }
        }

        private void AddEmotionalInfluence(string blendShapeName, float value)
        {
            if (targetMicroValues.ContainsKey(blendShapeName))
            {
                targetMicroValues[blendShapeName] = Mathf.Max(
                    targetMicroValues[blendShapeName],
                    value
                );
            }
        }

        private void UpdateSubtleMovements()
        {
            if (!enableSubtleMuscleMovements) return;

            // Add subtle random movements to simulate live tissue
            float time = Time.time;
            foreach (var kvp in currentMicroValues)
            {
                string blendShapeName = kvp.Key;
                float currentValue = kvp.Value;

                if (currentValue > 0.01f)
                {
                    float movement = Mathf.PerlinNoise(
                        time * muscleMovementSpeed,
                        blendShapeName.GetHashCode()
                    ) * muscleMovementAmplitude * currentValue;

                    if (blendShapeIndices.ContainsKey(blendShapeName))
                    {
                        int index = blendShapeIndices[blendShapeName];
                        float baseWeight = faceRenderer.GetBlendShapeWeight(index);
                        faceRenderer.SetBlendShapeWeight(index, baseWeight + movement);
                    }
                }
            }
        }

        private IEnumerator ProceduralExpressionCoroutine()
        {
            while (enableProceduralExpressions)
            {
                if (Time.time - lastExpressionTime > expressionInterval)
                {
                    if (Random.value < proceduralExpressionChance)
                    {
                        TriggerProceduralExpression();
                    }
                    lastExpressionTime = Time.time;
                }

                yield return null;
            }
        }

        private void TriggerProceduralExpression()
        {
            // Select expression based on emotional context
            MicroExpressionType expressionType = SelectContextualExpression();
            MicroExpressionPreset preset = GetPresetForType(expressionType);

            if (preset != null)
            {
                float intensity = preset.defaultIntensity * (0.8f + Random.value * 0.4f);
                float duration = preset.defaultDuration * (0.8f + Random.value * 0.4f);

                TriggerMicroExpression(expressionType, intensity, duration);
            }
        }

        private MicroExpressionType SelectContextualExpression()
        {
            // Select expression based on current emotional state
            float randomValue = Random.value;

            if (currentEmotionalState.happiness > 0.6f && randomValue < 0.5f)
            {
                return MicroExpressionType.LipCornerUp;
            }
            else if (currentEmotionalState.sadness > 0.6f && randomValue < 0.5f)
            {
                return MicroExpressionType.LipCornerDown;
            }
            else if (currentEmotionalState.anger > 0.6f && randomValue < 0.5f)
            {
                return MicroExpressionType.EyebrowFurrow;
            }
            else if (currentEmotionalState.surprise > 0.6f && randomValue < 0.5f)
            {
                return MicroExpressionType.EyeWiden;
            }

            // Random selection
            return (MicroExpressionType)Random.Range(0, System.Enum.GetValues(typeof(MicroExpressionType)).Length);
        }

        private MicroExpressionPreset GetPresetForType(MicroExpressionType type)
        {
            foreach (var preset in microExpressionPresets)
            {
                if (preset.expressionType == type)
                {
                    return preset;
                }
            }
            return null;
        }

        public void TriggerMicroExpression(MicroExpressionType type, float intensity = 0.5f, float duration = 0.5f)
        {
            MicroExpressionPreset preset = GetPresetForType(type);
            if (preset == null) return;

            MicroExpression expression = new MicroExpression
            {
                type = type,
                intensity = intensity,
                duration = duration,
                elapsedTime = 0f,
                influences = preset.blendShapeInfluences,
                isActive = true
            };

            activeExpressions.Add(expression);
            OnMicroExpressionTriggered?.Invoke(type);
        }

        private void RemoveExpression(MicroExpression expression)
        {
            expression.isActive = false;
        }

        public void SetEmotionalState(EmotionalState state)
        {
            currentEmotionalState = state;
            OnEmotionalStateChanged?.Invoke(state);
        }

        public void SetEmotionalValue(string emotion, float value)
        {
            switch (emotion.ToLower())
            {
                case "happiness":
                    currentEmotionalState.happiness = Mathf.Clamp01(value);
                    break;
                case "sadness":
                    currentEmotionalState.sadness = Mathf.Clamp01(value);
                    break;
                case "anger":
                    currentEmotionalState.anger = Mathf.Clamp01(value);
                    break;
                case "fear":
                    currentEmotionalState.fear = Mathf.Clamp01(value);
                    break;
                case "surprise":
                    currentEmotionalState.surprise = Mathf.Clamp01(value);
                    break;
                case "disgust":
                    currentEmotionalState.disgust = Mathf.Clamp01(value);
                    break;
                case "contempt":
                    currentEmotionalState.contempt = Mathf.Clamp01(value);
                    break;
            }
        }

        public void SetExpressionIntensity(float intensity)
        {
            expressionIntensity = Mathf.Clamp01(intensity);
        }

        public void SetProceduralExpressionsEnabled(bool enabled)
        {
            enableProceduralExpressions = enabled;

            if (enabled && proceduralCoroutine == null)
            {
                proceduralCoroutine = StartCoroutine(ProceduralExpressionCoroutine());
            }
            else if (!enabled && proceduralCoroutine != null)
            {
                StopCoroutine(proceduralCoroutine);
                proceduralCoroutine = null;
            }
        }

        public void ClearActiveExpressions()
        {
            foreach (var expression in activeExpressions)
            {
                expression.isActive = false;
            }
            activeExpressions.Clear();
        }
    }
}
