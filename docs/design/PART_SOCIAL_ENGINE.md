# SOCIAL ENGINE

## Overview

Social Engine manages multiple relationships with different roles: friends, colleagues, family, boss, etc.

---

## 1. Relationship Management

```csharp
// SocialEngine.cs
public class SocialEngine : MonoBehaviour
{
    [Header("Relationships")]
    [SerializeField] private Dictionary<string, Relationship> relationships;
    
    public void AddRelationship(string personId, RelationshipType type)
    {
        relationships[personId] = new Relationship
        {
            personId = personId,
            type = type,
            intimacy = 0.5f,
            trust = 0.5f,
            history = new List<InteractionRecord>()
        };
    }
    
    public void UpdateRelationship(string personId, InteractionRecord record)
    {
        if (relationships.TryGetValue(personId, out Relationship rel))
        {
            rel.history.Add(record);
            rel.intimacy = Mathf.Clamp01(rel.intimacy + record.intimacyDelta);
            rel.trust = Mathf.Clamp01(rel.trust + record.trustDelta);
        }
    }
    
    public string AdaptResponse(string personId, string baseResponse)
    {
        if (!relationships.TryGetValue(personId, out Relationship rel))
        {
            return baseResponse;
        }
        
        switch (rel.type)
        {
            case RelationshipType.Friend:
                return CasualResponse(baseResponse);
            case RelationshipType.Colleague:
                return ProfessionalResponse(baseResponse);
            case RelationshipType.Family:
                return PersonalResponse(baseResponse);
            case RelationshipType.Boss:
                return FormalResponse(baseResponse);
            default:
                return baseResponse;
        }
    }
}

public class Relationship
{
    public string personId;
    public RelationshipType type;
    public float intimacy;
    public float trust;
    public List<InteractionRecord> history;
}

public enum RelationshipType
{
    Friend,
    Colleague,
    Family,
    Boss,
    Acquaintance,
    Stranger
}
```

---

## 2. Social Context

```csharp
// SocialContextSystem.cs
public class SocialContextSystem : MonoBehaviour
{
    [Header("Social Context")]
    [SerializeField] private SocialContext currentContext;
    
    public void DetectSocialContext()
    {
        // Detect current social context
        currentContext = new SocialContext
        {
            setting = DetectSetting(),
            participants = DetectParticipants(),
            atmosphere = DetectAtmosphere()
        };
    }
    
    public CommunicationStyle AdaptCommunicationStyle()
    {
        switch (currentContext.setting)
        {
            case SocialSetting.Casual:
                return CommunicationStyle.Casual;
            case SocialSetting.Professional:
                return CommunicationStyle.Professional;
            case SocialSetting.Formal:
                return CommunicationStyle.Formal;
            default:
                return CommunicationStyle.Neutral;
        }
    }
}

public class SocialContext
{
    public SocialSetting setting;
    public List<string> participants;
    public Atmosphere atmosphere;
}

public enum SocialSetting
{
    Casual,
    Professional,
    Formal,
    Intimate
}

public enum CommunicationStyle
{
    Casual,
    Professional,
    Formal,
    Intimate
}
```

---

## 3. Social Memory

```csharp
// SocialMemorySystem.cs
public class SocialMemorySystem : MonoBehaviour
{
    [Header("Social Memory")]
    [SerializeField] private Dictionary<string, List<SocialMemory>> socialMemories;
    
    public void RecordSocialInteraction(string personId, SocialMemory memory)
    {
        if (!socialMemories.ContainsKey(personId))
        {
            socialMemories[personId] = new List<SocialMemory>();
        }
        
        socialMemories[personId].Add(memory);
    }
    
    public List<SocialMemory> GetSocialMemories(string personId)
    {
        return socialMemories.TryGetValue(personId, out List<SocialMemory> memories) 
            ? memories 
            : new List<SocialMemory>();
    }
    
    public string RecallSharedExperience(string personId)
    {
        List<SocialMemory> memories = GetSocialMemories(personId);
        
        if (memories.Count > 0)
        {
            return $"Nhớ lần đó anh em {memories[0].description}";
        }
        
        return null;
    }
}

public class SocialMemory
{
    public string personId;
    public string description;
    public float timestamp;
    public float importance;
}
```

---

## Conclusion

Social Engine enables AI to:
- **Manage multiple relationships** with different roles
- **Adapt communication style** based on relationship type
- **Remember shared experiences** with each person
- **Maintain social context** awareness

**Example**: AI talks casually with friends, professionally with colleagues, personally with family.
