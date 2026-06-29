using UnityEngine;
using System;
using System.Threading.Tasks;
using System.Collections.Generic;

namespace AICompanion.Vision
{
    /// <summary>
    /// Interface for vision processor handling computer vision tasks
    /// </summary>
    public interface IVisionProcessor
    {
        /// <summary>
        /// Event triggered when object detection results are available
        /// </summary>
        event Action<DetectionResult[]> OnObjectsDetected;

        /// <summary>
        /// Event triggered when pose estimation results are available
        /// </summary>
        event Action<PoseData> OnPoseEstimated;

        /// <summary>
        /// Event triggered when face detection results are available
        /// </summary>
        event Action<FaceData> OnFaceDetected;

        /// <summary>
        /// Event triggered when hand tracking results are available
        /// </summary>
        event Action<HandData> OnHandTracked;

        /// <summary>
        /// Check if vision processor is ready
        /// </summary>
        bool IsReady { get; }

        /// <summary>
        /// Check if currently processing
        /// </summary>
        bool IsProcessing { get; }

        /// <summary>
        /// Process camera frame for object detection
        /// </summary>
        /// <param name="texture">Camera texture</param>
        /// <returns>Detection results</returns>
        Task<DetectionResult[]> DetectObjectsAsync(Texture2D texture);

        /// <summary>
        /// Process camera frame for pose estimation
        /// </summary>
        /// <param name="texture">Camera texture</param>
        /// <returns>Pose data</returns>
        Task<PoseData> EstimatePoseAsync(Texture2D texture);

        /// <summary>
        /// Process camera frame for face detection
        /// </summary>
        /// <param name="texture">Camera texture</param>
        /// <returns>Face data</returns>
        Task<FaceData> DetectFaceAsync(Texture2D texture);

        /// <summary>
        /// Process camera frame for hand tracking
        /// </summary>
        /// <param name="texture">Camera texture</param>
        /// <returns>Hand data</returns>
        Task<HandData> TrackHandAsync(Texture2D texture);

        /// <summary>
        /// Enable/disable specific vision features
        /// </summary>
        void SetFeatureEnabled(VisionFeature feature, bool enabled);

        /// <summary>
        /// Check if feature is enabled
        /// </summary>
        bool IsFeatureEnabled(VisionFeature feature);

        /// <summary>
        /// Set detection confidence threshold
        /// </summary>
        void SetConfidenceThreshold(float threshold);

        /// <summary>
        /// Get current camera frame
        /// </summary>
        Texture2D GetCurrentFrame();

        /// <summary>
        /// Initialize vision processor
        /// </summary>
        Task InitializeAsync();

        /// <summary>
        /// Shutdown vision processor
        /// </summary>
        Task ShutdownAsync();
    }

    /// <summary>
    /// Vision feature enumeration
    /// </summary>
    [Flags]
    public enum VisionFeature
    {
        None = 0,
        ObjectDetection = 1 << 0,
        PoseEstimation = 1 << 1,
        FaceDetection = 1 << 2,
        HandTracking = 1 << 3,
        DepthEstimation = 1 << 4,
        Segmentation = 1 << 5,
        All = ObjectDetection | PoseEstimation | FaceDetection | HandTracking | DepthEstimation | Segmentation
    }

    /// <summary>
    /// Detection result data structure
    /// </summary>
    [Serializable]
    public class DetectionResult
    {
        public string label;
        public float confidence;
        public Rect boundingBox;
        public Vector3 position;
        public Quaternion rotation;
        public Vector3 size;

        public DetectionResult()
        {
            label = "";
            confidence = 0f;
            boundingBox = new Rect(0, 0, 0, 0);
            position = Vector3.zero;
            rotation = Quaternion.identity;
            size = Vector3.zero;
        }
    }

    /// <summary>
    /// Pose data structure
    /// </summary>
    [Serializable]
    public class PoseData
    {
        public PoseLandmark[] landmarks;
        public float confidence;
        public Vector3 position;
        public Quaternion rotation;

        public PoseData()
        {
            landmarks = new PoseLandmark[33]; // MediaPipe pose has 33 landmarks
            confidence = 0f;
            position = Vector3.zero;
            rotation = Quaternion.identity;
        }
    }

    /// <summary>
    /// Pose landmark structure
    /// </summary>
    [Serializable]
    public struct PoseLandmark
    {
        public Vector3 position;
        public float visibility;
        public float confidence;

        public PoseLandmark(Vector3 pos, float vis, float conf)
        {
            position = pos;
            visibility = vis;
            confidence = conf;
        }
    }

    /// <summary>
    /// Face data structure
    /// </summary>
    [Serializable]
    public class FaceData
    {
        public Rect boundingBox;
        public Vector2[] landmarks; // 468 landmarks for MediaPipe face mesh
        public float confidence;
        public Vector3 headPosition;
        public Quaternion headRotation;
        public float[] blendShapes; // Facial expression blend shapes

        public FaceData()
        {
            boundingBox = new Rect(0, 0, 0, 0);
            landmarks = new Vector2[468];
            confidence = 0f;
            headPosition = Vector3.zero;
            headRotation = Quaternion.identity;
            blendShapes = new float[52]; // Standard blend shape count
        }
    }

    /// <summary>
    /// Hand data structure
    /// </summary>
    [Serializable]
    public class HandData
    {
        public bool isLeftHand;
        public Vector2[] landmarks; // 21 landmarks for MediaPipe hands
        public float confidence;
        public Vector3 position;
        public Quaternion rotation;
        public FingerState[] fingers;

        public HandData()
        {
            isLeftHand = false;
            landmarks = new Vector2[21];
            confidence = 0f;
            position = Vector3.zero;
            rotation = Quaternion.identity;
            fingers = new FingerState[5]; // Thumb, Index, Middle, Ring, Pinky
        }
    }

    /// <summary>
    /// Finger state enumeration
    /// </summary>
    public enum FingerState
    {
        Unknown,
        Extended,
        Curled,
        PartiallyExtended
    }
}