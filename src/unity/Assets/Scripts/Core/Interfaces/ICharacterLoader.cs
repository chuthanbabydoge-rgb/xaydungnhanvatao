using System;
using System.Threading.Tasks;
using UnityEngine;

namespace AICompanion.Core.Interfaces
{
    /// <summary>
    /// Interface for character loading - follows Interface Segregation Principle
    /// </summary>
    public interface ICharacterLoader
    {
        event Action<float> OnLoadingProgress;
        event Action<GameObject> OnCharacterLoaded;
        event Action<string> OnLoadingFailed;
        
        Task<GameObject> LoadCharacterAsync(string characterId);
        void UnloadCharacter(GameObject character);
        bool IsCharacterLoaded(string characterId);
        GameObject GetLoadedCharacter(string characterId);
    }
}
