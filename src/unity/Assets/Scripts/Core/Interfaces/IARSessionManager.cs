using System;
using UnityEngine;

namespace AICompanion.Core.Interfaces
{
    /// <summary>
    /// Interface for AR session management - follows Interface Segregation Principle
    /// </summary>
    public interface IARSessionManager
    {
        event Action OnARSessionStarted;
        event Action OnARSessionStopped;
        event Action OnTrackingLost;
        event Action OnTrackingRegained;
        
        bool IsSessionRunning { get; }
        bool IsTracking { get; }
        
        void StartSession();
        void StopSession();
        void PauseSession();
        void ResumeSession();
        
        void SetPlaneDetectionEnabled(bool enabled);
        void SetLightEstimationEnabled(bool enabled);
    }
}
