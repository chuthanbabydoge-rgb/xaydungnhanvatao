using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;
using System;

namespace AICompanion.Rendering
{
    /// <summary>
    /// Post Processing Controller - follows Single Responsibility Principle
    /// Manages post-processing effects for visual quality
    /// </summary>
    public class PostProcessingController : MonoBehaviour
    {
        [Header("Post Processing Volume")]
        [SerializeField] private Volume postProcessVolume;
        [SerializeField] private bool useBloom = true;
        [SerializeField] private bool useSSAO = true;
        [SerializeField] private bool useSSR = true;
        [SerializeField] private bool useToneMapping = true;

        [Header("Bloom Settings")]
        [SerializeField] private float bloomThreshold = 0.9f;
        [SerializeField] private float bloomIntensity = 0.5f;
        [SerializeField] private float bloomScatter = 0.7f;

        [Header("SSAO Settings")]
        [SerializeField] private float ssaoIntensity = 1f;
        [SerializeField] private float ssaoRadius = 0.3f;
        [SerializeField] private float ssaoThickness = 0.5f;

        [Header("SSR Settings")]
        [SerializeField] private float ssrIntensity = 0.5f;
        [SerializeField] private float ssrMaxDistance = 50f;
        [SerializeField] private int ssrStepCount = 32;

        [Header("Tone Mapping Settings")]
        [SerializeField] private TonemappingMode toneMappingMode = TonemappingMode.ACES;
        [SerializeField] private float exposure = 0f;
        [SerializeField] private float contrast = 0f;
        [SerializeField] private float saturation = 0f;

        [Header("Color Grading")]
        [SerializeField] private float temperature = 0f;
        [SerializeField] private float tint = 0f;
        [SerializeField] private Color colorFilter = Color.white;

        private VolumeProfile volumeProfile;
        private Bloom bloom;
        private AmbientOcclusion ssao;
        private ScreenSpaceReflection ssr;
        private Tonemapping tonemapping;
        private ColorGrading colorGrading;
        private LiftGammaGain liftGammaGain;

        private void Start()
        {
            InitializePostProcessing();
        }

        private void InitializePostProcessing()
        {
            // Create or get post process volume
            if (postProcessVolume == null)
            {
                GameObject volumeGO = new GameObject("Post Process Volume");
                volumeGO.transform.parent = transform;
                postProcessVolume = volumeGO.AddComponent<Volume>();
                postProcessVolume.isGlobal = true;
            }

            // Create volume profile
            volumeProfile = ScriptableObject.CreateInstance<VolumeProfile>();
            postProcessVolume.profile = volumeProfile;

            // Add post processing effects
            AddPostProcessingEffects();

            // Configure effects
            ConfigurePostProcessingEffects();
        }

        private void AddPostProcessingEffects()
        {
            // Add Bloom
            if (!volumeProfile.TryGet(out bloom))
            {
                bloom = volumeProfile.Add<Bloom>(true);
            }

            // Add SSAO
            if (!volumeProfile.TryGet(out ssao))
            {
                ssao = volumeProfile.Add<AmbientOcclusion>(true);
            }

            // Add SSR
            if (!volumeProfile.TryGet(out ssr))
            {
                ssr = volumeProfile.Add<ScreenSpaceReflection>(true);
            }

            // Add Tone Mapping
            if (!volumeProfile.TryGet(out tonemapping))
            {
                tonemapping = volumeProfile.Add<Tonemapping>(true);
            }

            // Add Color Grading
            if (!volumeProfile.TryGet(out colorGrading))
            {
                colorGrading = volumeProfile.Add<ColorGrading>(true);
            }

            // Add Lift Gamma Gain
            if (!volumeProfile.TryGet(out liftGammaGain))
            {
                liftGammaGain = volumeProfile.Add<LiftGammaGain>(true);
            }
        }

        private void ConfigurePostProcessingEffects()
        {
            // Configure Bloom
            if (bloom != null)
            {
                bloom.active = useBloom;
                bloom.threshold.value = bloomThreshold;
                bloom.intensity.value = bloomIntensity;
                bloom.scatter.value = bloomScatter;
            }

            // Configure SSAO
            if (ssao != null)
            {
                ssao.active = useSSAO;
                ssao.intensity.value = ssaoIntensity;
                ssao.radius.value = ssaoRadius;
                ssao.thickness.value = ssaoThickness;
            }

            // Configure SSR
            if (ssr != null)
            {
                ssr.active = useSSR;
                ssr.intensity.value = ssrIntensity;
                ssr.maxDistance.value = ssrMaxDistance;
                ssr.stepCount.value = ssrStepCount;
            }

            // Configure Tone Mapping
            if (tonemapping != null)
            {
                tonemapping.active = useToneMapping;
                tonemapping.mode.value = toneMappingMode;
            }

            // Configure Color Grading
            if (colorGrading != null)
            {
                colorGrading.active = true;
                colorGrading.temperature.value = temperature;
                colorGrading.tint.value = tint;
                colorGrading.colorFilter.value = colorFilter;
            }

            // Configure Lift Gamma Gain
            if (liftGammaGain != null)
            {
                liftGammaGain.active = true;
                liftGammaGain.contrast.value = contrast;
                liftGammaGain.saturation.value = saturation;
            }
        }

        public void SetBloomEnabled(bool enabled)
        {
            useBloom = enabled;
            if (bloom != null)
            {
                bloom.active = enabled;
            }
        }

        public void SetBloomSettings(float threshold, float intensity, float scatter)
        {
            bloomThreshold = threshold;
            bloomIntensity = intensity;
            bloomScatter = scatter;

            if (bloom != null)
            {
                bloom.threshold.value = threshold;
                bloom.intensity.value = intensity;
                bloom.scatter.value = scatter;
            }
        }

        public void SetSSAOEnabled(bool enabled)
        {
            useSSAO = enabled;
            if (ssao != null)
            {
                ssao.active = enabled;
            }
        }

        public void SetSSAOSettings(float intensity, float radius, float thickness)
        {
            ssaoIntensity = intensity;
            ssaoRadius = radius;
            ssaoThickness = thickness;

            if (ssao != null)
            {
                ssao.intensity.value = intensity;
                ssao.radius.value = radius;
                ssao.thickness.value = thickness;
            }
        }

        public void SetSSREnabled(bool enabled)
        {
            useSSR = enabled;
            if (ssr != null)
            {
                ssr.active = enabled;
            }
        }

        public void SetSSRSettings(float intensity, float maxDistance, int stepCount)
        {
            ssrIntensity = intensity;
            ssrMaxDistance = maxDistance;
            ssrStepCount = stepCount;

            if (ssr != null)
            {
                ssr.intensity.value = intensity;
                ssr.maxDistance.value = maxDistance;
                ssr.stepCount.value = stepCount;
            }
        }

        public void SetToneMappingMode(TonemappingMode mode)
        {
            toneMappingMode = mode;
            if (tonemapping != null)
            {
                tonemapping.mode.value = mode;
            }
        }

        public void SetExposure(float exposureValue)
        {
            exposure = exposureValue;
            if (colorGrading != null)
            {
                colorGrading.postExposure.value = exposureValue;
            }
        }

        public void SetColorGrading(float contrastValue, float saturationValue, float temperatureValue, float tintValue)
        {
            contrast = contrastValue;
            saturation = saturationValue;
            temperature = temperatureValue;
            tint = tintValue;

            if (liftGammaGain != null)
            {
                liftGammaGain.contrast.value = contrastValue;
                liftGammaGain.saturation.value = saturationValue;
            }

            if (colorGrading != null)
            {
                colorGrading.temperature.value = temperatureValue;
                colorGrading.tint.value = tintValue;
            }
        }

        public void SetColorFilter(Color color)
        {
            colorFilter = color;
            if (colorGrading != null)
            {
                colorGrading.colorFilter.value = color;
            }
        }

        public void SetPostProcessVolume(Volume volume)
        {
            postProcessVolume = volume;
            InitializePostProcessing();
        }

        public void ResetToDefaults()
        {
            useBloom = true;
            useSSAO = true;
            useSSR = true;
            useToneMapping = true;

            bloomThreshold = 0.9f;
            bloomIntensity = 0.5f;
            bloomScatter = 0.7f;

            ssaoIntensity = 1f;
            ssaoRadius = 0.3f;
            ssaoThickness = 0.5f;

            ssrIntensity = 0.5f;
            ssrMaxDistance = 50f;
            ssrStepCount = 32;

            toneMappingMode = TonemappingMode.ACES;
            exposure = 0f;
            contrast = 0f;
            saturation = 0f;

            temperature = 0f;
            tint = 0f;
            colorFilter = Color.white;

            ConfigurePostProcessingEffects();
        }
    }
}
