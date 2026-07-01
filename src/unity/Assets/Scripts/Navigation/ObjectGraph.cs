using UnityEngine;
using System.Collections.Generic;
using System;

namespace AICompanion.Navigation
{
    /// <summary>
    /// Object Graph - follows Single Responsibility Principle
    /// Manages detected objects and their relationships in the environment
    /// </summary>
    public class ObjectGraph : MonoBehaviour
    {
        [Header("Object Detection")]
        [SerializeField] private LayerMask objectLayers = -1;
        [SerializeField] private float detectionRadius = 10f;
        [SerializeField] private float updateInterval = 1f;

        [Header("Object Categories")]
        [SerializeField] private List<ObjectCategory> objectCategories = new List<ObjectCategory>();

        [Header("Debug Visualization")]
        [SerializeField] private bool showObjects = true;
        [SerializeField] private bool showRelationships = true;

        private List<DetectedObject> detectedObjects = new List<DetectedObject>();
        private Dictionary<string, List<DetectedObject>> objectsByCategory = new Dictionary<string, List<DetectedObject>>();
        private Dictionary<Transform, DetectedObject> objectLookup = new Dictionary<Transform, DetectedObject>();
        private float lastUpdateTime;

        public event Action<DetectedObject> OnObjectDetected;
        public event Action<DetectedObject> OnObjectLost;
        public event Action OnObjectGraphUpdated;

        [Serializable]
        public class ObjectCategory
        {
            public string categoryName;
            public List<string> objectNames = new List<string>();
            public Color categoryColor = Color.white;
        }

        [Serializable]
        public class DetectedObject
        {
            public Transform transform;
            public string objectName;
            public string category;
            public Vector3 position;
            public Quaternion rotation;
            public Bounds bounds;
            public float lastSeenTime;
            public List<ObjectRelationship> relationships = new List<ObjectRelationship>();

            public DetectedObject(Transform objTransform, string name, string cat)
            {
                transform = objTransform;
                objectName = name;
                category = cat;
                position = objTransform.position;
                rotation = objTransform.rotation;
                lastSeenTime = Time.time;

                // Calculate bounds
                Renderer renderer = objTransform.GetComponent<Renderer>();
                if (renderer != null)
                {
                    bounds = renderer.bounds;
                }
                else
                {
                    bounds = new Bounds(position, Vector3.one);
                }
            }
        }

        [Serializable]
        public class ObjectRelationship
        {
            public DetectedObject relatedObject;
            public string relationshipType;
            public float strength;

            public ObjectRelationship(DetectedObject obj, string type, float str)
            {
                relatedObject = obj;
                relationshipType = type;
                strength = str;
            }
        }

        private void Start()
        {
            InitializeObjectCategories();
            DetectObjects();
        }

        private void InitializeObjectCategories()
        {
            // Initialize category dictionaries
            foreach (var category in objectCategories)
            {
                objectsByCategory[category.categoryName] = new List<DetectedObject>();
            }
        }

        private void Update()
        {
            if (Time.time - lastUpdateTime >= updateInterval)
            {
                DetectObjects();
                UpdateObjectRelationships();
                lastUpdateTime = Time.time;
            }
        }

        private void DetectObjects()
        {
            // Find all objects within detection radius
            Collider[] colliders = Physics.OverlapSphere(transform.position, detectionRadius, objectLayers);

            // Mark all objects as not seen this frame
            foreach (var obj in detectedObjects)
            {
                obj.lastSeenTime = Time.time;
            }

            // Process detected colliders
            foreach (Collider collider in colliders)
            {
                Transform objTransform = collider.transform;

                // Skip if already detected
                if (objectLookup.ContainsKey(objTransform))
                {
                    UpdateDetectedObject(objectLookup[objTransform]);
                    continue;
                }

                // Categorize object
                string category = CategorizeObject(objTransform);
                if (string.IsNullOrEmpty(category)) continue;

                // Create new detected object
                DetectedObject detectedObj = new DetectedObject(objTransform, objTransform.name, category);
                detectedObjects.Add(detectedObj);
                objectLookup[objTransform] = detectedObj;

                // Add to category
                if (objectsByCategory.ContainsKey(category))
                {
                    objectsByCategory[category].Add(detectedObj);
                }

                OnObjectDetected?.Invoke(detectedObj);
            }

            // Remove lost objects
            RemoveLostObjects();

            OnObjectGraphUpdated?.Invoke();
        }

        private string CategorizeObject(Transform objTransform)
        {
            string objectName = objTransform.name.ToLower();

            foreach (var category in objectCategories)
            {
                foreach (string name in category.objectNames)
                {
                    if (objectName.Contains(name.ToLower()))
                    {
                        return category.categoryName;
                    }
                }
            }

            return "Uncategorized";
        }

        private void UpdateDetectedObject(DetectedObject detectedObj)
        {
            if (detectedObj.transform == null) return;

            detectedObj.position = detectedObj.transform.position;
            detectedObj.rotation = detectedObj.transform.rotation;
            detectedObj.lastSeenTime = Time.time;

            // Update bounds
            Renderer renderer = detectedObj.transform.GetComponent<Renderer>();
            if (renderer != null)
            {
                detectedObj.bounds = renderer.bounds;
            }
        }

        private void RemoveLostObjects()
        {
            List<DetectedObject> toRemove = new List<DetectedObject>();

            foreach (var detectedObj in detectedObjects)
            {
                // Remove if object is destroyed or not seen for too long
                if (detectedObj.transform == null || Time.time - detectedObj.lastSeenTime > 5f)
                {
                    toRemove.Add(detectedObj);
                    OnObjectLost?.Invoke(detectedObj);

                    // Remove from category
                    if (objectsByCategory.ContainsKey(detectedObj.category))
                    {
                        objectsByCategory[detectedObj.category].Remove(detectedObj);
                    }

                    // Remove from lookup
                    if (objectLookup.ContainsKey(detectedObj.transform))
                    {
                        objectLookup.Remove(detectedObj.transform);
                    }
                }
            }

            foreach (var obj in toRemove)
            {
                detectedObjects.Remove(obj);
            }
        }

        private void UpdateObjectRelationships()
        {
            // Clear existing relationships
            foreach (var obj in detectedObjects)
            {
                obj.relationships.Clear();
            }

            // Calculate new relationships
            for (int i = 0; i < detectedObjects.Count; i++)
            {
                for (int j = i + 1; j < detectedObjects.Count; j++)
                {
                    DetectedObject obj1 = detectedObjects[i];
                    DetectedObject obj2 = detectedObjects[j];

                    float distance = Vector3.Distance(obj1.position, obj2.position);
                    
                    // Create spatial relationship
                    if (distance < 3f)
                    {
                        string relationshipType = DetermineRelationshipType(obj1, obj2, distance);
                        float strength = 1f - (distance / 3f);

                        obj1.relationships.Add(new ObjectRelationship(obj2, relationshipType, strength));
                        obj2.relationships.Add(new ObjectRelationship(obj1, relationshipType, strength));
                    }
                }
            }
        }

        private string DetermineRelationshipType(DetectedObject obj1, DetectedObject obj2, float distance)
        {
            // Determine relationship based on spatial arrangement
            Vector3 direction = (obj2.position - obj1.position).normalized;

            if (distance < 1f)
            {
                return "touching";
            }
            else if (Vector3.Dot(direction, Vector3.up) > 0.8f)
            {
                return "above";
            }
            else if (Vector3.Dot(direction, Vector3.up) < -0.8f)
            {
                return "below";
            }
            else if (Mathf.Abs(Vector3.Dot(direction, Vector3.forward)) > 0.8f)
            {
                return "in_front";
            }
            else if (Mathf.Abs(Vector3.Dot(direction, Vector3.back)) > 0.8f)
            {
                return "behind";
            }
            else
            {
                return "near";
            }
        }

        public List<DetectedObject> GetObjectsByCategory(string category)
        {
            if (objectsByCategory.ContainsKey(category))
            {
                return objectsByCategory[category];
            }
            return new List<DetectedObject>();
        }

        public List<DetectedObject> GetObjectsNearPosition(Vector3 position, float radius)
        {
            List<DetectedObject> nearbyObjects = new List<DetectedObject>();

            foreach (var obj in detectedObjects)
            {
                if (Vector3.Distance(obj.position, position) < radius)
                {
                    nearbyObjects.Add(obj);
                }
            }

            return nearbyObjects;
        }

        public DetectedObject GetNearestObject(Vector3 position, string category = null)
        {
            DetectedObject nearestObj = null;
            float nearestDistance = float.MaxValue;

            foreach (var obj in detectedObjects)
            {
                if (!string.IsNullOrEmpty(category) && obj.category != category) continue;

                float distance = Vector3.Distance(obj.position, position);
                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearestObj = obj;
                }
            }

            return nearestObj;
        }

        public List<DetectedObject> GetRelatedObjects(DetectedObject obj, string relationshipType = null)
        {
            List<DetectedObject> relatedObjects = new List<DetectedObject>();

            foreach (var relationship in obj.relationships)
            {
                if (string.IsNullOrEmpty(relationshipType) || relationship.relationshipType == relationshipType)
                {
                    relatedObjects.Add(relationship.relatedObject);
                }
            }

            return relatedObjects;
        }

        public void AddObjectCategory(string categoryName, List<string> objectNames, Color color)
        {
            var category = new ObjectCategory
            {
                categoryName = categoryName,
                objectNames = objectNames,
                categoryColor = color
            };
            objectCategories.Add(category);
            objectsByCategory[categoryName] = new List<DetectedObject>();
        }

        public void SetDetectionRadius(float radius)
        {
            detectionRadius = radius;
        }

        public void SetUpdateInterval(float interval)
        {
            updateInterval = interval;
        }

        private void OnDrawGizmos()
        {
            if (!showObjects && !showRelationships) return;

            // Draw detection radius
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(transform.position, detectionRadius);

            // Draw objects
            if (showObjects)
            {
                foreach (var category in objectCategories)
                {
                    Gizmos.color = category.categoryColor;
                    if (objectsByCategory.ContainsKey(category.categoryName))
                    {
                        foreach (var obj in objectsByCategory[category.categoryName])
                        {
                            Gizmos.DrawWireCube(obj.bounds.center, obj.bounds.size);
                        }
                    }
                }
            }

            // Draw relationships
            if (showRelationships)
            {
                Gizmos.color = Color.cyan;
                foreach (var obj in detectedObjects)
                {
                    foreach (var relationship in obj.relationships)
                    {
                        if (relationship.strength > 0.5f)
                        {
                            Gizmos.DrawLine(obj.position, relationship.relatedObject.position);
                        }
                    }
                }
            }
        }
    }
}
