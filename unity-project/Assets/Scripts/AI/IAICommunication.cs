using System.Threading.Tasks;

namespace AICompanion.AI
{
    /// <summary>
    /// Interface for AI communication with backend services
    /// </summary>
    public interface IAICommunication
    {
        /// <summary>
        /// Initialize communication with backend
        /// </summary>
        /// <param name="endpoint">API endpoint URL</param>
        /// <param name="timeout">Request timeout in seconds</param>
        void Initialize(string endpoint, float timeout);

        /// <summary>
        /// Send request to AI service
        /// </summary>
        /// <param name="request">AI request data</param>
        /// <returns>AI response</returns>
        Task<AIResponse> SendRequestAsync(AIRequest request);

        /// <summary>
        /// Shutdown communication
        /// </summary>
        Task ShutdownAsync();

        /// <summary>
        /// Check if communication is ready
        /// </summary>
        bool IsReady { get; }
    }
}