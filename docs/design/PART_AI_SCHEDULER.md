# AI SCHEDULER ENGINE

## Overview

AI Scheduler manages time-based tasks and reminders (08:00 → Morning → Greeting → Coffee → Calendar → Reminder).

---

## 1. Task Scheduling

```csharp
// AISchedulerSystem.cs
public class AISchedulerSystem : MonoBehaviour
{
    [Header("Schedule")]
    [SerializeField] private Schedule schedule;
    
    [Header("Current Time")]
    [SerializeField] private float currentTimeOfDay;
    
    public void ExecuteSchedule()
    {
        // Get current time
        currentTimeOfDay = GetCurrentTimeOfDay();
        
        // Find scheduled tasks
        List<ScheduledTask> tasks = schedule.GetTasksAtTime(currentTimeOfDay);
        
        // Execute tasks
        foreach (var task in tasks)
        {
            ExecuteTask(task);
        }
    }
    
    private void ExecuteTask(ScheduledTask task)
    {
        switch (task.type)
        {
            case TaskType.Greeting:
                ExecuteGreeting(task);
                break;
            case TaskType.Reminder:
                ExecuteReminder(task);
                break;
            case TaskType.CheckIn:
                ExecuteCheckIn(task);
                break;
        }
    }
}

public class Schedule
{
    public List<ScheduledTask> tasks;
    
    public List<ScheduledTask> GetTasksAtTime(float time)
    {
        return tasks.Where(t => t.time == time).ToList();
    }
}

public class ScheduledTask
{
    public float time;
    public TaskType type;
    public string description;
    public Dictionary<string, object> parameters;
}

public enum TaskType
{
    Greeting,
    Reminder,
    CheckIn,
    Suggestion
}
```

---

## 2. Context Awareness

```csharp
// SchedulerContextSystem.cs
public class SchedulerContextSystem : MonoBehaviour
{
    [Header("Context")]
    [SerializeField] private SchedulerContext context;
    
    public void UpdateContext()
    {
        context = new SchedulerContext
        {
            timeOfDay = GetCurrentTimeOfDay(),
            dayOfWeek = GetCurrentDayOfWeek(),
            userActivity = DetectUserActivity(),
            userMood = DetectUserMood()
        };
    }
    
    public bool ShouldExecuteTask(ScheduledTask task)
    {
        // Check if task should be executed based on context
        if (task.requiresUserActive && context.userActivity == UserActivity.Idle)
        {
            return false;
        }
        
        if (task.requiresUserAvailable && context.userAvailability == UserAvailability.Busy)
        {
            return false;
        }
        
        return true;
    }
}

public class SchedulerContext
{
    public float timeOfDay;
    public DayOfWeek dayOfWeek;
    public UserActivity userActivity;
    public UserMood userMood;
    public UserAvailability userAvailability;
}
```

---

## 3. Adaptive Scheduling

```csharp
// AdaptiveSchedulerSystem.cs
public class AdaptiveSchedulerSystem : MonoBehaviour
{
    [Header("Adaptation")]
    [SerializeField] private bool enableAdaptation = true;
    
    public void AdaptSchedule()
    {
        // Adapt schedule based on user patterns
        UserPattern pattern = AnalyzeUserPattern();
        
        // Adjust task times based on pattern
        foreach (var task in schedule.tasks)
        {
            if (pattern.preferredTimes.ContainsKey(task.type))
            {
                task.time = pattern.preferredTimes[task.type];
            }
        }
    }
    
    private UserPattern AnalyzeUserPattern()
    {
        // Analyze user's daily patterns
        return new UserPattern();
    }
}
```

---

## Conclusion

AI Scheduler enables:
- **Time-based task execution** (greetings, reminders, check-ins)
- **Context awareness** (user activity, mood, availability)
- **Adaptive scheduling** based on user patterns
- **Proactive assistance** throughout the day

**Example**: 08:00 → "Chào buổi sáng anh!" → 09:00 → "Đừng quên họp lúc 10h" → 12:00 → "Anh đã ăn trưa chưa?"
