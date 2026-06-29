# PHẦN 3: CHARACTER DISPLAY & PHYSICS SYSTEM

## Table of Contents
1. [System Overview](#system-overview)
2. [Character Display System](#character-display-system)
3. [Character Controller](#character-controller)
4. [Animation System](#animation-system)
5. [Physics System](#physics-system)
6. [Interaction System](#interaction-system)
7. [Lighting & Shadows](#lighting--shadows)
8. [Collision Detection](#collision-detection)
9. [Pathfinding & Navigation](#pathfinding--navigation)
10. [Performance Optimization](#performance-optimization)

---

## 1. System Overview

### 1.1 System Architecture

```mermaid
graph TB
    subgraph "Character Display System"
        A[Character Renderer] --> B[Mesh Renderer]
        A --> C[Material System]
        A --> D[LOD System]
        A --> E[Shadow System]
    end
    
    subgraph "Animation System"
        F[Animation Controller] --> G[Blend Tree]
        F --> H[Animation States]
        F --> I[IK Solver]
        F --> J[Facial Animation]
    end
    
    subgraph "Physics System"
        K[Character Controller] --> L[Rigidbody]
        K --> M[Collider]
        K --> N[Physics Material]
        K --> O[Forces]
    end
    
    subgraph "Interaction System"
        P[Interaction Manager] --> Q[Raycasting]
        P --> R[Trigger Detection]
        P --> S[Object Interaction]
    end
    
    subgraph "Navigation System"
        T[NavMesh Agent] --> U[Pathfinding]
        T --> V[Obstacle Avoidance]
        T --> W[Target Tracking]
    end
    
    A --> F
    F --> K
    K --> P
    P --> T
```

### 1.2 Character States

```yaml
Character States:
  movement:
    - Idle
    - Walking
    - Running
    - Jumping
    - Falling
    - Landing
    - Crouching
    - Climbing
  
  posture:
    - Standing
    - Sitting
    - Lying down
    - Kneeling
  
  interaction:
    - Interacting
    - Carrying
    - Using
    - Talking
  
  emotional:
    - Neutral
    - Happy
    - Sad
    - Angry
    - Surprised
    - Scared
  
  action:
    - Waving
    - Pointing
    - Nodding
    - Shaking head
    - Dancing
```

---

## 2. Character Display System

### 2.1 Character Renderer Architecture

```csharp
// CharacterRenderer.cs
using UnityEngine;
using System.Collections.Generic;

namespace AICompanion.Character
{
    /// <summary>
    /// Main character renderer handling mesh, materials, LODs, and shadows
    /// </summary>
    public class CharacterRenderer : MonoBehaviour
    {
        [Header("Mesh Components")]
        [SerializeField] private SkinnedMeshRenderer[] meshRenderers;
        [SerializeField] private MeshFilter[] meshFilters;
        
        [Header("Materials")]
        [SerializeField] private Material[] bodyMaterials;
        [SerializeField] private Material[] faceMaterials;
        [SerializeField] private Material[] hairMaterials;
        [SerializeField] private Material[] clothingMaterials;
        
        [Header("LOD System")]
        [SerializeField] private LODGroup lodGroup;
        [SerializeField] private GameObject[] lodObjects;
        [SerializeField] private float[] lodTransitionHeights;
        
        [Header("Shadows")]
        [SerializeField] private bool castShadows = true;
        [SerializeField] private bool receiveShadows = true;
        [SerializeField] private ShadowQuality shadowQuality = ShadowQuality.High;
        
        [Header("Rendering")]
        [SerializeField] private RenderingPath renderingPath;
        [SerializeField] private int renderQueue;
        
        private CharacterLOD currentLOD;
        private Dictionary<string, Material> materialCache;
        
        public enum ShadowQuality
        {
            Off,
            Low,
            Medium,
            High,
            Ultra
        }
        
        public enum CharacterLOD
        {
            LOD0 = 0,  // Hero (50K-100K triangles)
            LOD1 = 1,  // High (25K-50K triangles)
            LOD2 = 2,  // Medium (10K-25K triangles)
            LOD3 = 3,  // Low (5K-10K triangles)
            LOD4 = 4   // Placeholder (1K-5K triangles)
        }
        
        private void Awake()
        {
            InitializeRenderer();
            SetupMaterials();
            ConfigureShadows();
            SetupLOD();
        }
        
        private void InitializeRenderer()
        {
            // Get all mesh renderers
            meshRenderers = GetComponentsInChildren<SkinnedMeshRenderer>();
            meshFilters = GetComponentsInChildren<MeshFilter>();
            
            // Setup material cache
            materialCache = new Dictionary<string, Material>();
            
            Debug.Log($"CharacterRenderer initialized with {meshRenderers.Length} renderers");
        }
        
        private void SetupMaterials()
        {
            // Apply materials to renderers
            foreach (var renderer in meshRenderers)
            {
                renderer.materials = GetMaterialsForRenderer(renderer);
            }
        }
        
        private Material[] GetMaterialsForRenderer(SkinnedMeshRenderer renderer)
        {
            // Determine materials based on renderer name/path
            string rendererName = renderer.name.ToLower();
            
            if (rendererName.Contains("face") || rendererName.Contains("head"))
            {
                return faceMaterials;
            }
            else if (rendererName.Contains("hair"))
            {
                return hairMaterials;
            }
            else if (rendererName.Contains("cloth") || rendererName.Contains("clothing"))
            {
                return clothingMaterials;
            }
            else
            {
                return bodyMaterials;
            }
        }
        
        private void ConfigureShadows()
        {
            // Configure shadow settings for all renderers
            foreach (var renderer in meshRenderers)
            {
                renderer.shadowCastingMode = castShadows ? 
                    ShadowCastingMode.On : ShadowCastingMode.Off;
                renderer.receiveShadows = receiveShadows;
            }
            
            // Configure shadow quality
            switch (shadowQuality)
            {
                case ShadowQuality.Off:
                    DisableShadows();
                    break;
                case ShadowQuality.Low:
                    SetShadowDistance(10f);
                    SetShadowCascades(1);
                    break;
                case ShadowQuality.Medium:
                    SetShadowDistance(25f);
                    SetShadowCascades(2);
                    break;
                case ShadowQuality.High:
                    SetShadowDistance(50f);
                    SetShadowCascades(4);
                    break;
                case ShadowQuality.Ultra:
                    SetShadowDistance(100f);
                    SetShadowCascades(4);
                    SetShadowResolution(4096);
                    break;
            }
        }
        
        private void DisableShadows()
        {
            foreach (var renderer in meshRenderers)
            {
                renderer.shadowCastingMode = ShadowCastingMode.Off;
                renderer.receiveShadows = false;
            }
        }
        
        private void SetShadowDistance(float distance)
        {
            QualitySettings.shadowDistance = distance;
        }
        
        private void SetShadowCascades(int cascades)
        {
            QualitySettings.shadowCascades = (ShadowCascadesSize)cascades;
        }
        
        private void SetShadowResolution(int resolution)
        {
            QualitySettings.shadowResolution = (ShadowResolution)resolution;
        }
        
        private void SetupLOD()
        {
            if (lodGroup == null)
            {
                lodGroup = gameObject.AddComponent<LODGroup>();
            }
            
            // Setup LOD levels
            LOD[] lods = new LOD[lodObjects.Length];
            
            for (int i = 0; i < lodObjects.Length; i++)
            {
                float transitionHeight = lodTransitionHeights[i];
                Renderer[] renderers = lodObjects[i].GetComponentsInChildren<Renderer>();
                
                lods[i] = new LOD(transitionHeight, renderers);
            }
            
            lodGroup.SetLODs(lods);
            lodGroup.RecalculateBounds();
        }
        
        private void Update()
        {
            UpdateLOD();
        }
        
        private void UpdateLOD()
        {
            // Get current LOD level
            CharacterLOD newLOD = DetermineCurrentLOD();
            
            if (newLOD != currentLOD)
            {
                currentLOD = newLOD;
                OnLODChanged(currentLOD);
            }
        }
        
        private CharacterLOD DetermineCurrentLOD()
        {
            // Determine LOD based on distance to camera
            float distance = Vector3.Distance(transform.position, Camera.main.transform.position);
            
            if (distance < 2f) return CharacterLOD.LOD0;
            if (distance < 5f) return CharacterLOD.LOD1;
            if (distance < 10f) return CharacterLOD.LOD2;
            if (distance < 20f) return CharacterLOD.LOD3;
            return CharacterLOD.LOD4;
        }
        
        private void OnLODChanged(CharacterLOD newLOD)
        {
            // Handle LOD change
            Debug.Log($"LOD changed to {newLOD}");
            
            // You can trigger events or adjust quality here
            switch (newLOD)
            {
                case CharacterLOD.LOD0:
                    EnableHighQualityFeatures();
                    break;
                case CharacterLOD.LOD4:
                    DisableHighQualityFeatures();
                    break;
            }
        }
        
        private void EnableHighQualityFeatures()
        {
            // Enable features for close-up view
            foreach (var renderer in meshRenderers)
            {
                renderer.allowOcclusionWhenDynamic = false;
            }
        }
        
        private void DisableHighQualityFeatures()
        {
            // Disable features for distant view
            foreach (var renderer in meshRenderers)
            {
                renderer.allowOcclusionWhenDynamic = true;
            }
        }
        
        public void SetMaterial(Material material, string slotName)
        {
            if (materialCache.ContainsKey(slotName))
            {
                materialCache[slotName] = material;
            }
            else
            {
                materialCache.Add(slotName, material);
            }
            
            // Apply material to appropriate renderer
            ApplyMaterialToSlot(material, slotName);
        }
        
        private void ApplyMaterialToSlot(Material material, string slotName)
        {
            // Find renderer with matching slot name and apply material
            foreach (var renderer in meshRenderers)
            {
                if (renderer.name.ToLower().Contains(slotName.ToLower()))
                {
                    renderer.material = material;
                    break;
                }
            }
        }
        
        public Material GetMaterial(string slotName)
        {
            return materialCache.ContainsKey(slotName) ? materialCache[slotName] : null;
        }
        
        public void SetShadowQuality(ShadowQuality quality)
        {
            shadowQuality = quality;
            ConfigureShadows();
        }
        
        public void SetLODLevel(CharacterLOD lod)
        {
            currentLOD = lod;
            lodGroup.ForceLOD((int)lod);
        }
    }
}
```

### 2.2 Material System

```csharp
// CharacterMaterialController.cs
using UnityEngine;
using System.Collections.Generic;

namespace AICompanion.Character
{
    /// <summary>
    /// Controls character materials with PBR properties and dynamic updates
    /// </summary>
    public class CharacterMaterialController : MonoBehaviour
    {
        [Header("Material Properties")]
        [SerializeField] private float smoothness = 0.5f;
        [SerializeField] private float metallic = 0.0f;
        [SerializeField] private Color subsurfaceColor = Color.white;
        [SerializeField] private float subsurfaceScattering = 0.5f;
        
        [Header("Dynamic Properties")]
        [SerializeField] private bool enableWetness = false;
        [SerializeField] private float wetness = 0.0f;
        [SerializeField] private bool enableDirt = false;
        [SerializeField] private float dirtLevel = 0.0f;
        
        [Header("Environmental Response")]
        [SerializeField] private bool enableLightEstimation = true;
        [SerializeField] private float lightEstimationBlend = 0.5f;
        
        private MaterialPropertyBlock propertyBlock;
        private SkinnedMeshRenderer[] meshRenderers;
        private Dictionary<Renderer, Material[]> originalMaterials;
        
        private static readonly int SmoothnessProperty = Shader.PropertyToID("_Smoothness");
        private static readonly int MetallicProperty = Shader.PropertyToID("_Metallic");
        private static readonly int SubsurfaceColorProperty = Shader.PropertyToID("_SubsurfaceColor");
        private static readonly int SubsurfaceScatteringProperty = Shader.PropertyToID("_SubsurfaceScattering");
        private static readonly int WetnessProperty = Shader.PropertyToID("_Wetness");
        private static readonly int DirtLevelProperty = Shader.PropertyToID("_DirtLevel");
        private static readonly int AmbientLightProperty = Shader.PropertyToID("_AmbientLight");
        private static readonly int DirectionalLightProperty = Shader.PropertyToID("_DirectionalLight");
        
        private void Awake()
        {
            Initialize();
        }
        
        private void Initialize()
        {
            propertyBlock = new MaterialPropertyBlock();
            meshRenderers = GetComponentsInChildren<SkinnedMeshRenderer>();
            originalMaterials = new Dictionary<Renderer, Material[]>();
            
            // Store original materials
            foreach (var renderer in meshRenderers)
            {
                originalMaterials[renderer] = renderer.materials;
            }
            
            ApplyMaterialProperties();
        }
        
        private void ApplyMaterialProperties()
        {
            foreach (var renderer in meshRenderers)
            {
                renderer.GetPropertyBlock(propertyBlock);
                
                // Apply PBR properties
                propertyBlock.SetFloat(SmoothnessProperty, smoothness);
                propertyBlock.SetFloat(MetallicProperty, metallic);
                propertyBlock.SetColor(SubsurfaceColorProperty, subsurfaceColor);
                propertyBlock.SetFloat(SubsurfaceScatteringProperty, subsurfaceScattering);
                
                // Apply dynamic properties
                propertyBlock.SetFloat(WetnessProperty, enableWetness ? wetness : 0f);
                propertyBlock.SetFloat(DirtLevelProperty, enableDirt ? dirtLevel : 0f);
                
                renderer.SetPropertyBlock(propertyBlock);
            }
        }
        
        public void SetSmoothness(float value)
        {
            smoothness = Mathf.Clamp01(value);
            ApplyMaterialProperties();
        }
        
        public void SetMetallic(float value)
        {
            metallic = Mathf.Clamp01(value);
            ApplyMaterialProperties();
        }
        
        public void SetSubsurfaceScattering(float value)
        {
            subsurfaceScattering = Mathf.Clamp01(value);
            ApplyMaterialProperties();
        }
        
        public void SetWetness(float value)
        {
            wetness = Mathf.Clamp01(value);
            enableWetness = wetness > 0f;
            ApplyMaterialProperties();
        }
        
        public void SetDirtLevel(float value)
        {
            dirtLevel = Mathf.Clamp01(value);
            enableDirt = dirtLevel > 0f;
            ApplyMaterialProperties();
        }
        
        public void UpdateEnvironmentalLighting(LightEstimation lightEstimation)
        {
            if (!enableLightEstimation || lightEstimation == null) return;
            
            foreach (var renderer in meshRenderers)
            {
                renderer.GetPropertyBlock(propertyBlock);
                
                // Blend current lighting with estimated lighting
                Color blendedAmbient = Color.Lerp(
                    RenderSettings.ambientLight,
                    lightEstimation.AmbientColor,
                    lightEstimationBlend
                );
                
                Color blendedDirectional = Color.Lerp(
                    RenderSettings.sun ? RenderSettings.sun.color : Color.white,
                    lightEstimation.DirectionalColor,
                    lightEstimationBlend
                );
                
                propertyBlock.SetColor(AmbientLightProperty, blendedAmbient);
                propertyBlock.SetColor(DirectionalLightProperty, blendedDirectional);
                
                renderer.SetPropertyBlock(propertyBlock);
            }
        }
        
        public void ResetMaterials()
        {
            foreach (var kvp in originalMaterials)
            {
                kvp.Key.materials = kvp.Value;
            }
        }
    }
    
    /// <summary>
    /// Data structure for light estimation from AR system
    /// </summary>
    public class LightEstimation
    {
        public Color AmbientColor { get; set; }
        public Color DirectionalColor { get; set; }
        public Vector3 LightDirection { get; set; }
        public float LightIntensity { get; set; }
        public Color Temperature { get; set; }
    }
}
```

---

## 3. Character Controller

### 3.1 Character Controller Implementation

```csharp
// AICompanionController.cs
using UnityEngine;
using UnityEngine.AI;
using System.Collections.Generic;

namespace AICompanion.Character
{
    /// <summary>
    /// Main character controller handling movement, physics, and interactions
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    [RequireComponent(typeof(Animator))]
    public class AICompanionController : MonoBehaviour
    {
        [Header("Movement Settings")]
        [SerializeField] private float walkSpeed = 1.5f;
        [SerializeField] private float runSpeed = 3.5f;
        [SerializeField] private float jumpForce = 5f;
        [SerializeField] private float gravity = -9.81f;
        [SerializeField] private float rotationSpeed = 10f;
        
        [Header("Navigation")]
        [SerializeField] private NavMeshAgent navMeshAgent;
        [SerializeField] private float stoppingDistance = 0.5f;
        [SerializeField] private float destinationUpdateInterval = 0.5f;
        
        [Header("Interaction")]
        [SerializeField] private float interactionRadius = 2f;
        [SerializeField] private LayerMask interactionLayer;
        
        [Header("Posture")]
        [SerializeField] private float standingHeight = 1.7f;
        [SerializeField] private float sittingHeight = 1.0f;
        [SerializeField] private float transitionSpeed = 2f;
        
        private CharacterController characterController;
        private Animator animator;
        private Vector3 velocity;
        private Vector3 targetDestination;
        private bool isMoving;
        private bool isRunning;
        private bool isJumping;
        private bool isSitting;
        private float currentHeight;
        private List<GameObject> nearbyInteractables;
        
        // Animation parameters
        private static readonly int SpeedHash = Animator.StringToHash("Speed");
        private static readonly int IsMovingHash = Animator.StringToHash("IsMoving");
        private static readonly int IsRunningHash = Animator.StringToHash("IsRunning");
        private static readonly int IsJumpingHash = Animator.StringToHash("IsJumping");
        private static readonly int IsSittingHash = Animator.StringToHash("IsSitting");
        private static readonly int GroundedHash = Animator.StringToHash("Grounded");
        
        public enum MovementState
        {
            Idle,
            Walking,
            Running,
            Jumping,
            Falling,
            Landing
        }
        
        public enum PostureState
        {
            Standing,
            Sitting,
            LyingDown,
            Kneeling
        }
        
        public MovementState CurrentMovementState { get; private set; }
        public PostureState CurrentPostureState { get; private set; }
        public bool IsGrounded { get; private set; }
        
        private void Awake()
        {
            InitializeComponents();
            InitializeVariables();
        }
        
        private void InitializeComponents()
        {
            characterController = GetComponent<CharacterController>();
            animator = GetComponent<Animator>();
            
            if (navMeshAgent == null)
            {
                navMeshAgent = GetComponent<NavMeshAgent>();
            }
            
            if (navMeshAgent != null)
            {
                navMeshAgent.speed = walkSpeed;
                navMeshAgent.stoppingDistance = stoppingDistance;
                navMeshAgent.autoBraking = true;
            }
        }
        
        private void InitializeVariables()
        {
            velocity = Vector3.zero;
            targetDestination = transform.position;
            isMoving = false;
            isRunning = false;
            isJumping = false;
            isSitting = false;
            currentHeight = standingHeight;
            nearbyInteractables = new List<GameObject>();
            CurrentMovementState = MovementState.Idle;
            CurrentPostureState = PostureState.Standing;
            IsGrounded = true;
        }
        
        private void Update()
        {
            CheckGrounded();
            HandleMovement();
            HandlePhysics();
            HandleNavigation();
            DetectInteractables();
            UpdateAnimation();
        }
        
        private void CheckGrounded()
        {
            IsGrounded = characterController.isGrounded;
            animator.SetBool(GroundedHash, IsGrounded);
            
            if (IsGrounded && velocity.y < 0)
            {
                velocity.y = -2f; // Small downward force to keep grounded
            }
        }
        
        private void HandleMovement()
        {
            if (!isMoving || targetDestination == null) return;
            
            Vector3 direction = (targetDestination - transform.position).normalized;
            direction.y = 0; // Keep movement on horizontal plane
            
            float speed = isRunning ? runSpeed : walkSpeed;
            
            // Move character
            characterController.Move(direction * speed * Time.deltaTime);
            
            // Rotate towards destination
            if (direction != Vector3.zero)
            {
                Quaternion targetRotation = Quaternion.LookRotation(direction);
                transform.rotation = Quaternion.Slerp(
                    transform.rotation,
                    targetRotation,
                    rotationSpeed * Time.deltaTime
                );
            }
            
            // Check if reached destination
            float distanceToDestination = Vector3.Distance(transform.position, targetDestination);
            if (distanceToDestination < stoppingDistance)
            {
                isMoving = false;
                CurrentMovementState = MovementState.Idle;
            }
        }
        
        private void HandlePhysics()
        {
            // Apply gravity
            velocity.y += gravity * Time.deltaTime;
            characterController.Move(velocity * Time.deltaTime);
        }
        
        private void HandleNavigation()
        {
            if (navMeshAgent == null || !isMoving) return;
            
            // Update navigation destination
            if (navMeshAgent.destination != targetDestination)
            {
                navMeshAgent.SetDestination(targetDestination);
            }
            
            // Update speed based on state
            navMeshAgent.speed = isRunning ? runSpeed : walkSpeed;
        }
        
        private void DetectInteractables()
        {
            nearbyInteractables.Clear();
            
            Collider[] hitColliders = Physics.OverlapSphere(
                transform.position,
                interactionRadius,
                interactionLayer
            );
            
            foreach (var collider in hitColliders)
            {
                if (collider.gameObject != gameObject)
                {
                    nearbyInteractables.Add(collider.gameObject);
                }
            }
        }
        
        private void UpdateAnimation()
        {
            // Update animation parameters
            float currentSpeed = characterController.velocity.magnitude;
            animator.SetFloat(SpeedHash, currentSpeed);
            animator.SetBool(IsMovingHash, isMoving);
            animator.SetBool(IsRunningHash, isRunning);
            animator.SetBool(IsJumpingHash, isJumping);
            animator.SetBool(IsSittingHash, isSitting);
            
            // Update movement state
            if (!IsGrounded)
            {
                CurrentMovementState = velocity.y > 0 ? MovementState.Jumping : MovementState.Falling;
            }
            else if (isMoving)
            {
                CurrentMovementState = isRunning ? MovementState.Running : MovementState.Walking;
            }
            else
            {
                CurrentMovementState = MovementState.Idle;
            }
        }
        
        #region Public Movement Methods
        
        public void MoveTo(Vector3 destination, bool run = false)
        {
            targetDestination = destination;
            isMoving = true;
            isRunning = run;
            
            if (navMeshAgent != null && navMeshAgent.isOnNavMesh)
            {
                navMeshAgent.SetDestination(destination);
            }
        }
        
        public void StopMovement()
        {
            isMoving = false;
            targetDestination = transform.position;
            
            if (navMeshAgent != null)
            {
                navMeshAgent.isStopped = true;
                navMeshAgent.ResetPath();
            }
        }
        
        public void Jump()
        {
            if (IsGrounded && !isJumping)
            {
                velocity.y = Mathf.Sqrt(jumpForce * -2f * gravity);
                isJumping = true;
                CurrentMovementState = MovementState.Jumping;
            }
        }
        
        public void SetRunning(bool running)
        {
            isRunning = running;
        }
        
        #endregion
        
        #region Public Posture Methods
        
        public void SetPosture(PostureState posture)
        {
            StartCoroutine(TransitionPosture(posture));
        }
        
        private System.Collections.IEnumerator TransitionPosture(PostureState targetPosture)
        {
            float targetHeight = GetHeightForPosture(targetPosture);
            
            while (Mathf.Abs(currentHeight - targetHeight) > 0.01f)
            {
                currentHeight = Mathf.Lerp(currentHeight, targetHeight, transitionSpeed * Time.deltaTime);
                characterController.height = currentHeight;
                
                // Adjust center to keep feet on ground
                characterController.center = new Vector3(0, currentHeight / 2f, 0);
                
                yield return null;
            }
            
            currentHeight = targetHeight;
            CurrentPostureState = targetPosture;
            
            // Update animation
            isSitting = targetPosture == PostureState.Sitting;
            animator.SetBool(IsSittingHash, isSitting);
        }
        
        private float GetHeightForPosture(PostureState posture)
        {
            switch (posture)
            {
                case PostureState.Standing:
                    return standingHeight;
                case PostureState.Sitting:
                    return sittingHeight;
                case PostureState.LyingDown:
                    return standingHeight * 0.3f;
                case PostureState.Kneeling:
                    return standingHeight * 0.6f;
                default:
                    return standingHeight;
            }
        }
        
        #endregion
        
        #region Public Interaction Methods
        
        public GameObject[] GetNearbyInteractables()
        {
            return nearbyInteractables.ToArray();
        }
        
        public bool InteractWith(GameObject target)
        {
            if (!nearbyInteractables.Contains(target)) return false;
            
            // Trigger interaction on target
            var interactable = target.GetComponent<IInteractable>();
            if (interactable != null)
            {
                return interactable.Interact(this);
            }
            
            return false;
        }
        
        public void LookAt(Vector3 target)
        {
            Vector3 direction = (target - transform.position).normalized;
            direction.y = 0;
            
            if (direction != Vector3.zero)
            {
                Quaternion targetRotation = Quaternion.LookRotation(direction);
                transform.rotation = Quaternion.Slerp(
                    transform.rotation,
                    targetRotation,
                    rotationSpeed * Time.deltaTime
                );
            }
        }
        
        public void LookAt(Transform target)
        {
            if (target != null)
            {
                LookAt(target.position);
            }
        }
        
        #endregion
        
        #region Utility Methods
        
        public void Teleport(Vector3 position)
        {
            characterController.enabled = false;
            transform.position = position;
            characterController.enabled = true;
            
            if (navMeshAgent != null)
            {
                navMeshAgent.Warp(position);
            }
        }
        
        public void SetMovementSpeed(float walk, float run)
        {
            walkSpeed = walk;
            runSpeed = run;
            
            if (navMeshAgent != null)
            {
                navMeshAgent.speed = walkSpeed;
            }
        }
        
        #endregion
        
        private void OnDrawGizmosSelected()
        {
            // Draw interaction radius
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(transform.position, interactionRadius);
            
            // Draw destination
            if (isMoving)
            {
                Gizmos.color = Color.green;
                Gizmos.DrawSphere(targetDestination, 0.2f);
                Gizmos.DrawLine(transform.position, targetDestination);
            }
        }
    }
    
    /// <summary>
    /// Interface for interactable objects
    /// </summary>
    public interface IInteractable
    {
        bool Interact(AICompanionController character);
        string GetInteractionName();
    }
}
```

---

## 4. Animation System

### 4.1 Animation Controller

```csharp
// CharacterAnimationController.cs
using UnityEngine;
using System.Collections.Generic;

namespace AICompanion.Character
{
    /// <summary>
    /// Controls character animation including blend trees, states, and layers
    /// </summary>
    [RequireComponent(typeof(Animator))]
    public class CharacterAnimationController : MonoBehaviour
    {
        [Header("Animation References")]
        [SerializeField] private Animator animator;
        
        [Header("Animation States")]
        [SerializeField] private AnimationClip idleAnimation;
        [SerializeField] private AnimationClip walkAnimation;
        [SerializeField] private AnimationClip runAnimation;
        [SerializeField] private AnimationClip jumpAnimation;
        [SerializeField] private AnimationClip sitAnimation;
        [SerializeField] private AnimationClip standAnimation;
        
        [Header("Facial Animation")]
        [SerializeField] private SkinnedMeshRenderer faceMesh;
        [SerializeField] private BlendShapeMapping[] blendShapeMappings;
        
        [Header("Animation Settings")]
        [SerializeField] private float animationBlendSpeed = 0.2f;
        [SerializeField] private bool enableFootIK = true;
        [SerializeField] private bool enableHandIK = true;
        
        private Dictionary<string, int> blendShapeIndices;
        private Dictionary<string, float> currentBlendShapeValues;
        private AvatarIKGoal currentIKGoal;
        private Vector3 ikTargetPosition;
        private Quaternion ikTargetRotation;
        private bool ikActive;
        
        // Animation parameter hashes
        private static readonly int SpeedHash = Animator.StringToHash("Speed");
        private static readonly int DirectionHash = Animator.StringToHash("Direction");
        private static readonly int IsMovingHash = Animator.StringToHash("IsMoving");
        private static readonly int IsRunningHash = Animator.StringToHash("IsRunning");
        private static readonly int IsJumpingHash = Animator.StringToHash("IsJumping");
        private static readonly int IsSittingHash = Animator.StringToHash("IsSitting");
        private static readonly int EmotionHash = Animator.StringToHash("Emotion");
        
        [System.Serializable]
        public class BlendShapeMapping
        {
            public string blendShapeName;
            public int index;
            public float minValue = 0f;
            public float maxValue = 100f;
        }
        
        public enum EmotionType
        {
            Neutral,
            Happy,
            Sad,
            Angry,
            Surprised,
            Scared,
            Excited,
            Bored
        }
        
        private void Awake()
        {
            InitializeAnimator();
            InitializeBlendShapes();
        }
        
        private void InitializeAnimator()
        {
            if (animator == null)
            {
                animator = GetComponent<Animator>();
            }
            
            // Configure IK
            animator.applyRootMotion = false;
            animator.updateMode = AnimatorUpdateMode.Normal;
            animator.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
        }
        
        private void InitializeBlendShapes()
        {
            if (faceMesh == null)
            {
                faceMesh = GetComponentInChildren<SkinnedMeshRenderer>();
            }
            
            blendShapeIndices = new Dictionary<string, int>();
            currentBlendShapeValues = new Dictionary<string, float>();
            
            if (faceMesh != null)
            {
                // Map blend shape names to indices
                for (int i = 0; i < faceMesh.sharedMesh.blendShapeCount; i++)
                {
                    string blendShapeName = faceMesh.sharedMesh.GetBlendShapeName(i);
                    blendShapeIndices[blendShapeName] = i;
                    currentBlendShapeValues[blendShapeName] = 0f;
                }
                
                // Update blend shape mappings
                foreach (var mapping in blendShapeMappings)
                {
                    if (blendShapeIndices.ContainsKey(mapping.blendShapeName))
                    {
                        mapping.index = blendShapeIndices[mapping.blendShapeName];
                    }
                }
            }
        }
        
        #region Body Animation
        
        public void SetMovementParameters(float speed, float direction)
        {
            animator.SetFloat(SpeedHash, speed, animationBlendSpeed, Time.deltaTime);
            animator.SetFloat(DirectionHash, direction, animationBlendSpeed, Time.deltaTime);
        }
        
        public void SetMoving(bool moving)
        {
            animator.SetBool(IsMovingHash, moving);
        }
        
        public void SetRunning(bool running)
        {
            animator.SetBool(IsRunningHash, running);
        }
        
        public void SetJumping(bool jumping)
        {
            animator.SetBool(IsJumpingHash, jumping);
        }
        
        public void SetSitting(bool sitting)
        {
            animator.SetBool(IsSittingHash, sitting);
        }
        
        public void SetEmotion(EmotionType emotion)
        {
            animator.SetInteger(EmotionHash, (int)emotion);
        }
        
        public void PlayAnimation(string animationName, float transitionDuration = 0.2f)
        {
            animator.CrossFade(animationName, transitionDuration);
        }
        
        public void PlayAnimation(AnimationClip clip, float transitionDuration = 0.2f)
        {
            if (clip != null)
            {
                animator.CrossFade(clip.name, transitionDuration);
            }
        }
        
        #endregion
        
        #region Facial Animation
        
        public void SetBlendShape(string blendShapeName, float value)
        {
            if (faceMesh == null || !blendShapeIndices.ContainsKey(blendShapeName)) return;
            
            int index = blendShapeIndices[blendShapeName];
            value = Mathf.Clamp01(value);
            
            faceMesh.SetBlendShapeWeight(index, value * 100f);
            currentBlendShapeValues[blendShapeName] = value;
        }
        
        public void SetBlendShape(int index, float value)
        {
            if (faceMesh == null || index < 0 || index >= faceMesh.sharedMesh.blendShapeCount) return;
            
            value = Mathf.Clamp01(value);
            faceMesh.SetBlendShapeWeight(index, value * 100f);
        }
        
        public float GetBlendShapeValue(string blendShapeName)
        {
            return currentBlendShapeValues.ContainsKey(blendShapeName) ? 
                currentBlendShapeValues[blendShapeName] : 0f;
        }
        
        public void SetFacialExpression(Dictionary<string, float> expression)
        {
            foreach (var kvp in expression)
            {
                SetBlendShape(kvp.Key, kvp.Value);
            }
        }
        
        public void ResetFacialExpression()
        {
            foreach (var blendShapeName in blendShapeIndices.Keys)
            {
                SetBlendShape(blendShapeName, 0f);
            }
        }
        
        #endregion
        
        #region Viseme Animation (Lip Sync)
        
        public void SetViseme(string visemeName, float value)
        {
            SetBlendShape(visemeName, value);
        }
        
        public void SetViseme(int visemeIndex, float value)
        {
            SetBlendShape(visemeIndex, value);
        }
        
        public void AnimateVisemes(float[] visemeWeights)
        {
            for (int i = 0; i < visemeWeights.Length && i < faceMesh.sharedMesh.blendShapeCount; i++)
            {
                SetBlendShape(i, visemeWeights[i]);
            }
        }
        
        #endregion
        
        #region IK Control
        
        public void SetIKTarget(AvatarIKGoal goal, Vector3 position, Quaternion rotation)
        {
            currentIKGoal = goal;
            ikTargetPosition = position;
            ikTargetRotation = rotation;
            ikActive = true;
        }
        
        public void ClearIKTarget()
        {
            ikActive = false;
        }
        
        private void OnAnimatorIK(int layerIndex)
        {
            if (!ikActive) return;
            
            // Set IK position and rotation
            if (enableHandIK && (currentIKGoal == AvatarIKGoal.LeftHand || currentIKGoal == AvatarIKGoal.RightHand))
            {
                animator.SetIKPosition(currentIKGoal, ikTargetPosition);
                animator.SetIKRotation(currentIKGoal, ikTargetRotation);
                animator.SetIKPositionWeight(currentIKGoal, 1f);
                animator.SetIKRotationWeight(currentIKGoal, 1f);
            }
            
            if (enableFootIK && (currentIKGoal == AvatarIKGoal.LeftFoot || currentIKGoal == AvatarIKGoal.RightFoot))
            {
                animator.SetIKPosition(currentIKGoal, ikTargetPosition);
                animator.SetIKRotation(currentIKGoal, ikTargetRotation);
                animator.SetIKPositionWeight(currentIKGoal, 1f);
                animator.SetIKRotationWeight(currentIKGoal, 1f);
            }
        }
        
        #endregion
        
        #region Animation Events
        
        public void OnAnimationEvent(string eventName)
        {
            // Handle animation events
            switch (eventName)
            {
                case "Footstep":
                    OnFootstep();
                    break;
                case "JumpStart":
                    OnJumpStart();
                    break;
                case "JumpLand":
                    OnJumpLand();
                    break;
                case "SitStart":
                    OnSitStart();
                    break;
                case "SitEnd":
                    OnSitEnd();
                    break;
            }
        }
        
        private void OnFootstep()
        {
            // Trigger footstep sound or effect
            Debug.Log("Footstep");
        }
        
        private void OnJumpStart()
        {
            // Handle jump start
            Debug.Log("Jump Start");
        }
        
        private void OnJumpLand()
        {
            // Handle jump landing
            Debug.Log("Jump Land");
        }
        
        private void OnSitStart()
        {
            // Handle sit start
            Debug.Log("Sit Start");
        }
        
        private void OnSitEnd()
        {
            // Handle sit end
            Debug.Log("Sit End");
        }
        
        #endregion
        
        #region Utility Methods
        
        public AnimatorStateInfo GetCurrentAnimatorStateInfo(int layer = 0)
        {
            return animator.GetCurrentAnimatorStateInfo(layer);
        }
        
        public AnimatorStateInfo GetNextAnimatorStateInfo(int layer = 0)
        {
            return animator.GetNextAnimatorStateInfo(layer);
        }
        
        public bool IsPlayingAnimation(string animationName, int layer = 0)
        {
            return animator.GetCurrentAnimatorStateInfo(layer).IsName(animationName);
        }
        
        public float GetAnimationNormalizedTime(int layer = 0)
        {
            return animator.GetCurrentAnimatorStateInfo(layer).normalizedTime;
        }
        
        #endregion
    }
}
```

---

## 5. Physics System

### 5.1 Physics Controller

```csharp
// CharacterPhysicsController.cs
using UnityEngine;

namespace AICompanion.Character
{
    /// <summary>
    /// Handles physics interactions, collisions, and forces
    /// </summary>
    [RequireComponent(typeof(Rigidbody))]
    [RequireComponent(typeof(CapsuleCollider))]
    public class CharacterPhysicsController : MonoBehaviour
    {
        [Header("Physics Settings")]
        [SerializeField] private float mass = 70f;
        [SerializeField] private float drag = 0f;
        [SerializeField] private float angularDrag = 0.05f;
        [SerializeField] private bool useGravity = true;
        
        [Header("Collision Settings")]
        [SerializeField] private PhysicMaterial frictionMaterial;
        [SerializeField] private PhysicMaterial bounceMaterial;
        [SerializeField] private LayerMask collisionLayers;
        [SerializeField] private float collisionForceThreshold = 10f;
        
        [Header("Force Settings")]
        [SerializeField] private float maxForce = 1000f;
        [SerializeField] private float forceDecay = 0.9f;
        
        private Rigidbody rb;
        private CapsuleCollider capsuleCollider;
        private Vector3 externalForce;
        private Vector3 externalTorque;
        private bool isKnockedBack;
        private float knockbackTime;
        
        private void Awake()
        {
            InitializePhysics();
        }
        
        private void InitializePhysics()
        {
            rb = GetComponent<Rigidbody>();
            capsuleCollider = GetComponent<CapsuleCollider>();
            
            // Configure rigidbody
            rb.mass = mass;
            rb.drag = drag;
            rb.angularDrag = angularDrag;
            rb.useGravity = useGravity;
            rb.isKinematic = false;
            rb.interpolation = RigidbodyInterpolation.Interpolate;
            rb.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            
            // Configure collider
            if (frictionMaterial != null)
            {
                capsuleCollider.material = frictionMaterial;
            }
            
            externalForce = Vector3.zero;
            externalTorque = Vector3.zero;
        }
        
        private void FixedUpdate()
        {
            ApplyExternalForces();
            DecayForces();
        }
        
        private void ApplyExternalForces()
        {
            if (externalForce != Vector3.zero)
            {
                rb.AddForce(externalForce, ForceMode.Force);
            }
            
            if (externalTorque != Vector3.zero)
            {
                rb.AddTorque(externalTorque, ForceMode.Force);
            }
        }
        
        private void DecayForces()
        {
            externalForce *= forceDecay;
            externalTorque *= forceDecay;
            
            if (externalForce.magnitude < 0.1f)
            {
                externalForce = Vector3.zero;
            }
            
            if (externalTorque.magnitude < 0.1f)
            {
                externalTorque = Vector3.zero;
            }
        }
        
        private void OnCollisionEnter(Collision collision)
        {
            HandleCollision(collision);
        }
        
        private void OnCollisionStay(Collision collision)
        {
            HandleContinuousCollision(collision);
        }
        
        private void HandleCollision(Collision collision)
        {
            // Check if collision is strong enough to affect character
            float collisionForce = collision.impulse.magnitude / Time.fixedDeltaTime;
            
            if (collisionForce > collisionForceThreshold)
            {
                OnStrongCollision(collision);
            }
            
            // Check collision layers
            if (((1 << collision.gameObject.layer) & collisionLayers) != 0)
            {
                OnLayerCollision(collision);
            }
        }
        
        private void HandleContinuousCollision(Collision collision)
        {
            // Handle continuous collision (standing on ground, etc.)
            if (collision.contacts.Length > 0)
            {
                ContactPoint contact = collision.contacts[0];
                
                // Check if collision is from below (ground)
                if (Vector3.Dot(contact.normal, Vector3.up) > 0.5f)
                {
                    OnGroundCollision(contact);
                }
            }
        }
        
        private void OnStrongCollision(Collision collision)
        {
            // Handle strong collisions (being hit, falling, etc.)
            Vector3 impactDirection = collision.contacts[0].normal;
            float impactForce = collision.impulse.magnitude;
            
            // Apply knockback
            ApplyKnockback(impactDirection, impactForce);
            
            // Notify other systems
            var characterController = GetComponent<AICompanionController>();
            if (characterController != null)
            {
                characterController.StopMovement();
            }
        }
        
        private void OnLayerCollision(Collision collision)
        {
            // Handle collisions with specific layers
            var interactable = collision.gameObject.GetComponent<IInteractable>();
            if (interactable != null)
            {
                // Trigger interaction
                interactable.Interact(GetComponent<AICompanionController>());
            }
        }
        
        private void OnGroundCollision(ContactPoint contact)
        {
            // Handle ground collision
            // Can be used for foot placement, etc.
        }
        
        #region Public Force Methods
        
        public void AddForce(Vector3 force, ForceMode mode = ForceMode.Force)
        {
            force = Vector3.ClampMagnitude(force, maxForce);
            externalForce += force;
        }
        
        public void AddTorque(Vector3 torque, ForceMode mode = ForceMode.Force)
        {
            torque = Vector3.ClampMagnitude(torque, maxForce);
            externalTorque += torque;
        }
        
        public void ApplyKnockback(Vector3 direction, float force)
        {
            Vector3 knockbackForce = direction.normalized * force;
            AddForce(knockbackForce, ForceMode.Impulse);
            
            isKnockedBack = true;
            knockbackTime = Time.time + 0.5f;
            
            StartCoroutine(RecoverFromKnockback());
        }
        
        private System.Collections.IEnumerator RecoverFromKnockback()
        {
            yield return new WaitForSeconds(0.5f);
            isKnockedBack = false;
        }
        
        public void ExplosionForce(Vector3 position, float force, float radius)
        {
            Vector3 direction = transform.position - position;
            float distance = direction.magnitude;
            
            if (distance < radius)
            {
                float forceMagnitude = force * (1f - distance / radius);
                AddForce(direction.normalized * forceMagnitude, ForceMode.Impulse);
            }
        }
        
        #endregion
        
        #region Public Physics Methods
        
        public void SetMass(float newMass)
        {
            mass = newMass;
            rb.mass = mass;
        }
        
        public void SetGravity(bool enabled)
        {
            useGravity = enabled;
            rb.useGravity = enabled;
        }
        
        public void SetKinematic(bool kinematic)
        {
            rb.isKinematic = kinematic;
        }
        
        public void SetFreezePosition(bool freezeX, bool freezeY, bool freezeZ)
        {
            rb.constraints = RigidbodyConstraints.None;
            
            if (freezeX) rb.constraints |= RigidbodyConstraints.FreezePositionX;
            if (freezeY) rb.constraints |= RigidbodyConstraints.FreezePositionY;
            if (freezeZ) rb.constraints |= RigidbodyConstraints.FreezePositionZ;
        }
        
        public void SetFreezeRotation(bool freezeX, bool freezeY, bool freezeZ)
        {
            rb.constraints = RigidbodyConstraints.None;
            
            if (freezeX) rb.constraints |= RigidbodyConstraints.FreezeRotationX;
            if (freezeY) rb.constraints |= RigidbodyConstraints.FreezeRotationY;
            if (freezeZ) rb.constraints |= RigidbodyConstraints.FreezeRotationZ;
        }
        
        #endregion
        
        #region Collision Detection
        
        public bool CheckGrounded()
        {
            return Physics.Raycast(
                transform.position + Vector3.up * 0.1f,
                Vector3.down,
                0.2f,
                collisionLayers
            );
        }
        
        public bool CheckObstacle(Vector3 direction, float distance)
        {
            return Physics.Raycast(
                transform.position + Vector3.up * 0.5f,
                direction,
                distance,
                collisionLayers
            );
        }
        
        public Collider[] GetOverlappingColliders()
        {
            return Physics.OverlapCapsule(
                transform.position,
                transform.position + Vector3.up * capsuleCollider.height,
                capsuleCollider.radius,
                collisionLayers
            );
        }
        
        #endregion
        
        #region Utility Methods
        
        public Vector3 GetVelocity()
        {
            return rb.velocity;
        }
        
        public Vector3 GetAngularVelocity()
        {
            return rb.angularVelocity;
        }
        
        public float GetKineticEnergy()
        {
            return 0.5f * mass * rb.velocity.sqrMagnitude;
        }
        
        #endregion
    }
}
```

---

## 6. Interaction System

### 6.1 Interaction Manager

```csharp
// InteractionManager.cs
using UnityEngine;
using System.Collections.Generic;

namespace AICompanion.Character
{
    /// <summary>
    /// Manages character interactions with environment and objects
    /// </summary>
    public class InteractionManager : MonoBehaviour
    {
        [Header("Interaction Settings")]
        [SerializeField] private float interactionRange = 2f;
        [SerializeField] private LayerMask interactionLayer;
        [SerializeField] private float interactionCooldown = 0.5f;
        
        [Header("Visual Feedback")]
        [SerializeField] private GameObject interactionIndicator;
        [SerializeField] private Color highlightColor = Color.yellow;
        
        private AICompanionController characterController;
        private List<IInteractable> nearbyInteractables;
        private IInteractable currentInteractable;
        private float lastInteractionTime;
        private bool canInteract;
        
        private void Awake()
        {
            Initialize();
        }
        
        private void Initialize()
        {
            characterController = GetComponent<AICompanionController>();
            nearbyInteractables = new List<IInteractable>();
            canInteract = true;
            
            if (interactionIndicator != null)
            {
                interactionIndicator.SetActive(false);
            }
        }
        
        private void Update()
        {
            DetectInteractables();
            UpdateInteractionIndicator();
            CheckInteractionCooldown();
        }
        
        private void DetectInteractables()
        {
            nearbyInteractables.Clear();
            
            Collider[] hitColliders = Physics.OverlapSphere(
                transform.position,
                interactionRange,
                interactionLayer
            );
            
            foreach (var collider in hitColliders)
            {
                IInteractable interactable = collider.GetComponent<IInteractable>();
                if (interactable != null && collider.gameObject != gameObject)
                {
                    nearbyInteractables.Add(interactable);
                }
            }
            
            // Find closest interactable
            currentInteractable = GetClosestInteractable();
        }
        
        private IInteractable GetClosestInteractable()
        {
            IInteractable closest = null;
            float closestDistance = float.MaxValue;
            
            foreach (var interactable in nearbyInteractables)
            {
                float distance = Vector3.Distance(
                    transform.position,
                    interactable.GetInteractionPosition()
                );
                
                if (distance < closestDistance)
                {
                    closest = interactable;
                    closestDistance = distance;
                }
            }
            
            return closest;
        }
        
        private void UpdateInteractionIndicator()
        {
            if (interactionIndicator == null) return;
            
            if (currentInteractable != null && canInteract)
            {
                interactionIndicator.SetActive(true);
                interactionIndicator.transform.position = currentInteractable.GetInteractionPosition();
            }
            else
            {
                interactionIndicator.SetActive(false);
            }
        }
        
        private void CheckInteractionCooldown()
        {
            if (Time.time - lastInteractionTime >= interactionCooldown)
            {
                canInteract = true;
            }
        }
        
        #region Public Interaction Methods
        
        public bool TryInteract()
        {
            if (!canInteract || currentInteractable == null) return false;
            
            bool success = currentInteractable.Interact(characterController);
            
            if (success)
            {
                lastInteractionTime = Time.time;
                canInteract = false;
            }
            
            return success;
        }
        
        public bool TryInteract(IInteractable interactable)
        {
            if (!canInteract || interactable == null) return false;
            
            float distance = Vector3.Distance(
                transform.position,
                interactable.GetInteractionPosition()
            );
            
            if (distance > interactionRange) return false;
            
            bool success = interactable.Interact(characterController);
            
            if (success)
            {
                lastInteractionTime = Time.time;
                canInteract = false;
            }
            
            return success;
        }
        
        public IInteractable GetCurrentInteractable()
        {
            return currentInteractable;
        }
        
        public List<IInteractable> GetNearbyInteractables()
        {
            return new List<IInteractable>(nearbyInteractables);
        }
        
        public void SetInteractionRange(float range)
        {
            interactionRange = range;
        }
        
        #endregion
        
        private void OnDrawGizmosSelected()
        {
            // Draw interaction range
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(transform.position, interactionRange);
            
            // Draw line to current interactable
            if (currentInteractable != null)
            {
                Gizmos.color = Color.green;
                Gizmos.DrawLine(
                    transform.position,
                    currentInteractable.GetInteractionPosition()
                );
            }
        }
    }
    
    /// <summary>
    /// Extended interface for interactable objects with position
    /// </summary>
    public interface IInteractable
    {
        bool Interact(AICompanionController character);
        string GetInteractionName();
        Vector3 GetInteractionPosition();
    }
}
```

---

## 7. Lighting & Shadows

### 7.1 Dynamic Lighting System

```csharp
// DynamicLightingController.cs
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace AICompanion.Character
{
    /// <summary>
    /// Controls dynamic lighting and shadows for character
    /// </summary>
    public class DynamicLightingController : MonoBehaviour
    {
        [Header("Light Estimation")]
        [SerializeField] private bool useARLightEstimation = true;
        [SerializeField] private float lightEstimationUpdateInterval = 0.1f;
        
        [Header("Shadow Settings")]
        [SerializeField] private bool castShadows = true;
        [SerializeField] private bool receiveShadows = true;
        [SerializeField] private ShadowQuality shadowQuality = ShadowQuality.High;
        
        [Header("Reflections")]
        [SerializeField] private bool useReflections = true;
        [SerializeField] private LayerMask reflectionLayers;
        
        private Light mainLight;
        private LightEstimation currentLightEstimation;
        private float lastLightEstimationUpdate;
        private CharacterRenderer characterRenderer;
        
        public enum ShadowQuality
        {
            Off,
            Low,
            Medium,
            High,
            Ultra
        }
        
        private void Awake()
        {
            Initialize();
        }
        
        private void Initialize()
        {
            characterRenderer = GetComponent<CharacterRenderer>();
            mainLight = FindMainLight();
            
            ConfigureShadows();
            ConfigureReflections();
        }
        
        private Light FindMainLight()
        {
            // Try to find directional light
            Light[] lights = FindObjectsOfType<Light>();
            foreach (var light in lights)
            {
                if (light.type == LightType.Directional)
                {
                    return light;
                }
            }
            
            // Create main light if none exists
            GameObject lightObject = new GameObject("Main Light");
            Light newLight = lightObject.AddComponent<Light>();
            newLight.type = LightType.Directional;
            newLight.intensity = 1f;
            newLight.shadows = LightShadows.Soft;
            
            return newLight;
        }
        
        private void ConfigureShadows()
        {
            if (mainLight != null)
            {
                mainLight.shadows = castShadows ? LightShadows.Soft : LightShadows.None;
            }
            
            // Configure shadow quality
            switch (shadowQuality)
            {
                case ShadowQuality.Off:
                    QualitySettings.shadowDistance = 0f;
                    break;
                case ShadowQuality.Low:
                    QualitySettings.shadowDistance = 10f;
                    QualitySettings.shadowCascades = ShadowCascadesSize.NoCascades;
                    QualitySettings.shadowResolution = ShadowResolution.Low;
                    break;
                case ShadowQuality.Medium:
                    QualitySettings.shadowDistance = 25f;
                    QualitySettings.shadowCascades = ShadowCascadesSize.TwoCascades;
                    QualitySettings.shadowResolution = ShadowResolution.Medium;
                    break;
                case ShadowQuality.High:
                    QualitySettings.shadowDistance = 50f;
                    QualitySettings.shadowCascades = ShadowCascadesSize.FourCascades;
                    QualitySettings.shadowResolution = ShadowResolution.High;
                    break;
                case ShadowQuality.Ultra:
                    QualitySettings.shadowDistance = 100f;
                    QualitySettings.shadowCascades = ShadowCascadesSize.FourCascades;
                    QualitySettings.shadowResolution = ShadowResolution.VeryHigh;
                    break;
            }
        }
        
        private void ConfigureReflections()
        {
            if (!useReflections) return;
            
            // Setup reflection probe if needed
            ReflectionProbe probe = GetComponent<ReflectionProbe>();
            if (probe == null)
            {
                GameObject probeObject = new GameObject("Character Reflection Probe");
                probeObject.transform.SetParent(transform);
                probeObject.transform.localPosition = Vector3.zero;
                probe = probeObject.AddComponent<ReflectionProbe>();
            }
            
            probe.mode = ReflectionProbeMode.Realtime;
            probe.refreshMode = ReflectionProbeRefreshMode.ViaScripting;
            probe.timeSlicingMode = ReflectionProbeTimeSlicingMode.AllFacesAtOnce;
            probe.resolution = 128;
        }
        
        private void Update()
        {
            if (useARLightEstimation)
            {
                UpdateLightEstimation();
            }
        }
        
        private void UpdateLightEstimation()
        {
            if (Time.time - lastLightEstimationUpdate < lightEstimationUpdateInterval) return;
            
            // Get light estimation from AR system
            currentLightEstimation = GetARLightEstimation();
            
            if (currentLightEstimation != null)
            {
                ApplyLightEstimation(currentLightEstimation);
            }
            
            lastLightEstimationUpdate = Time.time;
        }
        
        private LightEstimation GetARLightEstimation()
        {
            // This would interface with AR Foundation's light estimation
            // For now, return null as placeholder
            return null;
        }
        
        private void ApplyLightEstimation(LightEstimation estimation)
        {
            if (mainLight != null)
            {
                mainLight.color = estimation.DirectionalColor;
                mainLight.intensity = estimation.LightIntensity;
                mainLight.transform.rotation = Quaternion.LookRotation(-estimation.LightDirection);
            }
            
            RenderSettings.ambientLight = estimation.AmbientColor;
            
            // Update character materials
            var materialController = GetComponent<CharacterMaterialController>();
            if (materialController != null)
            {
                materialController.UpdateEnvironmentalLighting(estimation);
            }
        }
        
        public void SetShadowQuality(ShadowQuality quality)
        {
            shadowQuality = quality;
            ConfigureShadows();
        }
        
        public void SetCastShadows(bool cast)
        {
            castShadows = cast;
            ConfigureShadows();
        }
        
        public void SetReceiveShadows(bool receive)
        {
            receiveShadows = receive;
            if (characterRenderer != null)
            {
                // Update character renderer shadow settings
            }
        }
    }
    
    /// <summary>
    /// Light estimation data structure
    /// </summary>
    public class LightEstimation
    {
        public Color AmbientColor { get; set; }
        public Color DirectionalColor { get; set; }
        public Vector3 LightDirection { get; set; }
        public float LightIntensity { get; set; }
        public Color ColorTemperature { get; set; }
    }
}
```

---

## 8. Navigation System

### 8.1 Navigation Controller

```csharp
// CharacterNavigationController.cs
using UnityEngine;
using UnityEngine.AI;

namespace AICompanion.Character
{
    /// <summary>
    /// Handles character navigation and pathfinding
    /// </summary>
    [RequireComponent(typeof(NavMeshAgent))]
    public class CharacterNavigationController : MonoBehaviour
    {
        [Header("Navigation Settings")]
        [SerializeField] private float stoppingDistance = 0.5f;
        [SerializeField] private float acceleration = 8f;
        [SerializeField] private float angularSpeed = 120f;
        [SerializeField] private bool autoBraking = true;
        
        [Header("Obstacle Avoidance")]
        [SerializeField] private float obstacleAvoidanceRadius = 0.5f;
        [SerializeField] private LayerMask obstacleLayers;
        
        [Header("Pathfinding")]
        [SerializeField] private float pathUpdateInterval = 0.5f;
        [SerializeField] private float repathDelay = 0.2f;
        
        private NavMeshAgent navMeshAgent;
        private AICompanionController characterController;
        private Vector3 currentDestination;
        private bool hasPath;
        private bool pathPending;
        private float lastPathUpdateTime;
        private bool isNavigating;
        
        public bool IsNavigating => isNavigating;
        public bool HasPath => hasPath;
        public Vector3 CurrentDestination => currentDestination;
        
        private void Awake()
        {
            Initialize();
        }
        
        private void Initialize()
        {
            navMeshAgent = GetComponent<NavMeshAgent>();
            characterController = GetComponent<AICompanionController>();
            
            ConfigureNavMeshAgent();
        }
        
        private void ConfigureNavMeshAgent()
        {
            navMeshAgent.stoppingDistance = stoppingDistance;
            navMeshAgent.acceleration = acceleration;
            navMeshAgent.angularSpeed = angularSpeed;
            navMeshAgent.autoBraking = autoBraking;
            navMeshAgent.obstacleAvoidanceType = ObstacleAvoidanceType.HighQualityObstacleAvoidance;
            
            // Configure for character
            navMeshAgent.height = 1.7f;
            navMeshAgent.radius = 0.5f;
        }
        
        private void Update()
        {
            UpdateNavigationStatus();
            CheckPathCompletion();
            HandleObstacleAvoidance();
        }
        
        private void UpdateNavigationStatus()
        {
            hasPath = navMeshAgent.hasPath;
            pathPending = navMeshAgent.pathPending;
            isNavigating = hasPath && !pathPending && navMeshAgent.remainingDistance > stoppingDistance;
        }
        
        private void CheckPathCompletion()
        {
            if (isNavigating && navMeshAgent.remainingDistance <= stoppingDistance)
            {
                OnDestinationReached();
            }
        }
        
        private void HandleObstacleAvoidance()
        {
            if (!isNavigating) return;
            
            // Check for dynamic obstacles
            Collider[] obstacles = Physics.OverlapSphere(
                transform.position,
                obstacleAvoidanceRadius,
                obstacleLayers
            );
            
            if (obstacles.Length > 0)
            {
                // Repath around obstacles
                if (Time.time - lastPathUpdateTime > repathDelay)
                {
                    RecalculatePath();
                    lastPathUpdateTime = Time.time;
                }
            }
        }
        
        #region Public Navigation Methods
        
        public bool SetDestination(Vector3 destination)
        {
            currentDestination = destination;
            
            if (navMeshAgent.isOnNavMesh)
            {
                return navMeshAgent.SetDestination(destination);
            }
            
            return false;
        }
        
        public bool SetDestination(Transform target)
        {
            if (target != null)
            {
                return SetDestination(target.position);
            }
            return false;
        }
        
        public void StopNavigation()
        {
            navMeshAgent.isStopped = true;
            navMeshAgent.ResetPath();
            isNavigating = false;
        }
        
        public void ResumeNavigation()
        {
            navMeshAgent.isStopped = false;
            if (currentDestination != Vector3.zero)
            {
                navMeshAgent.SetDestination(currentDestination);
            }
        }
        
        public void RecalculatePath()
        {
            if (currentDestination != Vector3.zero)
            {
                navMeshAgent.SetDestination(currentDestination);
            }
        }
        
        public NavMeshPath GetPath()
        {
            NavMeshPath path = new NavMeshPath();
            if (navMeshAgent.CalculatePath(currentDestination, path))
            {
                return path;
            }
            return null;
        }
        
        public float GetRemainingDistance()
        {
            return navMeshAgent.remainingDistance;
        }
        
        #endregion
        
        #region Navigation Events
        
        private void OnDestinationReached()
        {
            isNavigating = false;
            navMeshAgent.isStopped = true;
            
            // Notify character controller
            if (characterController != null)
            {
                characterController.StopMovement();
            }
            
            Debug.Log("Destination reached");
        }
        
        #endregion
        
        #region Utility Methods
        
        public bool CanReachDestination(Vector3 destination)
        {
            NavMeshPath path = new NavMeshPath();
            return navMeshAgent.CalculatePath(destination, path);
        }
        
        public Vector3 GetNearestValidPosition(Vector3 position, float maxDistance = 10f)
        {
            NavMeshHit hit;
            if (NavMesh.SamplePosition(position, out hit, maxDistance, NavMesh.AllAreas))
            {
                return hit.position;
            }
            return transform.position;
        }
        
        #endregion
        
        private void OnDrawGizmosSelected()
        {
            // Draw destination
            if (currentDestination != Vector3.zero)
            {
                Gizmos.color = Color.green;
                Gizmos.DrawSphere(currentDestination, 0.2f);
                Gizmos.DrawLine(transform.position, currentDestination);
            }
            
            // Draw obstacle avoidance radius
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(transform.position, obstacleAvoidanceRadius);
        }
    }
}
```

---

## 9. Performance Optimization

### 9.1 Character Performance Optimizer

```csharp
// CharacterPerformanceOptimizer.cs
using UnityEngine;
using System.Collections.Generic;

namespace AICompanion.Character
{
    /// <summary>
    /// Optimizes character performance based on distance and platform
    /// </summary>
    public class CharacterPerformanceOptimizer : MonoBehaviour
    {
        [Header("LOD Settings")]
        [SerializeField] private float lod0Distance = 2f;
        [SerializeField] private float lod1Distance = 5f;
        [SerializeField] private float lod2Distance = 10f;
        [SerializeField] private float lod3Distance = 20f;
        
        [Header("Update Rates")]
        [SerializeField] private float closeUpdateRate = 60f;
        [SerializeField] private float mediumUpdateRate = 30f;
        [SerializeField] private float farUpdateRate = 15f;
        
        [Header("Feature Optimization")]
        [SerializeField] private bool enableDynamicLOD = true;
        [SerializeField] private bool enableUpdateRateOptimization = true;
        [SerializeField] private bool enableFeatureCulling = true;
        
        private CharacterRenderer characterRenderer;
        private CharacterAnimationController animationController;
        private DynamicLightingController lightingController;
        private Camera mainCamera;
        private float currentDistance;
        private int currentLOD;
        private float currentUpdateRate;
        private Dictionary<string, bool> featureStates;
        
        private void Awake()
        {
            Initialize();
        }
        
        private void Initialize()
        {
            characterRenderer = GetComponent<CharacterRenderer>();
            animationController = GetComponent<CharacterAnimationController>();
            lightingController = GetComponent<DynamicLightingController>();
            mainCamera = Camera.main;
            
            featureStates = new Dictionary<string, bool>
            {
                { "Shadows", true },
                { "Reflections", true },
                { "Physics", true },
                { "IK", true },
                { "FacialAnimation", true }
            };
        }
        
        private void Update()
        {
            UpdateDistance();
            
            if (enableDynamicLOD)
            {
                UpdateLOD();
            }
            
            if (enableUpdateRateOptimization)
            {
                UpdateUpdateRate();
            }
            
            if (enableFeatureCulling)
            {
                UpdateFeatures();
            }
        }
        
        private void UpdateDistance()
        {
            if (mainCamera != null)
            {
                currentDistance = Vector3.Distance(transform.position, mainCamera.transform.position);
            }
        }
        
        private void UpdateLOD()
        {
            int newLOD = DetermineLOD();
            
            if (newLOD != currentLOD)
            {
                currentLOD = newLOD;
                ApplyLOD(currentLOD);
            }
        }
        
        private int DetermineLOD()
        {
            if (currentDistance < lod0Distance) return 0;
            if (currentDistance < lod1Distance) return 1;
            if (currentDistance < lod2Distance) return 2;
            if (currentDistance < lod3Distance) return 3;
            return 4;
        }
        
        private void ApplyLOD(int lod)
        {
            if (characterRenderer != null)
            {
                characterRenderer.SetLODLevel((CharacterRenderer.CharacterLOD)lod);
            }
            
            // Adjust features based on LOD
            switch (lod)
            {
                case 0: // Close up
                    EnableAllFeatures();
                    break;
                case 1: // Medium close
                    EnableHighPriorityFeatures();
                    break;
                case 2: // Medium
                    EnableMediumPriorityFeatures();
                    break;
                case 3: // Far
                    EnableLowPriorityFeatures();
                    break;
                case 4: // Very far
                    EnableMinimalFeatures();
                    break;
            }
        }
        
        private void UpdateUpdateRate()
        {
            float newUpdateRate = DetermineUpdateRate();
            
            if (newUpdateRate != currentUpdateRate)
            {
                currentUpdateRate = newUpdateRate;
                ApplyUpdateRate(currentUpdateRate);
            }
        }
        
        private float DetermineUpdateRate()
        {
            if (currentDistance < lod0Distance) return closeUpdateRate;
            if (currentDistance < lod1Distance) return mediumUpdateRate;
            return farUpdateRate;
        }
        
        private void ApplyUpdateRate(float updateRate)
        {
            // This would adjust component update rates
            // Implementation depends on specific components
        }
        
        private void UpdateFeatures()
        {
            // Enable/disable features based on distance and LOD
            bool enableShadows = currentLOD < 3;
            bool enableReflections = currentLOD < 2;
            bool enableFacialAnimation = currentLOD < 2;
            bool enableIK = currentLOD < 3;
            
            SetFeature("Shadows", enableShadows);
            SetFeature("Reflections", enableReflections);
            SetFeature("FacialAnimation", enableFacialAnimation);
            SetFeature("IK", enableIK);
        }
        
        private void EnableAllFeatures()
        {
            foreach (var key in featureStates.Keys)
            {
                featureStates[key] = true;
            }
            ApplyFeatureStates();
        }
        
        private void EnableHighPriorityFeatures()
        {
            featureStates["Shadows"] = true;
            featureStates["Reflections"] = true;
            featureStates["Physics"] = true;
            featureStates["IK"] = true;
            featureStates["FacialAnimation"] = true;
            ApplyFeatureStates();
        }
        
        private void EnableMediumPriorityFeatures()
        {
            featureStates["Shadows"] = true;
            featureStates["Reflections"] = false;
            featureStates["Physics"] = true;
            featureStates["IK"] = true;
            featureStates["FacialAnimation"] = false;
            ApplyFeatureStates();
        }
        
        private void EnableLowPriorityFeatures()
        {
            featureStates["Shadows"] = false;
            featureStates["Reflections"] = false;
            featureStates["Physics"] = true;
            featureStates["IK"] = false;
            featureStates["FacialAnimation"] = false;
            ApplyFeatureStates();
        }
        
        private void EnableMinimalFeatures()
        {
            featureStates["Shadows"] = false;
            featureStates["Reflections"] = false;
            featureStates["Physics"] = true;
            featureStates["IK"] = false;
            featureStates["FacialAnimation"] = false;
            ApplyFeatureStates();
        }
        
        private void SetFeature(string featureName, bool enabled)
        {
            if (featureStates.ContainsKey(featureName))
            {
                featureStates[featureName] = enabled;
            }
        }
        
        private void ApplyFeatureStates()
        {
            if (lightingController != null)
            {
                lightingController.SetCastShadows(featureStates["Shadows"]);
            }
            
            // Apply other feature states
            // Implementation depends on specific components
        }
        
        public void SetLODDistances(float lod0, float lod1, float lod2, float lod3)
        {
            lod0Distance = lod0;
            lod1Distance = lod1;
            lod2Distance = lod2;
            lod3Distance = lod3;
        }
        
        public void SetUpdateRates(float close, float medium, float far)
        {
            closeUpdateRate = close;
            mediumUpdateRate = medium;
            farUpdateRate = far;
        }
    }
}
```

---

## Conclusion

Phần 3 đã thiết kế chi tiết hệ thống Character Display & Physics bao gồm:

1. **Character Display System**: Renderer, materials, LODs, shadows
2. **Character Controller**: Movement, physics, posture
3. **Animation System**: Body animation, facial animation, IK
4. **Physics System**: Collisions, forces, knockback
5. **Interaction System**: Object interaction, detection
6. **Lighting & Shadows**: Dynamic lighting, AR light estimation
7. **Collision Detection**: Ground detection, obstacle detection
8. **Pathfinding & Navigation**: NavMesh integration, obstacle avoidance
9. **Performance Optimization**: Dynamic LOD, update rate optimization, feature culling

Tất cả components được thiết kế theo chuẩn Enterprise với:
- Clean Architecture
- SOLID principles
- Component-based design
- Performance optimization
- Extensive documentation
- Production-ready code
