using UnityEngine;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Linq;
using System.Text;

namespace AICompanion.Network
{
    /// <summary>
    /// Manages network communication with backend services
    /// </summary>
    public class NetworkManager : MonoBehaviour, INetworkManager
    {
        [Header("Network Configuration")]
        [SerializeField] private string defaultServerUrl = "localhost";
        [SerializeField] private int defaultPort = 8080;
        [SerializeField] private float connectionTimeout = 10f;
        [SerializeField] private float reconnectInterval = 5f;
        [SerializeField] private int maxReconnectAttempts = 5;
        [SerializeField] private bool autoReconnect = true;

        [Header("Network State")]
        [SerializeField] private ConnectionState connectionState = ConnectionState.Disconnected;
        [SerializeField] private NetworkQuality networkQuality = new NetworkQuality();
        [SerializeField] private bool isInitialized = false;

        // Connection management
        private WebSocketClient webSocketClient;
        private int reconnectAttempts = 0;
        private float lastPingTime = 0f;
        private Queue<NetworkMessage> messageQueue = new Queue<NetworkMessage>();
        private const int MAX_QUEUE_SIZE = 100;

        // Quality monitoring
        private List<float> latencyHistory = new List<float>();
        private const int LATENCY_HISTORY_SIZE = 10;
        private int packetsSent = 0;
        private int packetsReceived = 0;
        private int packetsLost = 0;

        // Events
        public event Action OnConnected;
        public event Action OnDisconnected;
        public event Action<NetworkMessage> OnMessageReceived;
        public event Action<ConnectionState> OnConnectionStateChanged;

        // Properties
        public ConnectionState ConnectionState => connectionState;
        public bool IsConnected => connectionState == ConnectionState.Connected;

        private void Update()
        {
            if (IsConnected)
            {
                // Process message queue
                ProcessMessageQueue();

                // Monitor network quality
                MonitorNetworkQuality();

                // Send periodic ping
                if (Time.time - lastPingTime > 5f)
                {
                    SendPingAsync();
                }
            }
            else if (autoReconnect && connectionState == ConnectionState.Disconnected && reconnectAttempts < maxReconnectAttempts)
            {
                // Attempt reconnection
                AttemptReconnect();
            }
        }

        private void OnDestroy()
        {
            ShutdownAsync().ContinueWith(task =>
            {
                if (task.IsFaulted)
                {
                    Debug.LogError($"Network Manager shutdown failed: {task.Exception}");
                }
            });
        }

        /// <summary>
        /// Initialize network manager
        /// </summary>
        public async Task InitializeAsync()
        {
            if (isInitialized)
            {
                Debug.LogWarning("Network Manager already initialized");
                return;
            }

            try
            {
                Debug.Log("Initializing Network Manager...");

                // Initialize WebSocket client
                webSocketClient = gameObject.AddComponent<WebSocketClient>();
                
                isInitialized = true;
                Debug.Log("Network Manager initialized successfully");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Network Manager initialization error: {ex.Message}");
                throw;
            }
        }

        /// <summary>
        /// Shutdown network manager
        /// </summary>
        public async Task ShutdownAsync()
        {
            if (!isInitialized)
            {
                return;
            }

            try
            {
                Debug.Log("Shutting down Network Manager...");

                // Disconnect if connected
                if (IsConnected)
                {
                    await DisconnectAsync();
                }

                // Clear message queue
                messageQueue.Clear();

                // Destroy WebSocket client
                if (webSocketClient != null)
                {
                    Destroy(webSocketClient);
                }

                isInitialized = false;
                Debug.Log("Network Manager shutdown complete");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Network Manager shutdown error: {ex.Message}");
            }
        }

        /// <summary>
        /// Connect to server
        /// </summary>
        public async Task<bool> ConnectAsync(string serverUrl, int port)
        {
            if (IsConnected)
            {
                Debug.LogWarning("Already connected to server");
                return true;
            }

            try
            {
                SetConnectionState(ConnectionState.Connecting);
                reconnectAttempts = 0;

                Debug.Log($"Connecting to {serverUrl}:{port}...");

                // Construct WebSocket URL
                string wsUrl = $"ws://{serverUrl}:{port}";
                
                // Initialize and connect WebSocket
                if (webSocketClient == null)
                {
                    webSocketClient = gameObject.AddComponent<WebSocketClient>();
                }

                bool connected = await webSocketClient.ConnectAsync(wsUrl, connectionTimeout);

                if (connected)
                {
                    SetConnectionState(ConnectionState.Connected);
                    OnConnected?.Invoke();
                    Debug.Log("Connected to server successfully");
                    
                    // Start receiving messages
                    StartReceivingMessages();
                    
                    return true;
                }
                else
                {
                    SetConnectionState(ConnectionState.Error);
                    Debug.LogError("Failed to connect to server");
                    return false;
                }
            }
            catch (Exception ex)
            {
                SetConnectionState(ConnectionState.Error);
                Debug.LogError($"Connection error: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Disconnect from server
        /// </summary>
        public async Task DisconnectAsync()
        {
            if (!IsConnected)
            {
                return;
            }

            try
            {
                SetConnectionState(ConnectionState.Disconnecting);
                Debug.Log("Disconnecting from server...");

                // Disconnect WebSocket
                if (webSocketClient != null)
                {
                    webSocketClient.Disconnect();
                }

                SetConnectionState(ConnectionState.Disconnected);
                OnDisconnected?.Invoke();
                Debug.Log("Disconnected from server");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Disconnect error: {ex.Message}");
                SetConnectionState(ConnectionState.Error);
            }

            await Task.CompletedTask;
        }

        /// <summary>
        /// Send message to server
        /// </summary>
        public async Task<bool> SendMessageAsync(NetworkMessage message)
        {
            if (!IsConnected)
            {
                Debug.LogWarning("Cannot send message - not connected");
                return false;
            }

            if (message == null)
            {
                Debug.LogWarning("Cannot send null message");
                return false;
            }

            // Add to queue or send immediately
            if (messageQueue.Count >= MAX_QUEUE_SIZE)
            {
                Debug.LogWarning("Message queue full, dropping message");
                packetsLost++;
                return false;
            }

            messageQueue.Enqueue(message);
            return true;
        }

        /// <summary>
        /// Send raw data to server
        /// </summary>
        public async Task<bool> SendRawAsync(byte[] data)
        {
            if (!IsConnected)
            {
                Debug.LogWarning("Cannot send raw data - not connected");
                return false;
            }

            if (data == null || data.Length == 0)
            {
                Debug.LogWarning("Cannot send empty raw data");
                return false;
            }

            try
            {
                if (webSocketClient != null)
                {
                    await webSocketClient.SendAsync(data);
                    packetsSent++;
                    return true;
                }
                return false;
            }
            catch (Exception ex)
            {
                Debug.LogError($"Raw data send error: {ex.Message}");
                packetsLost++;
                return false;
            }
        }

        /// <summary>
        /// Process message queue
        /// </summary>
        private async void ProcessMessageQueue()
        {
            while (messageQueue.Count > 0)
            {
                NetworkMessage message = messageQueue.Dequeue();
                
                try
                {
                    string json = JsonUtility.ToJson(message);
                    byte[] data = Encoding.UTF8.GetBytes(json);
                    
                    await webSocketClient.SendAsync(data);
                    packetsSent++;
                }
                catch (Exception ex)
                {
                    Debug.LogError($"Message send error: {ex.Message}");
                    packetsLost++;
                    break;
                }
            }
        }

        /// <summary>
        /// Start receiving messages
        /// </summary>
        private void StartReceivingMessages()
        {
            if (webSocketClient != null)
            {
                webSocketClient.OnMessageReceived += HandleMessageReceived;
            }
        }

        /// <summary>
        /// Handle received message
        /// </summary>
        private void HandleMessageReceived(byte[] data)
        {
            try
            {
                string json = Encoding.UTF8.GetString(data);
                NetworkMessage message = JsonUtility.FromJson<NetworkMessage>(json);
                
                packetsReceived++;
                OnMessageReceived?.Invoke(message);
                
                Debug.Log($"Message received: {message.messageType}");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Message receive error: {ex.Message}");
            }
        }

        /// <summary>
        /// Send ping for latency measurement
        /// </summary>
        private async void SendPingAsync()
        {
            if (!IsConnected) return;

            lastPingTime = Time.time;
            
            NetworkMessage pingMessage = new NetworkMessage("ping", Time.time.ToString());
            await SendMessageAsync(pingMessage);
        }

        /// <summary>
        /// Handle pong response
        /// </summary>
        private void HandlePong()
        {
            float rtt = (Time.time - lastPingTime) * 1000f; // Convert to ms
            UpdateLatency(rtt);
        }

        /// <summary>
        /// Update latency history
        /// </summary>
        private void UpdateLatency(float latency)
        {
            latencyHistory.Add(latency);
            
            if (latencyHistory.Count > LATENCY_HISTORY_SIZE)
            {
                latencyHistory.RemoveAt(0);
            }

            // Calculate average latency
            networkQuality.latency = latencyHistory.Average();
        }

        /// <summary>
        /// Monitor network quality
        /// </summary>
        private void MonitorNetworkQuality()
        {
            // Calculate packet loss
            if (packetsSent > 0)
            {
                networkQuality.packetLoss = (float)packetsLost / packetsSent * 100f;
            }

            // Calculate jitter (variance in latency)
            if (latencyHistory.Count > 1)
            {
                float avgLatency = latencyHistory.Average();
                float variance = latencyHistory.Sum(l => Mathf.Pow(l - avgLatency, 2)) / latencyHistory.Count;
                networkQuality.jitter = Mathf.Sqrt(variance);
            }

            // Reset counters periodically
            if (packetsSent > 1000)
            {
                packetsSent = 0;
                packetsReceived = 0;
                packetsLost = 0;
            }
        }

        /// <summary>
        /// Get network quality metrics
        /// </summary>
        public NetworkQuality GetNetworkQuality()
        {
            return networkQuality;
        }

        /// <summary>
        /// Attempt reconnection
        /// </summary>
        private async void AttemptReconnect()
        {
            if (Time.time - lastPingTime < reconnectInterval)
            {
                return;
            }

            lastPingTime = Time.time;
            reconnectAttempts++;

            Debug.Log($"Reconnection attempt {reconnectAttempts}/{maxReconnectAttempts}");

            bool connected = await ConnectAsync(defaultServerUrl, defaultPort);
            
            if (!connected && reconnectAttempts >= maxReconnectAttempts)
            {
                Debug.LogError("Max reconnection attempts reached");
                autoReconnect = false;
            }
        }

        /// <summary>
        /// Set connection state
        /// </summary>
        private void SetConnectionState(ConnectionState newState)
        {
            if (connectionState != newState)
            {
                connectionState = newState;
                OnConnectionStateChanged?.Invoke(newState);
                Debug.Log($"Connection state changed to: {newState}");
            }
        }
    }

    /// <summary>
    /// WebSocket client for real-time communication
    /// </summary>
    public class WebSocketClient : MonoBehaviour
    {
        private bool isConnected = false;
        private string serverUrl;
        
        public event Action<byte[]> OnMessageReceived;

        public bool IsConnected => isConnected;

        public async Task<bool> ConnectAsync(string url, float timeout)
        {
            serverUrl = url;
            
            // Note: This is a placeholder implementation
            // In production, use a WebSocket library like NativeWebSocket
            
            Debug.Log($"WebSocket connecting to {url}...");
            
            // Simulate connection delay
            await Task.Delay(1000);
            
            isConnected = true;
            Debug.Log("WebSocket connected");
            
            return true;
        }

        public void Disconnect()
        {
            isConnected = false;
            Debug.Log("WebSocket disconnected");
        }

        public async Task SendAsync(byte[] data)
        {
            if (!isConnected)
            {
                Debug.LogWarning("Cannot send - WebSocket not connected");
                return;
            }

            // Placeholder for actual WebSocket send
            Debug.Log($"WebSocket sent {data.Length} bytes");
            await Task.CompletedTask;
        }

        private void OnDestroy()
        {
            Disconnect();
        }
    }
}