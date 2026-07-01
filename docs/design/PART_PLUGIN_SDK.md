# PLUGIN SDK

## Overview

Plugin SDK allows community to write plugins for Spotify, Notion, Discord, Slack, Chrome, VSCode, Photoshop, Blender, Unity, creating an ecosystem instead of just an application.

---

## 1. Plugin Architecture

```csharp
// PluginSDK.cs
public class PluginSDK : MonoBehaviour
{
    [Header("Plugin System")]
    [SerializeField] private Dictionary<string, Plugin> loadedPlugins;
    
    [Header("Plugin API")]
    [SerializeField] private PluginAPI pluginAPI;
    
    public void LoadPlugin(string pluginPath)
    {
        // Load plugin from file
        Plugin plugin = PluginLoader.Load(pluginPath);
        
        // Initialize plugin
        plugin.Initialize(pluginAPI);
        
        // Register plugin
        loadedPlugins[plugin.id] = plugin;
    }
    
    public void UnloadPlugin(string pluginId)
    {
        if (loadedPlugins.TryGetValue(pluginId, out Plugin plugin))
        {
            plugin.Shutdown();
            loadedPlugins.Remove(pluginId);
        }
    }
    
    public Plugin GetPlugin(string pluginId)
    {
        return loadedPlugins.TryGetValue(pluginId, out Plugin plugin) ? plugin : null;
    }
}
```

---

## 2. Plugin API

```csharp
// PluginAPI.cs
public class PluginAPI
{
    // Core AI Companion APIs
    public AIAPI AI { get; }
    public VoiceAPI Voice { get; }
    public AnimationAPI Animation { get; }
    public MemoryAPI Memory { get; }
    public PersonalityAPI Personality { get; }
    
    // Platform APIs
    public DesktopAPI Desktop { get; }
    public MobileAPI Mobile { get; }
    public XRAPI XR { get; }
    public CloudAPI Cloud { get; }
    
    // External Service APIs
    public SpotifyAPI Spotify { get; }
    public NotionAPI Notion { get; }
    public DiscordAPI Discord { get; }
    public SlackAPI Slack { get; }
    public ChromeAPI Chrome { get; }
    public VSCodeAPI VSCode { get; }
    public PhotoshopAPI Photoshop { get; }
    public BlenderAPI Blender { get; }
    public UnityAPI Unity { get; }
}
```

---

## 3. Plugin Interface

```csharp
// IPlugin.cs
public interface IPlugin
{
    string id { get; }
    string name { get; }
    string version { get; }
    string author { get; }
    
    void Initialize(PluginAPI api);
    void Shutdown();
    void OnEnable();
    void OnDisable();
    void Update();
}
```

---

## 4. Example Plugins

```csharp
// SpotifyPlugin.cs
public class SpotifyPlugin : IPlugin
{
    public string id => "com.ai-companion.spotify";
    public string name => "Spotify Integration";
    public string version => "1.0.0";
    public string author => "AI Companion Team";
    
    private PluginAPI api;
    private SpotifyAPI spotify;
    
    public void Initialize(PluginAPI api)
    {
        this.api = api;
        this.spotify = api.Spotify;
        
        // Register commands
        api.AI.RegisterCommand("play_song", PlaySong);
        api.AI.RegisterCommand("pause_music", PauseMusic);
        api.AI.RegisterCommand("recommend_music", RecommendMusic);
    }
    
    public void Shutdown()
    {
        // Cleanup
    }
    
    public void OnEnable()
    {
        // Enable plugin
    }
    
    public void OnDisable()
    {
        // Disable plugin
    }
    
    public void Update()
    {
        // Update plugin
    }
    
    private void PlaySong(string songName)
    {
        spotify.Play(songName);
    }
    
    private void PauseMusic()
    {
        spotify.Pause();
    }
    
    private void RecommendMusic(string genre)
    {
        List<string> recommendations = spotify.GetRecommendations(genre);
        api.AI.SendMessage($"Here are some {genre} recommendations: {string.Join(", ", recommendations)}");
    }
}

// NotionPlugin.cs
public class NotionPlugin : IPlugin
{
    public string id => "com.ai-companion.notion";
    public string name => "Notion Integration";
    public string version => "1.0.0";
    public string author => "AI Companion Team";
    
    private PluginAPI api;
    private NotionAPI notion;
    
    public void Initialize(PluginAPI api)
    {
        this.api = api;
        this.notion = api.Notion;
        
        // Register commands
        api.AI.RegisterCommand("create_page", CreatePage);
        api.AI.RegisterCommand("search_pages", SearchPages);
        api.AI.RegisterCommand("add_task", AddTask);
    }
    
    public void Shutdown()
    {
        // Cleanup
    }
    
    public void OnEnable()
    {
        // Enable plugin
    }
    
    public void OnDisable()
    {
        // Disable plugin
    }
    
    public void Update()
    {
        // Update plugin
    }
    
    private void CreatePage(string title)
    {
        notion.CreatePage(title);
    }
    
    private void SearchPages(string query)
    {
        List<NotionPage> pages = notion.Search(query);
        api.AI.SendMessage($"Found {pages.Count} pages: {string.Join(", ", pages.Select(p => p.title))}");
    }
    
    private void AddTask(string task)
    {
        notion.AddTask(task);
    }
}
```

---

## 5. Plugin Distribution

```csharp
// PluginManager.cs
public class PluginManager : MonoBehaviour
{
    [Header("Plugin Registry")]
    [SerializeField] private string pluginRegistryURL = "https://plugins.ai-companion.com";
    
    [Header("Local Plugins")]
    [SerializeField] private string localPluginPath = "./Plugins";
    
    public async Task<List<PluginInfo>> GetAvailablePlugins()
    {
        // Fetch available plugins from registry
        using (HttpClient client = new HttpClient())
        {
            string json = await client.GetStringAsync(pluginRegistryURL + "/plugins");
            return JsonUtility.FromJson<List<PluginInfo>>(json);
        }
    }
    
    public async Task<Plugin> InstallPlugin(string pluginId)
    {
        // Download plugin from registry
        using (HttpClient client = new HttpClient())
        {
            byte[] pluginData = await client.GetByteArrayAsync(pluginRegistryURL + $"/plugins/{pluginId}/download");
            
            // Save to local
            string pluginPath = Path.Combine(localPluginPath, $"{pluginId}.plugin");
            File.WriteAllBytes(pluginPath, pluginData);
            
            // Load plugin
            return PluginLoader.Load(pluginPath);
        }
    }
}

public class PluginInfo
{
    public string id;
    public string name;
    public string version;
    public string author;
    public string description;
    public string downloadURL;
}
```

---

## Conclusion

Plugin SDK enables:
- **Community plugins** for Spotify, Notion, Discord, Slack, Chrome, VSCode, etc.
- **Extensible ecosystem** instead of single application
- **Plugin marketplace** for distribution
- **Plugin API** for easy integration

**Example**: User installs Spotify plugin → AI can play music, recommend songs, control playback.
