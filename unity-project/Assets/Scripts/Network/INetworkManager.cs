using UnityEngine;
using System;
using System.Threading.Tasks;

namespace AICompanion.Network
{
    /// <summary>
    /// Interface for network manager handling all network communications
    /// </summary>
    public interface INetworkManager
    {
        /// <summary>
        /// Event triggered when connection is established
        /// </summary>
        event Action OnConnected;

        /// <summary>
        /// Event triggered when connection is lost
        /// </summary>
        event Action OnDisconnected;

        /// <summary>
        /// Event triggered when message is received
        /// </summary>
        event Action<NetworkMessage> OnMessageReceived;

        /// <summary>
        /// Event triggered when connection state changes
        /// </summary>
        event Action<ConnectionState> OnConnectionStateChanged;

        /// <summary>
        /// Current connection state
        /// </summary>
        ConnectionState ConnectionState { get; }

        /// <summary>
        /// Check if connected
        /// </summary>
        bool IsConnected { get; }

        /// <summary>
        /// Connect to server
        /// </summary>
        /// <param name="serverUrl">Server URL</param>
        /// <param name="port">Server port</param>
        Task<bool> ConnectAsync(string serverUrl, int port);

        /// <summary>
        /// Disconnect from server
        /// </summary>
        Task DisconnectAsync();

        /// <summary>
        /// Send message to server
        /// </summary>
        /// <param name="message">Message to send</param>
        /// <returns>Send success status</returns>
        Task<bool> SendMessageAsync(NetworkMessage message);

        /// <summary>
        /// Send raw data to server
        /// </summary>
        /// <param name="data">Raw data bytes</param>
        /// <returns>Send success status</returns>
        Task<bool> SendRawAsync(byte[] data);

        /// <summary>
        /// Get connection quality metrics
        /// </summary>
        NetworkQuality GetNetworkQuality();

        /// <summary>
        /// Initialize network manager
        /// </summary>
        Task InitializeAsync();

        /// <summary>
        /// Shutdown network manager
        /// </summary>
        Task ShutdownAsync();
    }

    /// <summary>
    /// Connection state enumeration
    /// </summary>
    public enum ConnectionState
    {
        Disconnected,
        Connecting,
        Connected,
        Reconnecting,
        Disconnecting,
        Error
    }

    /// <summary>
    /// Network message data structure
    /// </summary>
    [Serializable]
    public class NetworkMessage
    {
        public string messageType;
        public string data;
        public long timestamp;
        public string messageId;
        public string correlationId;

        public NetworkMessage()
        {
            timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            messageId = Guid.NewGuid().ToString();
        }

        public NetworkMessage(string type, string messageData) : this()
        {
            messageType = type;
            data = messageData;
        }
    }

    /// <summary>
    /// Network quality metrics
    /// </summary>
    [Serializable]
    public class NetworkQuality
    {
        public float latency;          // Round-trip time in ms
        public float packetLoss;       // Packet loss percentage
        public float bandwidth;        // Available bandwidth in Mbps
        public float jitter;          // Jitter in ms
        public int signalStrength;    // Signal strength (0-100)

        public NetworkQuality()
        {
            latency = 0f;
            packetLoss = 0f;
            bandwidth = 0f;
            jitter = 0f;
            signalStrength = 100;
        }

        public bool IsGood()
        {
            return latency < 100f && packetLoss < 1f && signalStrength > 50;
        }
    }
}