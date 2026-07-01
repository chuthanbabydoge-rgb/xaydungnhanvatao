using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;

namespace AICompanion.Animation
{
    /// <summary>
    /// Streaming Voice Controller - follows Single Responsibility Principle
    /// Manages real-time audio streaming for voice synthesis
    /// </summary>
    public class StreamingVoiceController : MonoBehaviour
    {
        [Header("Audio Streaming")]
        [SerializeField] private AudioSource streamingAudioSource;
        [SerializeField] private int bufferSize = 4096;
        [SerializeField] private int sampleRate = 44100;
        [SerializeField] private int channels = 1;

        [Header("Streaming Settings")]
        [SerializeField] private float bufferLatency = 0.1f;
        [SerializeField] private float streamBufferDuration = 2f;
        [SerializeField] private bool enableDynamicBuffering = true;
        [SerializeField] private bool enableNoiseReduction = true;

        [Header("Quality Settings")]
        [SerializeField] private AudioQuality audioQuality = AudioQuality.High;
        [SerializeField] private float targetBitrate = 128000f;

        [Header("Fallback")]
        [SerializeField] private bool enableFallbackBuffer = true;
        [SerializeField] private float fallbackBufferDuration = 0.5f;

        [Header("Integration")]
        [SerializeField] private LipSyncController lipSyncController;
        [SerializeField] private SpeechController speechController;

        private Queue<float[]> audioBufferQueue = new Queue<float[]>();
        private float[] currentBuffer;
        private int currentBufferPosition;
        private bool isStreaming;
        private bool isBufferUnderrun;
        private Coroutine streamingCoroutine;
        private Coroutine bufferMonitoringCoroutine;

        public event Action OnStreamingStarted;
        public event Action OnStreamingStopped;
        public event Action OnBufferUnderrun;
        public event Action OnBufferRecovered;
        public event Action<float> OnBufferLevelChanged;

        public enum AudioQuality
        {
            Low,
            Medium,
            High,
            Ultra
        }

        private void Awake()
        {
            InitializeAudioSource();
        }

        private void InitializeAudioSource()
        {
            if (streamingAudioSource == null)
            {
                streamingAudioSource = gameObject.AddComponent<AudioSource>();
            }

            streamingAudioSource.playOnAwake = false;
            streamingAudioSource.loop = false;
        }

        private void Start()
        {
            FindControllers();
            InitializeBuffers();
        }

        private void FindControllers()
        {
            if (lipSyncController == null)
            {
                lipSyncController = GetComponent<LipSyncController>();
            }

            if (speechController == null)
            {
                speechController = GetComponent<SpeechController>();
            }
        }

        private void InitializeBuffers()
        {
            // Calculate buffer size based on settings
            int totalBufferSize = Mathf.CeilToInt(sampleRate * streamBufferDuration);
            currentBuffer = new float[bufferSize];
            currentBufferPosition = 0;
        }

        public void StartStreaming()
        {
            if (isStreaming) return;

            isStreaming = true;
            streamingAudioSource.Play();
            streamingCoroutine = StartCoroutine(StreamingCoroutine());
            bufferMonitoringCoroutine = StartCoroutine(BufferMonitoringCoroutine());

            OnStreamingStarted?.Invoke();
        }

        public void StopStreaming()
        {
            if (!isStreaming) return;

            isStreaming = false;
            streamingAudioSource.Stop();

            if (streamingCoroutine != null)
            {
                StopCoroutine(streamingCoroutine);
                streamingCoroutine = null;
            }

            if (bufferMonitoringCoroutine != null)
            {
                StopCoroutine(bufferMonitoringCoroutine);
                bufferMonitoringCoroutine = null;
            }

            audioBufferQueue.Clear();
            currentBufferPosition = 0;

            OnStreamingStopped?.Invoke();
        }

        public void StreamAudioData(float[] audioData)
        {
            if (!isStreaming) return;

            // Process audio data
            float[] processedData = ProcessAudioData(audioData);

            // Add to buffer queue
            audioBufferQueue.Enqueue(processedData);

            // Update lip sync if available
            if (lipSyncController != null)
            {
                UpdateLipSyncFromAudio(processedData);
            }
        }

        private float[] ProcessAudioData(float[] audioData)
        {
            float[] processedData = new float[audioData.Length];

            for (int i = 0; i < audioData.Length; i++)
            {
                processedData[i] = audioData[i];

                // Apply noise reduction
                if (enableNoiseReduction)
                {
                    processedData[i] = ApplyNoiseReduction(processedData[i]);
                }

                // Apply quality-based processing
                processedData[i] = ApplyQualityProcessing(processedData[i]);
            }

            return processedData;
        }

        private float ApplyNoiseReduction(float sample)
        {
            // Simple noise gate
            float noiseThreshold = 0.01f;
            if (Mathf.Abs(sample) < noiseThreshold)
            {
                return 0f;
            }
            return sample;
        }

        private float ApplyQualityProcessing(float sample)
        {
            switch (audioQuality)
            {
                case AudioQuality.Low:
                    // Apply basic compression
                    return Mathf.Clamp(sample * 1.2f, -1f, 1f);
                case AudioQuality.Medium:
                    // Apply gentle compression and limiting
                    float compressed = Mathf.Clamp(sample * 1.1f, -0.9f, 0.9f);
                    return compressed + (compressed * 0.1f * Mathf.Sign(compressed));
                case AudioQuality.High:
                    // Apply advanced processing
                    float processed = sample;
                    processed = Mathf.Clamp(processed * 1.05f, -0.95f, 0.95f);
                    processed += (processed * 0.05f * Mathf.Sign(processed));
                    return processed;
                case AudioQuality.Ultra:
                    // Apply premium processing
                    float ultraProcessed = sample;
                    ultraProcessed = Mathf.Clamp(ultraProcessed * 1.02f, -0.98f, 0.98f);
                    ultraProcessed += (ultraProcessed * 0.02f * Mathf.Sign(ultraProcessed));
                    return ultraProcessed;
                default:
                    return sample;
            }
        }

        private IEnumerator StreamingCoroutine()
        {
            while (isStreaming)
            {
                // Process buffered audio
                if (audioBufferQueue.Count > 0)
                {
                    float[] buffer = audioBufferQueue.Dequeue();
                    ProcessBuffer(buffer);
                }
                else if (enableFallbackBuffer && !isBufferUnderrun)
                {
                    // Handle buffer underrun
                    isBufferUnderrun = true;
                    OnBufferUnderrun?.Invoke();
                }

                yield return null;
            }
        }

        private void ProcessBuffer(float[] buffer)
        {
            // In a real implementation, this would feed the audio to the AudioSource
            // For now, we'll simulate the processing

            if (isBufferUnderrun)
            {
                isBufferUnderrun = false;
                OnBufferRecovered?.Invoke();
            }

            // Calculate buffer level
            float bufferLevel = (float)audioBufferQueue.Count / (streamBufferDuration / bufferLatency);
            OnBufferLevelChanged?.Invoke(bufferLevel);
        }

        private IEnumerator BufferMonitoringCoroutine()
        {
            while (isStreaming)
            {
                float bufferDuration = audioBufferQueue.Count * (bufferSize / (float)sampleRate);
                float bufferLevel = Mathf.Clamp01(bufferDuration / streamBufferDuration);

                if (bufferLevel < 0.2f && !isBufferUnderrun)
                {
                    isBufferUnderrun = true;
                    OnBufferUnderrun?.Invoke();
                }
                else if (bufferLevel > 0.5f && isBufferUnderrun)
                {
                    isBufferUnderrun = false;
                    OnBufferRecovered?.Invoke();
                }

                OnBufferLevelChanged?.Invoke(bufferLevel);

                yield return new WaitForSeconds(0.1f);
            }
        }

        private void UpdateLipSyncFromAudio(float[] audioData)
        {
            // Calculate average volume from audio data
            float sum = 0f;
            for (int i = 0; i < audioData.Length; i++)
            {
                sum += Mathf.Abs(audioData[i]);
            }
            float averageVolume = sum / audioData.Length;

            // Update lip sync sensitivity based on volume
            if (averageVolume > 0.1f)
            {
                lipSyncController.SetSensitivity(1.5f);
            }
            else if (averageVolume > 0.05f)
            {
                lipSyncController.SetSensitivity(1.2f);
            }
            else
            {
                lipSyncController.SetSensitivity(1.0f);
            }
        }

        public void SetAudioQuality(AudioQuality quality)
        {
            audioQuality = quality;

            // Adjust target bitrate based on quality
            switch (quality)
            {
                case AudioQuality.Low:
                    targetBitrate = 64000f;
                    break;
                case AudioQuality.Medium:
                    targetBitrate = 96000f;
                    break;
                case AudioQuality.High:
                    targetBitrate = 128000f;
                    break;
                case AudioQuality.Ultra:
                    targetBitrate = 192000f;
                    break;
            }
        }

        public void SetBufferLatency(float latency)
        {
            bufferLatency = Mathf.Clamp(latency, 0.05f, 0.5f);
        }

        public void SetStreamBufferDuration(float duration)
        {
            streamBufferDuration = Mathf.Clamp(duration, 0.5f, 5f);
            InitializeBuffers();
        }

        public void SetSampleRate(int rate)
        {
            sampleRate = rate;
            InitializeBuffers();
        }

        public bool IsStreaming()
        {
            return isStreaming;
        }

        public float GetBufferLevel()
        {
            float bufferDuration = audioBufferQueue.Count * (bufferSize / (float)sampleRate);
            return Mathf.Clamp01(bufferDuration / streamBufferDuration);
        }

        public int GetQueueSize()
        {
            return audioBufferQueue.Count;
        }

        public void ClearBuffer()
        {
            audioBufferQueue.Clear();
            currentBufferPosition = 0;
        }
    }
}
