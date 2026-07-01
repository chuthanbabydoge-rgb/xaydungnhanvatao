using UnityEngine;
using System;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Facial Animation Controller - follows Single Responsibility Principle
    /// Manages facial expressions and blend shapes
    /// </summary>
    public class FacialAnimationController : MonoBehaviour
    {
        [Header("Face Components")]
        [SerializeField] private SkinnedMeshRenderer faceRenderer;
        [SerializeField] private Transform headTransform;

        [Header("Blend Shape Configuration")]
        [SerializeField] private List<BlendShapeMapping> blendShapeMappings = new List<BlendShapeMapping>();

        [Header("Expression Presets")]
        [SerializeField] private ExpressionPreset neutralExpression;
        [SerializeField] private ExpressionPreset happyExpression;
        [SerializeField] private ExpressionPreset sadExpression;
        [SerializeField] private ExpressionPreset angryExpression;
        [SerializeField] private ExpressionPreset surprisedExpression;

        [Header("Animation Settings")]
        [SerializeField] private float expressionTransitionSpeed = 2f;
        [SerializeField] private float blinkInterval = 4f;
        [SerializeField] private float blinkDuration = 0.1f;

        private Dictionary<string, int> blendShapeIndices = new Dictionary<string, int>();
        private Dictionary<string, float> currentBlendShapeValues = new Dictionary<string, float>();
        private Dictionary<string, float> targetBlendShapeValues = new Dictionary<string, float>();
        private ExpressionPreset currentExpression;
        private float lastBlinkTime;
        private bool isBlinking;

        public event Action<ExpressionType> OnExpressionChanged;

        public enum ExpressionType
        {
            Neutral,
            Happy,
            Sad,
            Angry,
            Surprised,
            Fear,
            Disgust,
            Love
        }

        [Serializable]
        public class BlendShapeMapping
        {
            public string blendShapeName;
            public string mappedName;
            public float defaultValue = 0f;
        }

        [Serializable]
        public class ExpressionPreset
        {
            public ExpressionType expressionType;
            public List<BlendShapeValue> blendShapeValues = new List<BlendShapeValue>();
        }

        [Serializable]
        public class BlendShapeValue
        {
            public string blendShapeName;
            public float value;
        }

        private void Start()
        {
            InitializeBlendShapes();
            SetExpression(neutralExpression);
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
                currentBlendShapeValues[blendShapeName] = 0f;
                targetBlendShapeValues[blendShapeName] = 0f;
            }

            // Apply mappings
            foreach (var mapping in blendShapeMappings)
            {
                if (blendShapeIndices.ContainsKey(mapping.blendShapeName))
                {
                    currentBlendShapeValues[mapping.mappedName] = mapping.defaultValue;
                    targetBlendShapeValues[mapping.mappedName] = mapping.defaultValue;
                }
            }
        }

        private void Update()
        {
            UpdateBlendShapes();
            HandleBlinking();
        }

        private void UpdateBlendShapes()
        {
            if (faceRenderer == null) return;

            // Smoothly interpolate blend shape values
            foreach (var kvp in targetBlendShapeValues)
            {
                string blendShapeName = kvp.Key;
                float targetValue = kvp.Value;

                if (currentBlendShapeValues.ContainsKey(blendShapeName))
                {
                    float currentValue = currentBlendShapeValues[blendShapeName];
                    float newValue = Mathf.Lerp(
                        currentValue,
                        targetValue,
                        Time.deltaTime * expressionTransitionSpeed
                    );

                    currentBlendShapeValues[blendShapeName] = newValue;

                    // Apply to renderer
                    if (blendShapeIndices.ContainsKey(blendShapeName))
                    {
                        int index = blendShapeIndices[blendShapeName];
                        faceRenderer.SetBlendShapeWeight(index, newValue * 100f);
                    }
                }
            }
        }

        private void HandleBlinking()
        {
            if (Time.time - lastBlinkTime > blinkInterval && !isBlinking)
            {
                StartCoroutine(BlinkCoroutine());
            }
        }

        private System.Collections.IEnumerator BlinkCoroutine()
        {
            isBlinking = true;
            lastBlinkTime = Time.time;

            // Close eyes
            SetBlendShapeValue("EyesClosed", 1f);
            yield return new WaitForSeconds(blinkDuration);

            // Open eyes
            SetBlendShapeValue("EyesClosed", 0f);
            yield return new WaitForSeconds(blinkDuration);

            isBlinking = false;
        }

        public void SetExpression(ExpressionPreset preset)
        {
            if (preset == null) return;

            currentExpression = preset;

            // Set target blend shape values
            foreach (var blendShapeValue in preset.blendShapeValues)
            {
                SetBlendShapeValue(blendShapeValue.blendShapeName, blendShapeValue.value);
            }

            OnExpressionChanged?.Invoke(preset.expressionType);
        }

        public void SetExpression(ExpressionType expressionType)
        {
            ExpressionPreset preset = GetExpressionPreset(expressionType);
            if (preset != null)
            {
                SetExpression(preset);
            }
        }

        public void SetBlendShapeValue(string blendShapeName, float value)
        {
            // Check mapping
            string mappedName = blendShapeName;
            foreach (var mapping in blendShapeMappings)
            {
                if (mapping.mappedName == blendShapeName)
                {
                    mappedName = mapping.blendShapeName;
                    break;
                }
            }

            if (targetBlendShapeValues.ContainsKey(mappedName))
            {
                targetBlendShapeValues[mappedName] = Mathf.Clamp01(value);
            }
        }

        public float GetBlendShapeValue(string blendShapeName)
        {
            if (currentBlendShapeValues.ContainsKey(blendShapeName))
            {
                return currentBlendShapeValues[blendShapeName];
            }
            return 0f;
        }

        private ExpressionPreset GetExpressionPreset(ExpressionType expressionType)
        {
            switch (expressionType)
            {
                case ExpressionType.Neutral:
                    return neutralExpression;
                case ExpressionType.Happy:
                    return happyExpression;
                case ExpressionType.Sad:
                    return sadExpression;
                case ExpressionType.Angry:
                    return angryExpression;
                case ExpressionType.Surprised:
                    return surprisedExpression;
                default:
                    return neutralExpression;
            }
        }

        public void SetFaceRenderer(SkinnedMeshRenderer renderer)
        {
            faceRenderer = renderer;
            InitializeBlendShapes();
        }

        public void AddBlendShapeMapping(string blendShapeName, string mappedName, float defaultValue = 0f)
        {
            var mapping = new BlendShapeMapping
            {
                blendShapeName = blendShapeName,
                mappedName = mappedName,
                defaultValue = defaultValue
            };
            blendShapeMappings.Add(mapping);
        }

        public void SetExpressionTransitionSpeed(float speed)
        {
            expressionTransitionSpeed = speed;
        }

        public void SetBlinkParameters(float interval, float duration)
        {
            blinkInterval = interval;
            blinkDuration = duration;
        }
    }
}
