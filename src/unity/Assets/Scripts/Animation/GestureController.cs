using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Gesture Controller - follows Single Responsibility Principle
    /// Manages procedural hand and body gestures
    /// </summary>
    public class GestureController : MonoBehaviour
    {
        [Header("Hand Components")]
        [SerializeField] private Transform leftHand;
        [SerializeField] private Transform rightHand;
        [SerializeField] private Transform leftForearm;
        [SerializeField] private Transform rightForearm;
        [SerializeField] private Transform leftUpperArm;
        [SerializeField] private Transform upperArm;

        [Header("Gesture Settings")]
        [SerializeField] private float gestureSpeed = 3f;
        [SerializeField] private float gestureSmoothness = 0.2f;
        [SerializeField] private bool enableProceduralGestures = true;
        [SerializeField] private float gestureInterval = 4f;

        [Header("Gesture Types")]
        [SerializeField] private List<GesturePreset> gesturePresets = new List<GesturePreset>();

        [Header("Idle Gestures")]
        [SerializeField] private bool enableIdleGestures = true;
        [SerializeField] private float idleGestureChance = 0.3f;
        [SerializeField] private float idleGestureVariety = 0.5f;

        [Header("Communication Gestures")]
        [SerializeField] private bool enableCommunicationGestures = true;
        [SerializeField] private float speechGestureChance = 0.5f;

        [Header("Emotional Gestures")]
        [SerializeField] private bool enableEmotionalGestures = true;
        [SerializeField] private float emotionalGestureIntensity = 0.7f;

        [Header("Procedural Animation")]
        [SerializeField] private bool enableFingerAnimation = true;
        [SerializeField] private float fingerAnimationSpeed = 2f;
        [SerializeField] private float fingerCurlAmount = 0.3f;

        private Dictionary<string, Transform> boneMap = new Dictionary<string, Transform>();
        private Dictionary<string, Vector3> initialPositions = new Dictionary<string, Vector3>();
        private Dictionary<string, Quaternion> initialRotations = new Dictionary<string, Quaternion>();
        private List<ActiveGesture> activeGestures = new List<ActiveGesture>();
        private Coroutine gestureCoroutine;
        private Coroutine proceduralCoroutine;
        private float lastGestureTime;

        public event Action<GestureType> OnGestureStarted;
        public event Action<GestureType> OnGestureCompleted;

        public enum GestureType
        {
            Wave,
            Point,
            ThumbsUp,
            OpenHand,
            Fist,
            PeaceSign,
            Shrug,
            CrossArms,
            HandsOnHips,
            ScratchHead,
            RubChin,
            FacePalm,
            CountOnFingers,
            Beckon,
            Stop,
            Thinking,
            IdleHandMovement
        }

        [Serializable]
        public class GesturePreset
        {
            public GestureType gestureType;
            public List<BoneTransform> boneTransforms = new List<BoneTransform>();
            public float defaultDuration = 1f;
            public float defaultIntensity = 1f;
        }

        [Serializable]
        public class BoneTransform
        {
            public string boneName;
            public Vector3 positionOffset;
            public Vector3 rotationOffset;
            public float weight = 1f;
        }

        private class ActiveGesture
        {
            public GestureType type;
            public float duration;
            public float intensity;
            public float elapsedTime;
            public List<BoneTransform> transforms;
            public bool isActive;
            public bool isLooping;
        }

        private void Start()
        {
            InitializeBones();
            InitializePresets();
            StartProceduralGestures();
        }

        private void InitializeBones()
        {
            // Map bones
            if (leftHand != null)
            {
                boneMap["LeftHand"] = leftHand;
                initialPositions["LeftHand"] = leftHand.localPosition;
                initialRotations["LeftHand"] = leftHand.localRotation;
            }

            if (rightHand != null)
            {
                boneMap["RightHand"] = rightHand;
                initialPositions["RightHand"] = rightHand.localPosition;
                initialRotations["RightHand"] = rightHand.localRotation;
            }

            if (leftForearm != null)
            {
                boneMap["LeftForearm"] = leftForearm;
                initialPositions["LeftForearm"] = leftForearm.localPosition;
                initialRotations["LeftForearm"] = leftForearm.localRotation;
            }

            if (rightForearm != null)
            {
                boneMap["RightForearm"] = rightForearm;
                initialPositions["RightForearm"] = rightForearm.localPosition;
                initialRotations["RightForearm"] = rightForearm.localRotation;
            }

            if (leftUpperArm != null)
            {
                boneMap["LeftUpperArm"] = leftUpperArm;
                initialPositions["LeftUpperArm"] = leftUpperArm.localPosition;
                initialRotations["LeftUpperArm"] = leftUpperArm.localRotation;
            }

            if (upperArm != null)
            {
                boneMap["UpperArm"] = upperArm;
                initialPositions["UpperArm"] = upperArm.localPosition;
                initialRotations["UpperArm"] = upperArm.localRotation;
            }
        }

        private void InitializePresets()
        {
            // Create default procedural gestures if none are defined
            if (gesturePresets.Count == 0)
            {
                CreateDefaultPresets();
            }
        }

        private void CreateDefaultPresets()
        {
            // Wave gesture
            gesturePresets.Add(new GesturePreset
            {
                gestureType = GestureType.Wave,
                boneTransforms = new List<BoneTransform>
                {
                    new BoneTransform
                    {
                        boneName = "RightHand",
                        rotationOffset = new Vector3(0, 0, 45),
                        weight = 1f
                    },
                    new BoneTransform
                    {
                        boneName = "RightForearm",
                        rotationOffset = new Vector3(-30, 0, 0),
                        weight = 1f
                    }
                },
                defaultDuration = 1.5f,
                defaultIntensity = 1f
            });

            // Point gesture
            gesturePresets.Add(new GesturePreset
            {
                gestureType = GestureType.Point,
                boneTransforms = new List<BoneTransform>
                {
                    new BoneTransform
                    {
                        boneName = "RightHand",
                        rotationOffset = new Vector3(-20, 0, 0),
                        weight = 1f
                    },
                    new BoneTransform
                    {
                        boneName = "RightForearm",
                        rotationOffset = new Vector3(-45, 0, 0),
                        weight = 1f
                    }
                },
                defaultDuration = 1f,
                defaultIntensity = 1f
            });

            // Open hand gesture
            gesturePresets.Add(new GesturePreset
            {
                gestureType = GestureType.OpenHand,
                boneTransforms = new List<BoneTransform>
                {
                    new BoneTransform
                    {
                        boneName = "LeftHand",
                        rotationOffset = new Vector3(0, 0, 0),
                        weight = 1f
                    },
                    new BoneTransform
                    {
                        boneName = "RightHand",
                        rotationOffset = new Vector3(0, 0, 0),
                        weight = 1f
                    }
                },
                defaultDuration = 0.5f,
                defaultIntensity = 1f
            });

            // Thinking gesture
            gesturePresets.Add(new GesturePreset
            {
                gestureType = GestureType.Thinking,
                boneTransforms = new List<BoneTransform>
                {
                    new BoneTransform
                    {
                        boneName = "RightHand",
                        positionOffset = new Vector3(0.3f, 0.4f, 0.2f),
                        rotationOffset = new Vector3(-45, 30, 0),
                        weight = 1f
                    },
                    new BoneTransform
                    {
                        boneName = "RightForearm",
                        rotationOffset = new Vector3(-60, 45, 0),
                        weight = 1f
                    }
                },
                defaultDuration = 2f,
                defaultIntensity = 1f
            });
        }

        private void StartProceduralGestures()
        {
            if (enableProceduralGestures)
            {
                proceduralCoroutine = StartCoroutine(ProceduralGestureCoroutine());
            }
        }

        private void Update()
        {
            UpdateActiveGestures();
            ApplyGestureTransforms();
            UpdateFingerAnimation();
        }

        private void UpdateActiveGestures()
        {
            for (int i = activeGestures.Count - 1; i >= 0; i--)
            {
                ActiveGesture gesture = activeGestures[i];
                gesture.elapsedTime += Time.deltaTime;

                if (gesture.elapsedTime >= gesture.duration && !gesture.isLooping)
                {
                    // Remove completed gesture
                    gesture.isActive = false;
                    activeGestures.RemoveAt(i);
                    OnGestureCompleted?.Invoke(gesture.type);
                }
            }
        }

        private void ApplyGestureTransforms()
        {
            // Reset all bones to initial positions
            foreach (var kvp in initialPositions)
            {
                if (boneMap.ContainsKey(kvp.Key))
                {
                    Transform bone = boneMap[kvp.Key];
                    bone.localPosition = kvp.Value;
                    bone.localRotation = initialRotations[kvp.Key];
                }
            }

            // Apply active gesture transforms
            foreach (var gesture in activeGestures)
            {
                if (!gesture.isActive) continue;

                float progress = gesture.elapsedTime / gesture.duration;
                float intensity = CalculateGestureIntensity(progress, gesture.intensity);

                foreach (var boneTransform in gesture.transforms)
                {
                    if (boneMap.ContainsKey(boneTransform.boneName))
                    {
                        Transform bone = boneMap[boneTransform.boneName];
                        float weight = boneTransform.weight * intensity;

                        // Apply position offset
                        if (boneTransform.positionOffset != Vector3.zero)
                        {
                            bone.localPosition += boneTransform.positionOffset * weight;
                        }

                        // Apply rotation offset
                        if (boneTransform.rotationOffset != Vector3.zero)
                        {
                            Quaternion rotationOffset = Quaternion.Euler(boneTransform.rotationOffset);
                            bone.localRotation = Quaternion.Slerp(
                                bone.localRotation,
                                initialRotations[boneTransform.boneName] * rotationOffset,
                                weight
                            );
                        }
                    }
                }
            }
        }

        private float CalculateGestureIntensity(float progress, float baseIntensity)
        {
            // Apply easing for natural gesture rise and fall
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

        private void UpdateFingerAnimation()
        {
            if (!enableFingerAnimation) return;

            // Add subtle finger movements for realism
            float time = Time.time;
            foreach (var kvp in boneMap)
            {
                Transform bone = kvp.Value;
                string boneName = kvp.Key;

                if (boneName.Contains("Hand"))
                {
                    // Add subtle finger curling animation
                    float fingerCurl = Mathf.Sin(time * fingerAnimationSpeed) * fingerCurlAmount;
                    Vector3 fingerRotation = new Vector3(fingerCurl, 0, 0);
                    bone.localRotation *= Quaternion.Euler(fingerRotation * Time.deltaTime);
                }
            }
        }

        private IEnumerator ProceduralGestureCoroutine()
        {
            while (enableProceduralGestures)
            {
                if (Time.time - lastGestureTime > gestureInterval)
                {
                    if (enableIdleGestures && Random.value < idleGestureChance)
                    {
                        TriggerIdleGesture();
                    }
                    lastGestureTime = Time.time;
                }

                yield return null;
            }
        }

        private void TriggerIdleGesture()
        {
            GestureType gestureType = SelectIdleGesture();
            GesturePreset preset = GetPresetForType(gestureType);

            if (preset != null)
            {
                float intensity = preset.defaultIntensity * (0.8f + Random.value * 0.4f);
                float duration = preset.defaultDuration * (0.8f + Random.value * 0.4f);

                TriggerGesture(gestureType, intensity, duration);
            }
        }

        private GestureType SelectIdleGesture()
        {
            // Select from idle-appropriate gestures
            GestureType[] idleGestures = new GestureType[]
            {
                GestureType.IdleHandMovement,
                GestureType.OpenHand,
                GestureType.Thinking
            };

            return idleGestures[Random.Range(0, idleGestures.Length)];
        }

        private GesturePreset GetPresetForType(GestureType type)
        {
            foreach (var preset in gesturePresets)
            {
                if (preset.gestureType == type)
                {
                    return preset;
                }
            }
            return null;
        }

        public void TriggerGesture(GestureType type, float intensity = 1f, float duration = 1f, bool loop = false)
        {
            GesturePreset preset = GetPresetForType(type);
            if (preset == null) return;

            ActiveGesture gesture = new ActiveGesture
            {
                type = type,
                duration = duration,
                intensity = intensity,
                elapsedTime = 0f,
                transforms = preset.boneTransforms,
                isActive = true,
                isLooping = loop
            };

            activeGestures.Add(gesture);
            OnGestureStarted?.Invoke(type);
        }

        public void TriggerCommunicationGesture(string speechContext)
        {
            if (!enableCommunicationGestures) return;

            GestureType gestureType = SelectCommunicationGesture(speechContext);
            GesturePreset preset = GetPresetForType(gestureType);

            if (preset != null && Random.value < speechGestureChance)
            {
                float intensity = preset.defaultIntensity * emotionalGestureIntensity;
                float duration = preset.defaultDuration;

                TriggerGesture(gestureType, intensity, duration);
            }
        }

        private GestureType SelectCommunicationGesture(string context)
        {
            // Select gesture based on speech context
            if (context.ToLower().Contains("hello") || context.ToLower().Contains("hi"))
            {
                return GestureType.Wave;
            }
            else if (context.ToLower().Contains("look") || context.ToLower().Contains("see"))
            {
                return GestureType.Point;
            }
            else if (context.ToLower().Contains("think") || context.ToLower().Contains("wonder"))
            {
                return GestureType.Thinking;
            }
            else if (context.ToLower().Contains("stop") || context.ToLower().Contains("wait"))
            {
                return GestureType.Stop;
            }
            else if (context.ToLower().Contains("good") || context.ToLower().Contains("great"))
            {
                return GestureType.ThumbsUp;
            }

            // Random selection
            return (GestureType)Random.Range(0, System.Enum.GetValues(typeof(GestureType)).Length);
        }

        public void TriggerEmotionalGesture(string emotion, float intensity)
        {
            if (!enableEmotionalGestures) return;

            GestureType gestureType = SelectEmotionalGesture(emotion);
            GesturePreset preset = GetPresetForType(gestureType);

            if (preset != null)
            {
                float gestureIntensity = preset.defaultIntensity * intensity * emotionalGestureIntensity;
                float duration = preset.defaultDuration;

                TriggerGesture(gestureType, gestureIntensity, duration);
            }
        }

        private GestureType SelectEmotionalGesture(string emotion)
        {
            switch (emotion.ToLower())
            {
                case "happiness":
                    return GestureType.ThumbsUp;
                case "sadness":
                    return GestureType.Shrug;
                case "anger":
                    return GestureType.Fist;
                case "surprise":
                    return GestureType.OpenHand;
                case "thinking":
                    return GestureType.Thinking;
                default:
                    return GestureType.IdleHandMovement;
            }
        }

        public void SetGestureSpeed(float speed)
        {
            gestureSpeed = Mathf.Clamp(speed, 1f, 10f);
        }

        public void SetGestureInterval(float interval)
        {
            gestureInterval = Mathf.Clamp(interval, 1f, 10f);
        }

        public void SetProceduralGesturesEnabled(bool enabled)
        {
            enableProceduralGestures = enabled;

            if (enabled && proceduralCoroutine == null)
            {
                proceduralCoroutine = StartCoroutine(ProceduralGestureCoroutine());
            }
            else if (!enabled && proceduralCoroutine != null)
            {
                StopCoroutine(proceduralCoroutine);
                proceduralCoroutine = null;
            }
        }

        public void ClearActiveGestures()
        {
            foreach (var gesture in activeGestures)
            {
                gesture.isActive = false;
            }
            activeGestures.Clear();
        }

        public bool IsGestureActive(GestureType type)
        {
            foreach (var gesture in activeGestures)
            {
                if (gesture.type == type && gesture.isActive)
                {
                    return true;
                }
            }
            return false;
        }
    }
}
