using System;
using UnityEngine;
using UnityEngine.XR;
using UnityEngine.XR.ARFoundation;
using AICompanion.Core.Interfaces;

namespace AICompanion.AR
{
    /// <summary>
    /// AR Session Manager - follows Single Responsibility Principle
    /// Manages AR session lifecycle and tracking state
    /// </summary>
    public class ARSessionManager : MonoBehaviour, IARSessionManager
    {
        public event Action OnARSessionStarted;
        public event Action OnARSessionStopped;
        public event Action OnTrackingLost;
        public event Action OnTrackingRegained;

        [Header("AR Components")]
        [SerializeField] private ARSession arSession;
        [SerializeField] private ARSessionOrigin arSessionOrigin;
        [SerializeField] private ARPlaneManager arPlaneManager;
        [SerializeField] private AROcclusionManager arOcclusionManager;

        [Header("Settings")]
        [SerializeField] private bool autoStartSession = true;
        [SerializeField] private bool enablePlaneDetection = true;
        [SerializeField] private bool enableLightEstimation = true;

        public bool IsSessionRunning { get; private set; }
        public bool IsTracking { get; private set; }

        private void Start()
        {
            InitializeARComponents();
            
            if (autoStartSession)
            {
                StartSession();
            }
        }

        private void InitializeARComponents()
        {
            // Get or create AR components
            if (arSession == null)
            {
                arSession = FindObjectOfType<ARSession>();
                if (arSession == null)
                {
                    GameObject sessionGO = new GameObject("AR Session");
                    arSession = sessionGO.AddComponent<ARSession>();
                }
            }

            if (arSessionOrigin == null)
            {
                arSessionOrigin = FindObjectOfType<ARSessionOrigin>();
                if (arSessionOrigin == null)
                {
                    GameObject originGO = new GameObject("AR Session Origin");
                    arSessionOrigin = originGO.AddComponent<ARSessionOrigin>();
                }
            }

            if (arPlaneManager == null)
            {
                arPlaneManager = FindObjectOfType<ARPlaneManager>();
                if (arPlaneManager == null && arSessionOrigin != null)
                {
                    arPlaneManager = arSessionOrigin.gameObject.AddComponent<ARPlaneManager>();
                }
            }

            if (arOcclusionManager == null)
            {
                arOcclusionManager = FindObjectOfType<AROcclusionManager>();
                if (arOcclusionManager == null && arSessionOrigin != null)
                {
                    arOcclusionManager = arSessionOrigin.gameObject.AddComponent<AROcclusionManager>();
                }
            }

            // Configure initial settings
            SetPlaneDetectionEnabled(enablePlaneDetection);
            SetLightEstimationEnabled(enableLightEstimation);
        }

        public void StartSession()
        {
            if (IsSessionRunning) return;

            Debug.Log("Starting AR Session...");
            
            if (arSession != null)
            {
                arSession.enabled = true;
                IsSessionRunning = true;
                OnARSessionStarted?.Invoke();
            }
        }

        public void StopSession()
        {
            if (!IsSessionRunning) return;

            Debug.Log("Stopping AR Session...");
            
            if (arSession != null)
            {
                arSession.enabled = false;
                IsSessionRunning = false;
                IsTracking = false;
                OnARSessionStopped?.Invoke();
            }
        }

        public void PauseSession()
        {
            if (!IsSessionRunning) return;

            Debug.Log("Pausing AR Session...");
            
            if (arSession != null)
            {
                arSession.Pause();
            }
        }

        public void ResumeSession()
        {
            if (!IsSessionRunning) return;

            Debug.Log("Resuming AR Session...");
            
            if (arSession != null)
            {
                arSession.Resume();
            }
        }

        public void SetPlaneDetectionEnabled(bool enabled)
        {
            if (arPlaneManager != null)
            {
                arPlaneManager.enabled = enabled;
                enablePlaneDetection = enabled;
                Debug.Log($"Plane detection {(enabled ? "enabled" : "disabled")}");
            }
        }

        public void SetLightEstimationEnabled(bool enabled)
        {
            enableLightEstimation = enabled;
            Debug.Log($"Light estimation {(enabled ? "enabled" : "disabled")}");
        }

        private void Update()
        {
            UpdateTrackingState();
        }

        private void UpdateTrackingState()
        {
            bool wasTracking = IsTracking;
            IsTracking = IsSessionRunning && CheckTrackingStatus();

            if (wasTracking && !IsTracking)
            {
                OnTrackingLost?.Invoke();
                Debug.LogWarning("AR Tracking lost");
            }
            else if (!wasTracking && IsTracking)
            {
                OnTrackingRegained?.Invoke();
                Debug.Log("AR Tracking regained");
            }
        }

        private bool CheckTrackingStatus()
        {
            // Check AR system tracking status
            if (XRSettings.enabled)
            {
                // Additional tracking checks can be added here
                return true;
            }
            return false;
        }

        private void OnDestroy()
        {
            StopSession();
        }
    }
}
