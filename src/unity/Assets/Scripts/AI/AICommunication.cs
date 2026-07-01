using UnityEngine;
using System;
using System.Threading.Tasks;
using System.Text;
using System.Collections;
using UnityEngine.Networking;

namespace AICompanion.AI
{
    /// <summary>
    /// Handles communication with AI backend services via HTTP/WebSocket
    /// </summary>
    public class AICommunication : MonoBehaviour, IAICommunication
    {
        private string apiEndpoint;
        private float requestTimeout;
        private bool isInitialized = false;
        private bool isReady = false;

        // WebSocket connection for real-time communication
        private WebSocketClient webSocketClient;

        // Retry configuration
        private int maxRetries = 3;
        private float retryDelay = 1f;

        public bool IsReady => isReady;

        /// <summary>
        /// Initialize communication with backend
        /// </summary>
        public void Initialize(string endpoint, float timeout)
        {
            apiEndpoint = endpoint;
            requestTimeout = timeout;

            Debug.Log($"AI Communication initialized with endpoint: {apiEndpoint}");
            isInitialized = true;
        }

        /// <summary>
        /// Initialize async tasks
        /// </summary>
        public async Task InitializeAsync()
        {
            if (!isInitialized)
            {
                Debug.LogWarning("AI Communication not initialized");
                return;
            }

            try
            {
                // Test connection
                await TestConnectionAsync();

                // Initialize WebSocket for real-time updates
                InitializeWebSocket();

                isReady = true;
                Debug.Log("AI Communication ready");
            }
            catch (Exception ex)
            {
                Debug.LogError($"AI Communication initialization failed: {ex.Message}");
                throw;
            }
        }

        /// <summary>
        /// Test connection to backend
        /// </summary>
        private async Task TestConnectionAsync()
        {
            string healthEndpoint = $"{apiEndpoint}/health";
            
            using (UnityWebRequest request = UnityWebRequest.Get(healthEndpoint))
            {
                request.timeout = (int)requestTimeout;
                
                var operation = request.SendWebRequest();
                
                while (!operation.isDone)
                {
                    await Task.Yield();
                }

                if (request.result == UnityWebRequest.Result.Success)
                {
                    Debug.Log("Backend connection test successful");
                }
                else
                {
                    Debug.LogWarning($"Backend connection test failed: {request.error}");
                    // Continue anyway - backend might not be fully ready
                }
            }
        }

        /// <summary>
        /// Initialize WebSocket client
        /// </summary>
        private void InitializeWebSocket()
        {
            // Convert HTTP endpoint to WebSocket endpoint
            string wsEndpoint = apiEndpoint.Replace("http://", "ws://").Replace("https://", "wss://");
            wsEndpoint = $"{wsEndpoint}/ws";

            webSocketClient = gameObject.AddComponent<WebSocketClient>();
            webSocketClient.Initialize(wsEndpoint);

            Debug.Log($"WebSocket initialized: {wsEndpoint}");
        }

        /// <summary>
        /// Send request to AI service
        /// </summary>
        public async Task<AIResponse> SendRequestAsync(AIRequest request)
        {
            if (!isReady)
            {
                Debug.LogWarning("AI Communication not ready");
                return CreateErrorResponse("Communication not ready");
            }

            int attempt = 0;
            Exception lastException = null;

            while (attempt < maxRetries)
            {
                try
                {
                    return await SendRequestInternalAsync(request);
                }
                catch (Exception ex)
                {
                    lastException = ex;
                    attempt++;
                    Debug.LogWarning($"Request attempt {attempt} failed: {ex.Message}");

                    if (attempt < maxRetries)
                    {
                        await Task.Delay((int)(retryDelay * 1000 * attempt));
                    }
                }
            }

            Debug.LogError($"All request attempts failed: {lastException?.Message}");
            return CreateErrorResponse($"Request failed: {lastException?.Message}");
        }

        /// <summary>
        /// Internal request sending logic
        /// </summary>
        private async Task<AIResponse> SendRequestInternalAsync(AIRequest request)
        {
            string endpoint = $"{apiEndpoint}/process";
            
            // Serialize request to JSON
            string jsonRequest = JsonUtility.ToJson(request);
            
            using (UnityWebRequest webRequest = new UnityWebRequest(endpoint, "POST"))
            {
                byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonRequest);
                webRequest.uploadHandler = new UploadHandlerRaw(bodyRaw);
                webRequest.downloadHandler = new DownloadHandlerBuffer();
                webRequest.SetRequestHeader("Content-Type", "application/json");
                webRequest.timeout = (int)requestTimeout;

                // Send request
                var operation = webRequest.SendWebRequest();
                
                while (!operation.isDone)
                {
                    await Task.Yield();
                }

                if (webRequest.result == UnityWebRequest.Result.Success)
                {
                    string jsonResponse = webRequest.downloadHandler.text;
                    return ParseResponse(jsonResponse);
                }
                else
                {
                    throw new Exception($"HTTP Error: {webRequest.error}");
                }
            }
        }

        /// <summary>
        /// Parse JSON response
        /// </summary>
        private AIResponse ParseResponse(string jsonResponse)
        {
            try
            {
                AIResponse response = JsonUtility.FromJson<AIResponse>(jsonResponse);
                response.timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
                return response;
            }
            catch (Exception ex)
            {
                Debug.LogError($"Response parsing error: {ex.Message}");
                return CreateErrorResponse("Response parsing failed");
            }
        }

        /// <summary>
        /// Send real-time message via WebSocket
        /// </summary>
        public async Task SendWebSocketMessageAsync(string message)
        {
            if (webSocketClient != null && webSocketClient.IsConnected)
            {
                await webSocketClient.SendMessageAsync(message);
            }
            else
            {
                Debug.LogWarning("WebSocket not connected");
            }
        }

        /// <summary>
        /// Shutdown communication
        /// </summary>
        public async Task ShutdownAsync()
        {
            try
            {
                Debug.Log("Shutting down AI Communication...");

                // Close WebSocket
                if (webSocketClient != null)
                {
                    webSocketClient.Disconnect();
                    Destroy(webSocketClient);
                }

                isReady = false;
                isInitialized = false;

                Debug.Log("AI Communication shutdown complete");
            }
            catch (Exception ex)
            {
                Debug.LogError($"AI Communication shutdown error: {ex.Message}");
            }

            await Task.CompletedTask;
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
    /// Simple WebSocket client for real-time communication
    /// </summary>
    public class WebSocketClient : MonoBehaviour
    {
        private string endpoint;
        private bool isConnected = false;
        private WebSocket webSocket;

        public bool IsConnected => isConnected;

        public void Initialize(string wsEndpoint)
        {
            endpoint = wsEndpoint;
            Debug.Log($"WebSocket client initialized: {endpoint}");
        }

        public async Task ConnectAsync()
        {
            // Note: Unity doesn't have built-in WebSocket support in the core
            // This would typically use a WebSocket library like NativeWebSocket
            // For now, this is a placeholder implementation
            
            Debug.Log("WebSocket connection (placeholder)");
            isConnected = true;
            
            await Task.CompletedTask;
        }

        public void Disconnect()
        {
            isConnected = false;
            Debug.Log("WebSocket disconnected");
        }

        public async Task SendMessageAsync(string message)
        {
            if (!isConnected)
            {
                Debug.LogWarning("Cannot send message - WebSocket not connected");
                return;
            }

            // Placeholder for actual WebSocket send
            Debug.Log($"WebSocket message sent: {message}");
            await Task.CompletedTask;
        }

        private void OnDestroy()
        {
            Disconnect();
        }
    }

    /// <summary>
    /// Placeholder WebSocket interface
    /// In production, use a library like NativeWebSocket
    /// </summary>
    public class WebSocket
    {
        // Placeholder implementation
    }
}