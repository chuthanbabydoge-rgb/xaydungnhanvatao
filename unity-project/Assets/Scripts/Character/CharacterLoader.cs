using System;
using System.Collections;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.AddressableAssets;
using UnityEngine.ResourceManagement.AsyncOperations;
using AICompanion.Core.Interfaces;

namespace AICompanion.Character
{
    /// <summary>
    /// Character loader using Addressables - follows Single Responsibility Principle
    /// Handles loading and unloading of character assets
    /// </summary>
    public class CharacterLoader : MonoBehaviour, ICharacterLoader
    {
        public event Action<float> OnLoadingProgress;
        public event Action<GameObject> OnCharacterLoaded;
        public event Action<string> OnLoadingFailed;

        [Header("Loading Settings")]
        [SerializeField] private float loadingDelay = 0.1f;
        [SerializeField] private bool instantiateOnLoad = true;

        private GameObject currentCharacter;
        private AsyncOperationHandle<GameObject> currentLoadOperation;

        public bool IsCharacterLoaded(string characterId)
        {
            return currentCharacter != null && currentCharacter.name == characterId;
        }

        public GameObject GetLoadedCharacter(string characterId)
        {
            if (IsCharacterLoaded(characterId))
            {
                return currentCharacter;
            }
            return null;
        }

        public async Task<GameObject> LoadCharacterAsync(string characterId)
        {
            try
            {
                // Load character from Addressables
                currentLoadOperation = Addressables.LoadAssetAsync<GameObject>(characterId);
                
                // Monitor progress
                while (!currentLoadOperation.IsDone)
                {
                    float progress = currentLoadOperation.PercentComplete;
                    OnLoadingProgress?.Invoke(progress);
                    await Task.Yield();
                }

                if (currentLoadOperation.Status == AsyncOperationStatus.Succeeded)
                {
                    GameObject characterPrefab = currentLoadOperation.Result;
                    
                    if (instantiateOnLoad)
                    {
                        currentCharacter = Instantiate(characterPrefab);
                        currentCharacter.name = characterId;
                        
                        // Setup character components
                        SetupCharacterComponents(currentCharacter);
                        
                        OnCharacterLoaded?.Invoke(currentCharacter);
                        return currentCharacter;
                    }
                    else
                    {
                        OnCharacterLoaded?.Invoke(characterPrefab);
                        return characterPrefab;
                    }
                }
                else
                {
                    string error = $"Failed to load character: {characterId}";
                    OnLoadingFailed?.Invoke(error);
                    return null;
                }
            }
            catch (Exception ex)
            {
                string error = $"Exception loading character {characterId}: {ex.Message}";
                OnLoadingFailed?.Invoke(error);
                return null;
            }
        }

        public void UnloadCharacter(GameObject character)
        {
            if (character == null) return;

            if (currentCharacter == character)
            {
                Destroy(currentCharacter);
                currentCharacter = null;
            }

            // Release Addressable asset
            if (currentLoadOperation.IsValid())
            {
                Addressables.Release(currentLoadOperation);
            }
        }

        private void SetupCharacterComponents(GameObject character)
        {
            // Ensure character has required components
            if (character.GetComponent<Animator>() == null)
            {
                character.AddComponent<Animator>();
            }

            if (character.GetComponent<Rigidbody>() == null)
            {
                Rigidbody rb = character.AddComponent<Rigidbody>();
                rb.useGravity = true;
                rb.isKinematic = false;
            }

            if (character.GetComponent<CapsuleCollider>() == null)
            {
                CapsuleCollider collider = character.AddComponent<CapsuleCollider>();
                collider.height = 2f;
                collider.radius = 0.5f;
                collider.center = new Vector3(0, 1f, 0);
            }
        }

        private void OnDestroy()
        {
            // Cleanup on destroy
            if (currentCharacter != null)
            {
                Destroy(currentCharacter);
            }

            if (currentLoadOperation.IsValid())
            {
                Addressables.Release(currentLoadOperation);
            }
        }
    }
}
