using UnityEngine;
using AICompanion.Core.Interfaces;

namespace AICompanion.Core.Managers
{
    /// <summary>
    /// Main game manager - follows Single Responsibility Principle
    /// Manages game lifecycle and core systems initialization
    /// </summary>
    public class GameManager : MonoBehaviour
    {
        private static GameManager _instance;
        public static GameManager Instance
        {
            get
            {
                if (_instance == null)
                {
                    GameObject go = new GameObject("GameManager");
                    _instance = go.AddComponent<GameManager>();
                    DontDestroyOnLoad(go);
                }
                return _instance;
            }
        }

        [Header("Core Systems")]
        [SerializeField] private IARSessionManager arSessionManager;
        [SerializeField] private ICharacterLoader characterLoader;
        [SerializeField] private ILightingController lightingController;

        public bool IsInitialized { get; private set; }

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }

            _instance = this;
            DontDestroyOnLoad(gameObject);
        }

        private void Start()
        {
            InitializeSystems();
        }

        private void InitializeSystems()
        {
            // Initialize core systems
            Debug.Log("Initializing AI Companion Systems...");
            
            // AR Session Manager
            if (arSessionManager != null)
            {
                arSessionManager.OnARSessionStarted += OnARSessionStarted;
                arSessionManager.OnARSessionStopped += OnARSessionStopped;
            }

            // Character Loader
            if (characterLoader != null)
            {
                characterLoader.OnCharacterLoaded += OnCharacterLoaded;
                characterLoader.OnLoadingFailed += OnLoadingFailed;
            }

            IsInitialized = true;
            Debug.Log("AI Companion Systems initialized successfully");
        }

        private void OnDestroy()
        {
            // Cleanup event subscriptions
            if (arSessionManager != null)
            {
                arSessionManager.OnARSessionStarted -= OnARSessionStarted;
                arSessionManager.OnARSessionStopped -= OnARSessionStopped;
            }

            if (characterLoader != null)
            {
                characterLoader.OnCharacterLoaded -= OnCharacterLoaded;
                characterLoader.OnLoadingFailed -= OnLoadingFailed;
            }
        }

        private void OnARSessionStarted()
        {
            Debug.Log("AR Session started");
        }

        private void OnARSessionStopped()
        {
            Debug.Log("AR Session stopped");
        }

        private void OnCharacterLoaded(GameObject character)
        {
            Debug.Log($"Character loaded: {character.name}");
        }

        private void OnLoadingFailed(string error)
        {
            Debug.LogError($"Character loading failed: {error}");
        }

        public void SetARSessionManager(IARSessionManager manager)
        {
            arSessionManager = manager;
        }

        public void SetCharacterLoader(ICharacterLoader loader)
        {
            characterLoader = loader;
        }

        public void SetLightingController(ILightingController controller)
        {
            lightingController = controller;
        }
    }
}
