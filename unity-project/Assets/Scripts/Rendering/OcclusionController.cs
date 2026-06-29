using UnityEngine;
using UnityEngine.XR.ARFoundation;

namespace AICompanion.Rendering
{
    /// <summary>
    /// Occlusion Controller - follows Single Responsibility Principle
    /// Manages occlusion handling for AR characters
    /// </summary>
    public class OcclusionController : MonoBehaviour
    {
        [Header("Occlusion Components")]
        [SerializeField] private AROcclusionManager arOcclusionManager;
        [SerializeField] private GameObject characterRoot;

        [Header("Occlusion Settings")]
        [SerializeField] private bool useHumanSegmentation = true;
        [SerializeField] private bool useEnvironmentDepth = true;
        [SerializeField] private float occlusionSmoothness = 0.1f;

        [Header("Material Configuration")]
        [SerializeField] private Material occlusionMaterial;
        [SerializeField] private float stencilReferenceValue = 1;

        private Renderer[] characterRenderers;
        private bool isOcclusionEnabled;

        private void Start()
        {
            InitializeOcclusion();
        }

        private void InitializeOcclusion()
        {
            // Get AR Occlusion Manager
            if (arOcclusionManager == null)
            {
                arOcclusionManager = FindObjectOfType<AROcclusionManager>();
            }

            // Get character renderers
            if (characterRoot != null)
            {
                characterRenderers = characterRoot.GetComponentsInChildren<Renderer>();
            }
            else
            {
                characterRenderers = GetComponentsInChildren<Renderer>();
            }

            // Configure occlusion
            ConfigureAROcclusion();
            ConfigureStencilBuffer();
        }

        private void ConfigureAROcclusion()
        {
            if (arOcclusionManager == null) return;

            // Configure human segmentation
            if (useHumanSegmentation)
            {
                arOcclusionManager.humanSegmentationStencilMode = 
                    ARHumanSegmentationStencilMode.SeparateStencilTexture;
                arOcclusionManager.humanSegmentationSmoothing = occlusionSmoothness;
            }

            // Configure environment depth
            if (useEnvironmentDepth)
            {
                arOcclusionManager.environmentDepthMode = 
                    AROcclusionEnvironmentDepthMode.Fastest;
                arOcclusionManager.environmentDepthTemporalSmoothing = occlusionSmoothness;
            }

            isOcclusionEnabled = true;
        }

        private void ConfigureStencilBuffer()
        {
            // Configure stencil buffer for custom occlusion
            if (occlusionMaterial != null)
            {
                occlusionMaterial.SetFloat("_StencilRef", stencilReferenceValue);
            }

            // Apply stencil settings to character renderers
            foreach (Renderer renderer in characterRenderers)
            {
                if (renderer.material != null)
                {
                    // Configure material stencil
                    renderer.material.SetFloat("_StencilRef", stencilReferenceValue);
                }
            }
        }

        private void Update()
        {
            UpdateOcclusion();
        }

        private void UpdateOcclusion()
        {
            if (!isOcclusionEnabled) return;

            // Update occlusion based on AR tracking
            if (arOcclusionManager != null)
            {
                UpdateHumanOcclusion();
                UpdateEnvironmentOcclusion();
            }
        }

        private void UpdateHumanOcclusion()
        {
            if (!useHumanSegmentation) return;

            // Get human segmentation texture
            Texture2D stencilTexture = arOcclusionManager.humanStencil;
            
            if (stencilTexture != null)
            {
                // Apply human occlusion to character
                ApplyHumanOcclusion(stencilTexture);
            }
        }

        private void UpdateEnvironmentOcclusion()
        {
            if (!useEnvironmentDepth) return;

            // Get environment depth texture
            Texture2D depthTexture = arOcclusionManager.environmentDepth;

            if (depthTexture != null)
            {
                // Apply environment occlusion to character
                ApplyEnvironmentOcclusion(depthTexture);
            }
        }

        private void ApplyHumanOcclusion(Texture2D stencilTexture)
        {
            // Apply human segmentation stencil to character materials
            foreach (Renderer renderer in characterRenderers)
            {
                if (renderer.material != null)
                {
                    renderer.material.SetTexture("_HumanStencil", stencilTexture);
                }
            }
        }

        private void ApplyEnvironmentOcclusion(Texture2D depthTexture)
        {
            // Apply environment depth to character materials
            foreach (Renderer renderer in characterRenderers)
            {
                if (renderer.material != null)
                {
                    renderer.material.SetTexture("_EnvironmentDepth", depthTexture);
                }
            }
        }

        public void SetOcclusionEnabled(bool enabled)
        {
            isOcclusionEnabled = enabled;
            
            if (arOcclusionManager != null)
            {
                arOcclusionManager.enabled = enabled;
            }
        }

        public void SetHumanSegmentationEnabled(bool enabled)
        {
            useHumanSegmentation = enabled;
            
            if (arOcclusionManager != null)
            {
                arOcclusionManager.humanSegmentationEnabled = enabled;
            }
        }

        public void SetEnvironmentDepthEnabled(bool enabled)
        {
            useEnvironmentDepth = enabled;
            
            if (arOcclusionManager != null)
            {
                arOcclusionManager.environmentDepthEnabled = enabled;
            }
        }

        public void SetOcclusionSmoothness(float smoothness)
        {
            occlusionSmoothness = Mathf.Clamp01(smoothness);
            
            if (arOcclusionManager != null)
            {
                arOcclusionManager.humanSegmentationSmoothing = smoothness;
                arOcclusionManager.environmentDepthTemporalSmoothing = smoothness;
            }
        }

        public void SetCharacterRoot(GameObject root)
        {
            characterRoot = root;
            characterRenderers = root.GetComponentsInChildren<Renderer>();
        }

        public void SetOcclusionMaterial(Material material)
        {
            occlusionMaterial = material;
            ConfigureStencilBuffer();
        }
    }
}
