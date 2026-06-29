using UnityEngine;
using System;
using System.Threading.Tasks;
using System.Collections.Generic;

namespace AICompanion.AI
{
    /// <summary>
    /// Main AI companion controller managing AI behavior, communication, and state
    /// </summary>
    public class AICompanionController : MonoBehaviour, IAIController
    {
        [Header("AI Configuration")]
        [SerializeField] private string apiEndpoint = "http://localhost:8000/api/v1/ai";
        [SerializeField] private float requestTimeout = 30f;
        [SerializeField] private bool enableVoiceInput = true;
        [SerializeField] private bool enableVisionInput = true;

        [Header("AI State")]
        [SerializeField] private EmotionState currentEmotion;
        [SerializeField] private PersonalityConfig personality;
        [SerializeField] private bool isInitialized = false;
        [SerializeField] private bool isProcessing = false;

        // Dependencies
        private IAICommunication aiCommunication;
        private Queue<AIRequest> requestQueue = new Queue<AIRequest>();
        private const int MAX_QUEUE_SIZE = 10;

        // Events
        public event Action<AIResponse> OnAIResponse;
        public event Action<EmotionState> OnEmotionChanged;
        public event Action<string> OnAnimationRequested;

        // Properties
        public EmotionState CurrentEmotion => currentEmotion;
        public bool IsInitialized => isInitialized;
        public bool IsProcessing => isProcessing;

        private void Awake()
        {
            InitializeDefaults();
        }

        private void Start()
        {
            InitializeAsync().ContinueWith(task =>
            {
                if (task.IsFaulted)
                {
                    Debug.LogError($"AI Controller initialization failed: {task.Exception}");
                }
            });
        }

        private void Update()
        {
            ProcessRequestQueue();
            UpdateEmotionDecay();
        }

        private void OnDestroy()
        {
            ShutdownAsync().ContinueWith(task =>
            {
                if (task.IsFaulted)
                {
                    Debug.LogError($"AI Controller shutdown failed: {task.Exception}");
                }
            });
        }

        /// <summary>
        /// Initialize default values
        /// </summary>
        private void InitializeDefaults()
        {
            currentEmotion = new EmotionState();
            personality = new PersonalityConfig();
            
            // Create AI communication handler
            aiCommunication = gameObject.AddComponent<AICommunication>();
            if (aiCommunication is IAICommunication comm)
            {
                comm.Initialize(apiEndpoint, requestTimeout);
            }
        }

        /// <summary>
        /// Initialize AI controller
        /// </summary>
        public async Task InitializeAsync()
        {
            if (isInitialized)
            {
                Debug.LogWarning("AI Controller already initialized");
                return;
            }

            try
            {
                Debug.Log("Initializing AI Controller...");

                // Initialize communication
                if (aiCommunication != null)
                {
                    await aiCommunication.InitializeAsync();
                }

                // Load saved personality if available
                await LoadPersonalityAsync();

                // Load saved emotion state if available
                await LoadEmotionStateAsync();

                isInitialized = true;
                Debug.Log("AI Controller initialized successfully");
            }
            catch (Exception ex)
            {
                Debug.LogError($"AI Controller initialization error: {ex.Message}");
                throw;
            }
        }

        /// <summary>
        /// Shutdown AI controller
        /// </summary>
        public async Task ShutdownAsync()
        {
            if (!isInitialized)
            {
                return;
            }

            try
            {
                Debug.Log("Shutting down AI Controller...");

                // Save current state
                await SaveEmotionStateAsync();
                await SavePersonalityAsync();

                // Shutdown communication
                if (aiCommunication != null)
                {
                    await aiCommunication.ShutdownAsync();
                }

                // Clear queue
                requestQueue.Clear();

                isInitialized = false;
                Debug.Log("AI Controller shutdown complete");
            }
            catch (Exception ex)
            {
                Debug.LogError($"AI Controller shutdown error: {ex.Message}");
            }
        }

        /// <summary>
        /// Send user message to AI for processing
        /// </summary>
        public async Task<AIResponse> SendMessageAsync(string message)
        {
            if (!isInitialized)
            {
                Debug.LogWarning("AI Controller not initialized");
                return CreateErrorResponse("AI Controller not initialized");
            }

            if (string.IsNullOrEmpty(message))
            {
                Debug.LogWarning("Empty message received");
                return CreateErrorResponse("Empty message");
            }

            var request = new AIRequest
            {
                type = RequestType.Text,
                data = message,
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            };

            return await ProcessRequestAsync(request);
        }

        /// <summary>
        /// Send user voice audio to AI for processing
        /// </summary>
        public async Task<AIResponse> SendVoiceAsync(byte[] audioData)
        {
            if (!enableVoiceInput)
            {
                Debug.LogWarning("Voice input is disabled");
                return CreateErrorResponse("Voice input disabled");
            }

            if (!isInitialized)
            {
                Debug.LogWarning("AI Controller not initialized");
                return CreateErrorResponse("AI Controller not initialized");
            }

            if (audioData == null || audioData.Length == 0)
            {
                Debug.LogWarning("Empty audio data received");
                return CreateErrorResponse("Empty audio data");
            }

            var request = new AIRequest
            {
                type = RequestType.Voice,
                data = Convert.ToBase64String(audioData),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            };

            return await ProcessRequestAsync(request);
        }

        /// <summary>
        /// Send vision data to AI for processing
        /// </summary>
        public async Task<AIResponse> SendVisionAsync(byte[] imageData)
        {
            if (!enableVisionInput)
            {
                Debug.LogWarning("Vision input is disabled");
                return CreateErrorResponse("Vision input disabled");
            }

            if (!isInitialized)
            {
                Debug.LogWarning("AI Controller not initialized");
                return CreateErrorResponse("AI Controller not initialized");
            }

            if (imageData == null || imageData.Length == 0)
            {
                Debug.LogWarning("Empty image data received");
                return CreateErrorResponse("Empty image data");
            }

            var request = new AIRequest
            {
                type = RequestType.Vision,
                data = Convert.ToBase64String(imageData),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            };

            return await ProcessRequestAsync(request);
        }

        /// <summary>
        /// Process AI request
        /// </summary>
        private async Task<AIResponse> ProcessRequestAsync(AIRequest request)
        {
            if (isProcessing)
            {
                // Queue the request if not already at capacity
                if (requestQueue.Count < MAX_QUEUE_SIZE)
                {
                    requestQueue.Enqueue(request);
                    Debug.Log($"Request queued (Queue size: {requestQueue.Count})");
                }
                else
                {
                    Debug.LogWarning("Request queue full, dropping request");
                    return CreateErrorResponse("Request queue full");
                }
                return null;
            }

            isProcessing = true;

            try
            {
                Debug.Log($"Processing {request.type} request...");

                // Add context to request
                request.context = new RequestContext
                {
                    currentEmotion = currentEmotion,
                    personality = personality,
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
                };

                // Send to AI service
                AIResponse response = await aiCommunication.SendRequestAsync(request);

                if (response != null)
                {
                    // Process response
                    await ProcessAIResponseAsync(response);
                }

                return response;
            }
            catch (Exception ex)
            {
                Debug.LogError($"Request processing error: {ex.Message}");
                return CreateErrorResponse(ex.Message);
            }
            finally
            {
                isProcessing = false;
            }
        }

        /// <summary>
        /// Process AI response
        /// </summary>
        private async Task ProcessAIResponseAsync(AIResponse response)
        {
            try
            {
                // Update emotion if provided
                if (!string.IsNullOrEmpty(response.emotion))
                {
                    UpdateEmotion(response.emotion);
                }

                // Trigger animation if requested
                if (!string.IsNullOrEmpty(response.animation))
                {
                    OnAnimationRequested?.Invoke(response.animation);
                }

                // Notify listeners
                OnAIResponse?.Invoke(response);

                Debug.Log($"AI Response processed: {response.text}");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Response processing error: {ex.Message}");
            }
        }

        /// <summary>
        /// Process request queue
        /// </summary>
        private void ProcessRequestQueue()
        {
            if (isProcessing || requestQueue.Count == 0)
            {
                return;
            }

            var request = requestQueue.Dequeue();
            _ = ProcessRequestAsync(request);
        }

        /// <summary>
        /// Update emotion state
        /// </summary>
        private void UpdateEmotion(string emotionString)
        {
            if (Enum.TryParse<EmotionType>(emotionString, true, out EmotionType newEmotion))
            {
                currentEmotion.primaryEmotion = newEmotion;
                currentEmotion.timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
                
                // Trigger emotion change event
                OnEmotionChanged?.Invoke(currentEmotion);
                
                Debug.Log($"Emotion updated to: {newEmotion}");
            }
            else
            {
                Debug.LogWarning($"Unknown emotion: {emotionString}");
            }
        }

        /// <summary>
        /// Update emotion decay over time
        /// </summary>
        private void UpdateEmotionDecay()
        {
            // Gradually return to neutral if no strong emotion
            if (currentEmotion.emotionIntensity > 0.1f)
            {
                currentEmotion.emotionIntensity = Mathf.Max(
                    0.1f, 
                    currentEmotion.emotionIntensity - Time.deltaTime * 0.05f
                );
            }

            // Update mood slowly
            currentEmotion.mood = Mathf.Clamp(
                currentEmotion.mood + Time.deltaTime * 0.01f * (UnityEngine.Random.value - 0.5f),
                0f, 
                1f
            );
        }

        /// <summary>
        /// Get current AI emotion state
        /// </summary>
        public EmotionState GetCurrentEmotion()
        {
            return currentEmotion;
        }

        /// <summary>
        /// Set AI personality parameters
        /// </summary>
        public void SetPersonality(PersonalityConfig newPersonality)
        {
            if (newPersonality == null)
            {
                Debug.LogWarning("Null personality provided");
                return;
            }

            personality = newPersonality;
            Debug.Log("Personality updated");
        }

        /// <summary>
        /// Load personality from storage
        /// </summary>
        private async Task LoadPersonalityAsync()
        {
            try
            {
                string filePath = GetPersonalityFilePath();
                
                if (System.IO.File.Exists(filePath))
                {
                    string json = System.IO.File.ReadAllText(filePath);
                    personality = JsonUtility.FromJson<PersonalityConfig>(json);
                    Debug.Log($"Personality loaded from {filePath}");
                }
                else
                {
                    Debug.Log("No saved personality found, using defaults");
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Failed to load personality: {e.Message}");
                // Keep default personality on error
            }
            
            await Task.CompletedTask;
        }

        /// <summary>
        /// Save personality to storage
        /// </summary>
        private async Task SavePersonalityAsync()
        {
            try
            {
                string filePath = GetPersonalityFilePath();
                string directory = System.IO.Path.GetDirectoryName(filePath);
                
                // Ensure directory exists
                if (!System.IO.Directory.Exists(directory))
                {
                    System.IO.Directory.CreateDirectory(directory);
                }
                
                string json = JsonUtility.ToJson(personality, true);
                System.IO.File.WriteAllText(filePath, json);
                Debug.Log($"Personality saved to {filePath}");
            }
            catch (Exception e)
            {
                Debug.LogError($"Failed to save personality: {e.Message}");
            }
            
            await Task.CompletedTask;
        }

        /// <summary>
        /// Load emotion state from storage
        /// </summary>
        private async Task LoadEmotionStateAsync()
        {
            try
            {
                string filePath = GetEmotionStateFilePath();
                
                if (System.IO.File.Exists(filePath))
                {
                    string json = System.IO.File.ReadAllText(filePath);
                    currentEmotion = JsonUtility.FromJson<EmotionState>(json);
                    Debug.Log($"Emotion state loaded from {filePath}");
                }
                else
                {
                    Debug.Log("No saved emotion state found, using defaults");
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Failed to load emotion state: {e.Message}");
                // Keep default emotion state on error
            }
            
            await Task.CompletedTask;
        }

        /// <summary>
        /// Save emotion state to storage
        /// </summary>
        private async Task SaveEmotionStateAsync()
        {
            try
            {
                string filePath = GetEmotionStateFilePath();
                string directory = System.IO.Path.GetDirectoryName(filePath);
                
                // Ensure directory exists
                if (!System.IO.Directory.Exists(directory))
                {
                    System.IO.Directory.CreateDirectory(directory);
                }
                
                string json = JsonUtility.ToJson(currentEmotion, true);
                System.IO.File.WriteAllText(filePath, json);
                Debug.Log($"Emotion state saved to {filePath}");
            }
            catch (Exception e)
            {
                Debug.LogError($"Failed to save emotion state: {e.Message}");
            }
            
            await Task.CompletedTask;
        }

        /// <summary>
        /// Get file path for personality storage
        /// </summary>
        private string GetPersonalityFilePath()
        {
            string persistentPath = Application.persistentDataPath;
            return System.IO.Path.Combine(persistentPath, "AICompanion", "personality.json");
        }

        /// <summary>
        /// Get file path for emotion state storage
        /// </summary>
        private string GetEmotionStateFilePath()
        {
            string persistentPath = Application.persistentDataPath;
            return System.IO.Path.Combine(persistentPath, "AICompanion", "emotion_state.json");
        }

        /// <summary>
        /// Create error response
        /// </summary>
        private AIResponse CreateErrorResponse(string errorMessage)
        {
            return new AIResponse
            {
                text = $"Error: {errorMessage}",
                emotion = "Confused",
                animation = "idle",
                confidence = 0f,
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            };
        }
    }

    /// <summary>
    /// AI request data structure
    /// </summary>
    [Serializable]
    internal class AIRequest
    {
        public RequestType type;
        public string data;
        public RequestContext context;
        public long timestamp;
    }

    /// <summary>
    /// Request type enumeration
    /// </summary>
    internal enum RequestType
    {
        Text,
        Voice,
        Vision
    }

    /// <summary>
    /// Request context data structure
    /// </summary>
    [Serializable]
    internal class RequestContext
    {
        public EmotionState currentEmotion;
        public PersonalityConfig personality;
        public long timestamp;
    }
}