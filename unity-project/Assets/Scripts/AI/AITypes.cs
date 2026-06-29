using UnityEngine;
using System;

namespace AICompanion.AI
{
    /// <summary>
    /// AI request data structure
    /// </summary>
    [Serializable]
    public class AIRequest
    {
        public RequestType type;
        public string data;
        public RequestContext context;
        public long timestamp;
    }

    /// <summary>
    /// Request type enumeration
    /// </summary>
    public enum RequestType
    {
        Text,
        Voice,
        Vision
    }

    /// <summary>
    /// Request context data structure
    /// </summary>
    [Serializable]
    public class RequestContext
    {
        public EmotionState currentEmotion;
        public PersonalityConfig personality;
        public long timestamp;
    }
}