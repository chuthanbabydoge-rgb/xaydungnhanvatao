using UnityEngine;
using UnityEngine.Rendering;
using System.Collections.Generic;

namespace AICompanion.Rendering
{
    /// <summary>
    /// Reflection Probe Controller - follows Single Responsibility Principle
    /// Manages reflection probes for realistic environment reflections
    /// </summary>
    public class ReflectionProbeController : MonoBehaviour
    {
        [Header("Reflection Probe Settings")]
        [SerializeField] private ReflectionProbe mainReflectionProbe;
        [SerializeField] private bool useRealtimeReflections = true;
        [SerializeField] private int reflectionResolution = 128;
        [SerializeField] private float refreshInterval = 0.1f;

        [Header("Probe Placement")]
        [SerializeField] private float probeSpacing = 5f;
        [SerializeField] private Bounds probeArea = new Bounds(Vector3.zero, new Vector3(20f, 10f, 20f));
        [SerializeField] private bool autoGenerateProbes = true;

        [Header("HDRP Settings")]
        [SerializeField] private HDReflectionProbe hdReflectionProbe;

        private List<ReflectionProbe> reflectionProbes = new List<ReflectionProbe>();
        private float lastRefreshTime;
        private bool isInitialized;

        private void Start()
        {
            InitializeReflectionProbes();
        }

        private void InitializeReflectionProbes()
        {
            // Configure main reflection probe
            if (mainReflectionProbe == null)
            {
                mainReflectionProbe = GetComponent<ReflectionProbe>();
            }

            if (mainReflectionProbe == null)
            {
                GameObject probeGO = new GameObject("Main Reflection Probe");
                probeGO.transform.parent = transform;
                mainReflectionProbe = probeGO.AddComponent<ReflectionProbe>();
            }

            // Configure main probe
            ConfigureReflectionProbe(mainReflectionProbe);

            // Generate additional probes if enabled
            if (autoGenerateProbes)
            {
                GenerateReflectionProbes();
            }

            // Configure HDRP probe if available
            #if UNITY_2021_2_OR_NEWER
            ConfigureHDRPProbe();
            #endif

            isInitialized = true;
        }

        private void ConfigureReflectionProbe(ReflectionProbe probe)
        {
            probe.resolution = reflectionResolution;
            probe.cullingMask = -1; // Reflect everything
            probe.clearFlags = ReflectionProbeClearFlags.Skybox;
            probe.timeSlicingMode = ReflectionProbeTimeSlicingMode.IndividualFacesSliced;
            probe.refreshMode = useRealtimeReflections ? 
                ReflectionProbeRefreshMode.Realtime : 
                ReflectionProbeRefreshMode.OnAwake;
        }

        #if UNITY_2021_2_OR_NEWER
        private void ConfigureHDRPProbe()
        {
            if (mainReflectionProbe != null)
            {
                hdReflectionProbe = mainReflectionProbe.GetComponent<HDReflectionProbe>();
                if (hdReflectionProbe == null)
                {
                    hdReflectionProbe = mainReflectionProbe.gameObject.AddComponent<HDReflectionProbe>();
                }

                // Configure HDRP reflection probe
                hdReflectionProbe probeSettings = hdReflectionProbe.probeSettings;
                probeSettings.resolution = reflectionResolution;
                probeSettings.influenceVolume.shape = InfluenceVolumeShape.Box;
                probeSettings.weight = 1f;
            }
        }
        #endif

        private void GenerateReflectionProbes()
        {
            Vector3 min = probeArea.min;
            Vector3 max = probeArea.max;

            for (float x = min.x; x <= max.x; x += probeSpacing)
            {
                for (float y = min.y; y <= max.y; y += probeSpacing)
                {
                    for (float z = min.z; z <= max.z; z += probeSpacing)
                    {
                        Vector3 probePosition = new Vector3(x, y, z);
                        CreateReflectionProbe(probePosition);
                    }
                }
            }
        }

        private void CreateReflectionProbe(Vector3 position)
        {
            GameObject probeGO = new GameObject($"Reflection Probe {reflectionProbes.Count}");
            probeGO.transform.position = position;
            probeGO.transform.parent = transform;

            ReflectionProbe probe = probeGO.AddComponent<ReflectionProbe>();
            ConfigureReflectionProbe(probe);

            reflectionProbes.Add(probe);
        }

        private void Update()
        {
            if (!isInitialized) return;

            UpdateReflectionProbes();
        }

        private void UpdateReflectionProbes()
        {
            // Refresh realtime reflections periodically
            if (useRealtimeReflections && Time.time - lastRefreshTime >= refreshInterval)
            {
                RefreshReflectionProbes();
                lastRefreshTime = Time.time;
            }
        }

        private void RefreshReflectionProbes()
        {
            // Refresh main probe
            if (mainReflectionProbe != null && mainReflectionProbe.refreshMode == ReflectionProbeRefreshMode.Realtime)
            {
                mainReflectionProbe.RenderProbe();
            }

            // Refresh additional probes
            foreach (ReflectionProbe probe in reflectionProbes)
            {
                if (probe.refreshMode == ReflectionProbeRefreshMode.Realtime)
                {
                    probe.RenderProbe();
                }
            }
        }

        public void SetMainReflectionProbe(ReflectionProbe probe)
        {
            mainReflectionProbe = probe;
            ConfigureReflectionProbe(probe);
        }

        public void SetReflectionResolution(int resolution)
        {
            reflectionResolution = resolution;
            
            if (mainReflectionProbe != null)
            {
                mainReflectionProbe.resolution = resolution;
            }

            foreach (ReflectionProbe probe in reflectionProbes)
            {
                probe.resolution = resolution;
            }
        }

        public void SetRealtimeReflectionsEnabled(bool enabled)
        {
            useRealtimeReflections = enabled;
            
            ReflectionProbeRefreshMode refreshMode = enabled ? 
                ReflectionProbeRefreshMode.Realtime : 
                ReflectionProbeRefreshMode.OnAwake;

            if (mainReflectionProbe != null)
            {
                mainReflectionProbe.refreshMode = refreshMode;
            }

            foreach (ReflectionProbe probe in reflectionProbes)
            {
                probe.refreshMode = refreshMode;
            }
        }

        public void SetRefreshInterval(float interval)
        {
            refreshInterval = interval;
        }

        public void SetProbeArea(Bounds area)
        {
            probeArea = area;
            
            // Regenerate probes
            ClearReflectionProbes();
            GenerateReflectionProbes();
        }

        public void SetProbeSpacing(float spacing)
        {
            probeSpacing = spacing;
            
            // Regenerate probes
            ClearReflectionProbes();
            GenerateReflectionProbes();
        }

        public void AddReflectionProbe(Vector3 position)
        {
            CreateReflectionProbe(position);
        }

        public void RemoveReflectionProbe(ReflectionProbe probe)
        {
            if (reflectionProbes.Contains(probe))
            {
                reflectionProbes.Remove(probe);
                Destroy(probe.gameObject);
            }
        }

        public void ClearReflectionProbes()
        {
            foreach (ReflectionProbe probe in reflectionProbes)
            {
                Destroy(probe.gameObject);
            }
            reflectionProbes.Clear();
        }

        public void BakeAllReflections()
        {
            // Bake all reflection probes
            if (mainReflectionProbe != null)
            {
                mainReflectionProbe.refreshMode = ReflectionProbeRefreshMode.OnAwake;
                mainReflectionProbe.RenderProbe();
            }

            foreach (ReflectionProbe probe in reflectionProbes)
            {
                probe.refreshMode = ReflectionProbeRefreshMode.OnAwake;
                probe.RenderProbe();
            }
        }

        public List<ReflectionProbe> GetReflectionProbes()
        {
            List<ReflectionProbe> allProbes = new List<ReflectionProbe>(reflectionProbes);
            if (mainReflectionProbe != null)
            {
                allProbes.Add(mainReflectionProbe);
            }
            return allProbes;
        }
    }
}
