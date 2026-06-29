using UnityEngine;
using System;

namespace AICompanion.Rendering
{
    /// <summary>
    /// Camera Manager - follows Single Responsibility Principle
    /// Manages camera setup, AR camera configuration, and post-processing
    /// </summary>
    public class CameraManager : MonoBehaviour
    {
        [Header("Camera Configuration")]
        [SerializeField] private Camera mainCamera;
        [SerializeField] private bool isARCamera = true;

        [Header("Camera Settings")]
        [SerializeField] private float fieldOfView = 60f;
        [SerializeField] private float nearClipPlane = 0.1f;
        [SerializeField] private float farClipPlane = 1000f;
        [SerializeField] private Vector3 defaultPosition = new Vector3(0, 1.6f, 0);

        [Header("Follow Settings")]
        [SerializeField] private Transform followTarget;
        [SerializeField] private float followSpeed = 5f;
        [SerializeField] private float rotationSpeed = 5f;
        [SerializeField] private Vector3 followOffset = new Vector3(0, 0, -2f);

        [Header("Camera Modes")]
        [SerializeField] private CameraMode currentMode = CameraMode.FirstPerson;
        [SerializeField] private float thirdPersonDistance = 3f;
        [SerializeField] private float thirdPersonHeight = 1.5f;

        public enum CameraMode
        {
            FirstPerson,
            ThirdPerson,
            Cinematic,
            FreeLook
        }

        private Vector3 currentVelocity;
        private Quaternion targetRotation;

        public event Action<CameraMode> OnCameraModeChanged;

        private void Start()
        {
            InitializeCamera();
            SetCameraMode(currentMode);
        }

        private void InitializeCamera()
        {
            if (mainCamera == null)
            {
                mainCamera = Camera.main;
            }

            if (mainCamera == null)
            {
                GameObject cameraGO = new GameObject("Main Camera");
                mainCamera = cameraGO.AddComponent<Camera>();
                cameraGO.tag = "MainCamera";
            }

            // Configure camera
            mainCamera.fieldOfView = fieldOfView;
            mainCamera.nearClipPlane = nearClipPlane;
            mainCamera.farClipPlane = farClipPlane;
            mainCamera.transform.position = defaultPosition;

            // Configure for AR if needed
            if (isARCamera)
            {
                ConfigureARCamera();
            }
        }

        private void ConfigureARCamera()
        {
            // AR camera configuration
            mainCamera.clearFlags = CameraClearFlags.SolidColor;
            mainCamera.backgroundColor = new Color(0, 0, 0, 0);
            
            // Add AR camera component if using AR Foundation
            #if UNITY_AR_FOUNDATION_AVAILABLE
            var arCamera = mainCamera.gameObject.GetComponent<UnityEngine.XR.ARFoundation.ARCameraBackground>();
            if (arCamera == null)
            {
                arCamera = mainCamera.gameObject.AddComponent<UnityEngine.XR.ARFoundation.ARCameraBackground>();
            }
            #endif
        }

        private void Update()
        {
            UpdateCameraPosition();
            UpdateCameraRotation();
        }

        private void UpdateCameraPosition()
        {
            if (followTarget == null) return;

            Vector3 targetPosition;

            switch (currentMode)
            {
                case CameraMode.FirstPerson:
                    targetPosition = followTarget.position + followOffset;
                    break;
                case CameraMode.ThirdPerson:
                    targetPosition = followTarget.position + 
                        followTarget.rotation * (Vector3.back * thirdPersonDistance + Vector3.up * thirdPersonHeight);
                    break;
                case CameraMode.Cinematic:
                    targetPosition = CalculateCinematicPosition();
                    break;
                case CameraMode.FreeLook:
                    targetPosition = mainCamera.transform.position; // Manual control
                    break;
                default:
                    targetPosition = mainCamera.transform.position;
                    break;
            }

            // Smooth follow
            mainCamera.transform.position = Vector3.SmoothDamp(
                mainCamera.transform.position,
                targetPosition,
                ref currentVelocity,
                1f / followSpeed
            );
        }

        private void UpdateCameraRotation()
        {
            if (followTarget == null) return;

            switch (currentMode)
            {
                case CameraMode.FirstPerson:
                    targetRotation = followTarget.rotation;
                    break;
                case CameraMode.ThirdPerson:
                    targetRotation = Quaternion.LookRotation(followTarget.position - mainCamera.transform.position);
                    break;
                case CameraMode.Cinematic:
                    targetRotation = CalculateCinematicRotation();
                    break;
                case CameraMode.FreeLook:
                    // Manual rotation control
                    return;
            }

            mainCamera.transform.rotation = Quaternion.Slerp(
                mainCamera.transform.rotation,
                targetRotation,
                Time.deltaTime * rotationSpeed
            );
        }

        private Vector3 CalculateCinematicPosition()
        {
            // Dynamic cinematic positioning
            float time = Time.time * 0.5f;
            float xOffset = Mathf.Sin(time) * 2f;
            float zOffset = Mathf.Cos(time) * 2f;
            float yOffset = Mathf.Sin(time * 0.5f) * 1f + 2f;

            return followTarget.position + new Vector3(xOffset, yOffset, zOffset);
        }

        private Quaternion CalculateCinematicRotation()
        {
            // Dynamic cinematic rotation
            return Quaternion.LookRotation(followTarget.position - mainCamera.transform.position);
        }

        public void SetCameraMode(CameraMode mode)
        {
            currentMode = mode;
            OnCameraModeChanged?.Invoke(mode);
        }

        public void SetFollowTarget(Transform target)
        {
            followTarget = target;
        }

        public void SetFieldOfView(float fov)
        {
            fieldOfView = fov;
            if (mainCamera != null)
            {
                mainCamera.fieldOfView = fov;
            }
        }

        public void SetFollowParameters(float speed, Vector3 offset)
        {
            followSpeed = speed;
            followOffset = offset;
        }

        public void SetThirdPersonParameters(float distance, float height)
        {
            thirdPersonDistance = distance;
            thirdPersonHeight = height;
        }

        public void ResetCamera()
        {
            if (mainCamera != null)
            {
                mainCamera.transform.position = defaultPosition;
                mainCamera.transform.rotation = Quaternion.identity;
            }
        }

        public Camera GetMainCamera()
        {
            return mainCamera;
        }

        public CameraMode GetCurrentMode()
        {
            return currentMode;
        }
    }
}
