using UnityEngine;

namespace AICompanion.Core.Interfaces
{
    /// <summary>
    /// Interface for lighting control - follows Interface Segregation Principle
    /// </summary>
    public interface ILightingController
    {
        void SetAmbientLight(Color color, float intensity);
        void SetDirectionalLight(Vector3 direction, Color color, float intensity);
        void UpdateLightEstimation(Color estimatedColor, float estimatedIntensity);
        void SetLightProbeGroup(GameObject lightProbeGroup);
        void BakeLightProbes();
        Color GetCurrentAmbientColor();
        float GetCurrentAmbientIntensity();
    }
}
