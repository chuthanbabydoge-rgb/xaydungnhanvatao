using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

namespace AICompanion.Rendering
{
    /// <summary>
    /// Shadow Controller - follows Single Responsibility Principle
    /// Manages shadow settings and quality for realistic lighting
    /// </summary>
    public class ShadowController : MonoBehaviour
    {
        [Header("Shadow Settings")]
        [SerializeField] private Light shadowLight;
        [SerializeField] private ShadowQuality shadowQuality = ShadowQuality.High;
        [SerializeField] private ShadowResolution shadowResolution = ShadowResolution.High;
        [SerializeField] private float shadowDistance = 50f;
        [SerializeField] private int shadowCascadeCount = 4;

        [Header("Cascade Settings")]
        [SerializeField] private float cascade1Split = 0.067f;
        [SerializeField] private float cascade2Split = 0.2f;
        [SerializeField] private float cascade3Split = 0.467f;

        [Header("Shadow Softness")]
        [SerializeField] private float softShadows = 1f;
        [SerializeField] private bool useContactHardening = true;

        [Header("HDRP Shadow Settings")]
        [SerializeField] private HDAdditionalLightData hdLightData;

        public enum ShadowQuality
        {
            Low,
            Medium,
            High,
            Ultra
        }

        public enum ShadowResolution
        {
            Low,
            Medium,
            High,
            VeryHigh
        }

        private void Start()
        {
            InitializeShadows();
        }

        private void InitializeShadows()
        {
            // Get shadow light
            if (shadowLight == null)
            {
                shadowLight = FindObjectOfType<Light>();
            }

            if (shadowLight == null)
            {
                GameObject lightGO = new GameObject("Shadow Light");
                shadowLight = lightGO.AddComponent<Light>();
                shadowLight.type = LightType.Directional;
            }

            // Configure shadows
            ConfigureShadowSettings();

            // Configure HDRP shadows if available
            #if UNITY_2021_2_OR_NEWER
            ConfigureHDRPShadows();
            #endif
        }

        private void ConfigureShadowSettings()
        {
            if (shadowLight == null) return;

            // Configure basic shadow settings
            shadowLight.shadows = LightShadows.Soft;
            shadowLight.shadowStrength = 1f;
            shadowLight.shadowBias = 0.05f;
            shadowLight.shadowNormalBias = 0.4f;
            shadowLight.shadowNearPlaneOffset = 3f;

            // Configure quality settings
            ApplyShadowQuality();
        }

        #if UNITY_2021_2_OR_NEWER
        private void ConfigureHDRPShadows()
        {
            if (shadowLight == null) return;

            // Get or create HD additional light data
            hdLightData = shadowLight.GetComponent<HDAdditionalLightData>();
            if (hdLightData == null)
            {
                hdLightData = shadowLight.gameObject.AddComponent<HDAdditionalLightData>();
            }

            // Configure HD shadow settings
            hdLightData.enableShadows = true;
            ApplyHDRPShadowQuality();
        }
        #endif

        private void ApplyShadowQuality()
        {
            QualitySettings.shadowDistance = shadowDistance;
            QualitySettings.shadowCascades = shadowCascadeCount;
            QualitySettings.shadowCascade2Split = cascade1Split;
            QualitySettings.shadowCascade4Split = new Vector2(cascade2Split, cascade3Split);

            // Apply resolution
            switch (shadowResolution)
            {
                case ShadowResolution.Low:
                    QualitySettings.shadowResolution = ShadowResolution.Low;
                    break;
                case ShadowResolution.Medium:
                    QualitySettings.shadowResolution = ShadowResolution.Medium;
                    break;
                case ShadowResolution.High:
                    QualitySettings.shadowResolution = ShadowResolution.High;
                    break;
                case ShadowResolution.VeryHigh:
                    QualitySettings.shadowResolution = ShadowResolution.VeryHigh;
                    break;
            }
        }

        #if UNITY_2021_2_OR_NEWER
        private void ApplyHDRPShadowQuality()
        {
            if (hdLightData == null) return;

            // Configure HD shadow quality
            switch (shadowQuality)
            {
                case ShadowQuality.Low:
                    hdLightData.shadowResolution = HDShadowResolution.Low;
                    hdLightData.shadowUpdateMode = ShadowUpdateMode.EveryTwoFrames;
                    break;
                case ShadowQuality.Medium:
                    hdLightData.shadowResolution = HDShadowResolution.Medium;
                    hdLightData.shadowUpdateMode = ShadowUpdateMode.EveryFrame;
                    break;
                case ShadowQuality.High:
                    hdLightData.shadowResolution = HDShadowResolution.High;
                    hdLightData.shadowUpdateMode = ShadowUpdateMode.EveryFrame;
                    break;
                case ShadowQuality.Ultra:
                    hdLightData.shadowResolution = HDShadowResolution.Ultra;
                    hdLightData.shadowUpdateMode = ShadowUpdateMode.EveryFrame;
                    break;
            }

            // Configure contact hardening
            hdLightData.contactShadowLength = useContactHardening ? 0.1f : 0f;
        }
        #endif

        public void SetShadowQuality(ShadowQuality quality)
        {
            shadowQuality = quality;
            ApplyShadowQuality();
            #if UNITY_2021_2_OR_NEWER
            ApplyHDRPShadowQuality();
            #endif
        }

        public void SetShadowResolution(ShadowResolution resolution)
        {
            shadowResolution = resolution;
            ApplyShadowQuality();
        }

        public void SetShadowDistance(float distance)
        {
            shadowDistance = distance;
            QualitySettings.shadowDistance = distance;
        }

        public void SetShadowCascadeCount(int count)
        {
            shadowCascadeCount = Mathf.Clamp(count, 1, 4);
            QualitySettings.shadowCascades = shadowCascadeCount;
        }

        public void SetCascadeSplits(float split1, float split2, float split3)
        {
            cascade1Split = split1;
            cascade2Split = split2;
            cascade3Split = split3;

            QualitySettings.shadowCascade2Split = split1;
            QualitySettings.shadowCascade4Split = new Vector2(split2, split3);
        }

        public void SetShadowSoftness(float softness)
        {
            softShadows = Mathf.Clamp01(softness);
            
            if (shadowLight != null)
            {
                shadowLight.shadowStrength = softShadows;
            }
        }

        public void SetContactHardeningEnabled(bool enabled)
        {
            useContactHardening = enabled;
            #if UNITY_2021_2_OR_NEWER
            if (hdLightData != null)
            {
                hdLightData.contactShadowLength = enabled ? 0.1f : 0f;
            }
            #endif
        }

        public void SetShadowLight(Light light)
        {
            shadowLight = light;
            ConfigureShadowSettings();
            #if UNITY_2021_2_OR_NEWER
            ConfigureHDRPShadows();
            #endif
        }

        public void UpdateShadowSettings()
        {
            ApplyShadowQuality();
            #if UNITY_2021_2_OR_NEWER
            ApplyHDRPShadowQuality();
            #endif
        }
    }
}
