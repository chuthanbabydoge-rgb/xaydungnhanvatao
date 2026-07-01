using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;
using AICompanion.Core.Interfaces;

namespace AICompanion.Rendering
{
    /// <summary>
    /// Lighting Controller - follows Single Responsibility Principle
    /// Manages dynamic lighting and light estimation for AR
    /// </summary>
    public class LightingController : MonoBehaviour, ILightingController
    {
        [Header("Light Components")]
        [SerializeField] private Light mainDirectionalLight;
        [SerializeField] private Light additionalLight1;
        [SerializeField] private Light additionalLight2;

        [Header("Light Settings")]
        [SerializeField] private Color defaultAmbientColor = new Color(0.2f, 0.2f, 0.2f);
        [SerializeField] private float defaultAmbientIntensity = 1f;
        [SerializeField] private float defaultLightIntensity = 1f;

        [Header("Light Estimation")]
        [SerializeField] private bool useLightEstimation = true;
        [SerializeField] private float lightEstimationSmoothing = 0.1f;

        [Header("HDRP Settings")]
        [SerializeField] private Volume postProcessVolume;
        [SerializeField] private HDRI skyHDRISetup;

        private Color currentAmbientColor;
        private float currentAmbientIntensity;
        private Color estimatedLightColor;
        private float estimatedLightIntensity;

        private void Start()
        {
            InitializeLights();
            SetAmbientLight(defaultAmbientColor, defaultAmbientIntensity);
        }

        private void InitializeLights()
        {
            // Create main directional light if not assigned
            if (mainDirectionalLight == null)
            {
                GameObject lightGO = new GameObject("Main Directional Light");
                mainDirectionalLight = lightGO.AddComponent<Light>();
                mainDirectionalLight.type = LightType.Directional;
                mainDirectionalLight.shadows = LightShadows.Soft;
                lightGO.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
            }

            // Set default light intensity
            mainDirectionalLight.intensity = defaultLightIntensity;

            // Configure for HDRP if available
            #if UNITY_2021_2_OR_NEWER
            ConfigureHDRPLighting();
            #endif
        }

        #if UNITY_2021_2_OR_NEWER
        private void ConfigureHDRPLighting()
        {
            // Configure HDRP specific lighting settings
            if (mainDirectionalLight != null)
            {
                HDAdditionalLightData additionalLightData = mainDirectionalLight.GetComponent<HDAdditionalLightData>();
                if (additionalLightData == null)
                {
                    additionalLightData = mainDirectionalLight.gameObject.AddComponent<HDAdditionalLightData>();
                }

                // Configure HD light settings
                additionalLightData.enableShadows = true;
                additionalLightData.shadowResolution = HDShadowResolution.SoftShadows;
            }
        }
        #endif

        private void Update()
        {
            if (useLightEstimation)
            {
                UpdateLightEstimation();
            }
        }

        private void UpdateLightEstimation()
        {
            // Smoothly interpolate to estimated light values
            if (mainDirectionalLight != null)
            {
                mainDirectionalLight.color = Color.Lerp(
                    mainDirectionalLight.color,
                    estimatedLightColor,
                    Time.deltaTime * lightEstimationSmoothing
                );

                mainDirectionalLight.intensity = Mathf.Lerp(
                    mainDirectionalLight.intensity,
                    estimatedLightIntensity,
                    Time.deltaTime * lightEstimationSmoothing
                );
            }

            // Update ambient light
            RenderSettings.ambientLight = Color.Lerp(
                RenderSettings.ambientLight,
                currentAmbientColor,
                Time.deltaTime * lightEstimationSmoothing
            );

            RenderSettings.ambientIntensity = Mathf.Lerp(
                RenderSettings.ambientIntensity,
                currentAmbientIntensity,
                Time.deltaTime * lightEstimationSmoothing
            );
        }

        public void SetAmbientLight(Color color, float intensity)
        {
            currentAmbientColor = color;
            currentAmbientIntensity = intensity;
            RenderSettings.ambientLight = color;
            RenderSettings.ambientIntensity = intensity;
        }

        public void SetDirectionalLight(Vector3 direction, Color color, float intensity)
        {
            if (mainDirectionalLight != null)
            {
                mainDirectionalLight.transform.rotation = Quaternion.LookRotation(-direction);
                mainDirectionalLight.color = color;
                mainDirectionalLight.intensity = intensity;
            }
        }

        public void UpdateLightEstimation(Color estimatedColor, float estimatedIntensity)
        {
            estimatedLightColor = estimatedColor;
            estimatedLightIntensity = estimatedIntensity;
        }

        public void SetLightProbeGroup(GameObject lightProbeGroup)
        {
            if (lightProbeGroup != null)
            {
                LightProbes lightProbes = lightProbeGroup.GetComponent<LightProbes>();
                if (lightProbes == null)
                {
                    lightProbes = lightProbeGroup.AddComponent<LightProbes>();
                }
            }
        }

        public void BakeLightProbes()
        {
            // Trigger light probe baking
            LightmapSettings.bakeProbeLayerMask = -1;
            Lightmapping.BakeAsync();
        }

        public Color GetCurrentAmbientColor()
        {
            return RenderSettings.ambientLight;
        }

        public float GetCurrentAmbientIntensity()
        {
            return RenderSettings.ambientIntensity;
        }

        public void SetMainLight(Light light)
        {
            mainDirectionalLight = light;
        }

        public void SetLightEstimationEnabled(bool enabled)
        {
            useLightEstimation = enabled;
        }

        public void SetLightEstimationSmoothing(float smoothing)
        {
            lightEstimationSmoothing = Mathf.Clamp01(smoothing);
        }

        public void ConfigureAdditionalLights(Color color1, Color color2, float intensity1, float intensity2)
        {
            if (additionalLight1 != null)
            {
                additionalLight1.color = color1;
                additionalLight1.intensity = intensity1;
            }

            if (additionalLight2 != null)
            {
                additionalLight2.color = color2;
                additionalLight2.intensity = intensity2;
            }
        }
    }
}
