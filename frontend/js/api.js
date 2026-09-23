/**
 * CrowdEye AI - Backend API Communication Layer
 * Utilizes the standard Fetch API to interact with the FastAPI backend service.
 */

const API_CONFIG = {
  baseUrl: window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "http://127.0.0.1:8000",
  timeoutMs: 4000
};

// Internal fetch wrapper with timeout and fallback
async function fetchWithTimeout(endpoint, options = {}) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), API_CONFIG.timeoutMs);

  try {
    const response = await fetch(`${API_CONFIG.baseUrl}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      }
    });
    clearTimeout(id);
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

/**
 * Fetch current crowd density, headcounts, and risk level across all active zones
 */
async function getCrowdStatus() {
  try {
    const data = await fetchWithTimeout("/api/v1/crowd/status");
    return { success: true, source: "backend", data };
  } catch (err) {
    console.warn("[CrowdEye API] Backend unavailable, using standby telemetry:", err.message);
    return {
      success: true,
      source: "standby",
      data: {
        total_people: 1420,
        current_density: 2.4, // ppl / m²
        risk_level: "MODERATE",
        risk_score: 0.42,
        timestamp: new Date().toISOString(),
        zones: [
          { zone: "Main Gate", people_count: 480, density: 3.2, risk: "HIGH", lat: 28.6139, lng: 77.2090 },
          { zone: "Food Court", people_count: 310, density: 1.8, risk: "LOW", lat: 28.6145, lng: 77.2105 },
          { zone: "Stage Area", people_count: 520, density: 3.8, risk: "CRITICAL", lat: 28.6132, lng: 77.2082 },
          { zone: "Emergency Exit A", people_count: 110, density: 0.9, risk: "LOW", lat: 28.6125, lng: 77.2095 }
        ]
      }
    };
  }
}

/**
 * Fetch active and recent security alerts
 */
async function getAlerts() {
  try {
    const data = await fetchWithTimeout("/api/v1/alerts");
    return { success: true, source: "backend", data: data.alerts || [] };
  } catch (err) {
    console.warn("[CrowdEye API] Backend unavailable, using standby alerts:", err.message);
    return {
      success: true,
      source: "standby",
      data: [
        {
          id: "alt-001",
          zone: "Stage Area",
          message: "High crowd surge detected (density exceeded 3.5 ppl/m²)",
          severity: "CRITICAL",
          created_at: new Date(Date.now() - 5 * 60000).toISOString(),
          resolved: false
        },
        {
          id: "alt-002",
          zone: "Main Gate",
          message: "Bottleneck forming at security turnstiles",
          severity: "WARNING",
          created_at: new Date(Date.now() - 12 * 60000).toISOString(),
          resolved: false
        },
        {
          id: "alt-003",
          zone: "Food Court",
          message: "Normal crowd dispersion rate restored",
          severity: "INFO",
          created_at: new Date(Date.now() - 25 * 60000).toISOString(),
          resolved: true
        }
      ]
    };
  }
}

/**
 * Fetch registered events from the system
 */
async function getEvents() {
  try {
    const data = await fetchWithTimeout("/api/v1/events");
    return { success: true, source: "backend", data: data.events || [] };
  } catch (err) {
    console.warn("[CrowdEye API] Backend unavailable, using standby events:", err.message);
    return {
      success: true,
      source: "standby",
      data: [
        {
          id: "evt-001",
          event_name: "Metro Grand Arena 2026",
          location: "Central Pavilion Zone A-D",
          date: new Date().toISOString(),
          status: "LIVE_MONITORING"
        },
        {
          id: "evt-002",
          event_name: "Tech Summit Keynote",
          location: "Convention Hall B",
          date: new Date(Date.now() + 86400000).toISOString(),
          status: "SCHEDULED"
        }
      ]
    };
  }
}

/**
 * Ping backend to check operational status
 */
async function checkBackendHealth() {
  try {
    const res = await fetchWithTimeout("/");
    return { online: true, project: res.project, status: res.status };
  } catch (err) {
    return { online: false, error: err.message };
  }
}
