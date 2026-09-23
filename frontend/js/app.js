/**
 * CrowdEye AI - Dashboard Application Controller
 * Handles Chart.js visualization, Leaflet.js interactive venue mapping,
 * and metric card updates.
 */

let densityChartInstance = null;
let venueMapInstance = null;
let mapMarkers = [];

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initChart();
  loadDashboardData();

  // Periodic refresh every 15 seconds
  setInterval(loadDashboardData, 15000);
});

/**
 * Initialize Leaflet.js map with custom dark tiles and zone markers
 */
function initMap() {
  const mapElement = document.getElementById("venue-map");
  if (!mapElement) return;

  // Center coordinate (Stadium / Public Event Venue representation)
  const defaultCoords = [28.6139, 77.2090];

  venueMapInstance = L.map("venue-map", {
    center: defaultCoords,
    zoom: 16,
    zoomControl: true,
    attributionControl: false
  });

  // Dark-themed OpenStreetMap tiles (CartoDB Dark Matter)
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd",
    maxZoom: 19
  }).addTo(venueMapInstance);

  // Initial zone coordinates
  const zones = [
    { name: "Main Gate (Zone A)", lat: 28.6145, lng: 77.2085, color: "#f59e0b", density: "3.2 ppl/m²", risk: "HIGH" },
    { name: "Food Court (Zone B)", lat: 28.6150, lng: 77.2105, color: "#10b981", density: "1.8 ppl/m²", risk: "LOW" },
    { name: "Stage Front (Zone C)", lat: 28.6132, lng: 77.2088, color: "#ef4444", density: "3.8 ppl/m²", risk: "CRITICAL" },
    { name: "Emergency Exit (Zone D)", lat: 28.6125, lng: 77.2098, color: "#10b981", density: "0.9 ppl/m²", risk: "LOW" }
  ];

  zones.forEach(zone => {
    // Pulsing circle overlay representing crowd density radius
    const circle = L.circle([zone.lat, zone.lng], {
      color: zone.color,
      fillColor: zone.color,
      fillOpacity: 0.25,
      radius: 50
    }).addTo(venueMapInstance);

    // Marker with popup
    const marker = L.circleMarker([zone.lat, zone.lng], {
      radius: 8,
      fillColor: zone.color,
      color: "#ffffff",
      weight: 2,
      opacity: 1,
      fillOpacity: 0.9
    }).addTo(venueMapInstance);

    marker.bindPopup(`
      <div style="font-family: Inter, sans-serif; padding: 4px;">
        <h4 style="margin: 0 0 4px 0; color: #fff;">${zone.name}</h4>
        <p style="margin: 0; font-size: 12px; color: #94a3b8;">Density: <strong>${zone.density}</strong></p>
        <p style="margin: 4px 0 0 0; font-size: 12px; color: ${zone.color};">Status: <strong>${zone.risk}</strong></p>
      </div>
    `);

    mapMarkers.push({ marker, circle, zone });
  });

  // Force Leaflet to recalculate size inside flex/grid container
  setTimeout(() => {
    venueMapInstance.invalidateSize();
  }, 400);
}

/**
 * Initialize Chart.js crowd density trend chart
 */
function initChart() {
  const ctx = document.getElementById("densityChart");
  if (!ctx) return;

  const labels = ["10:00", "10:10", "10:20", "10:30", "10:40", "10:50", "11:00"];
  const densityData = [1.2, 1.5, 2.1, 2.9, 3.4, 3.1, 2.4];
  const thresholdCritical = [3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5];

  densityChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Current Density (ppl/m²)",
          data: densityData,
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.1)",
          fill: true,
          tension: 0.35,
          borderWidth: 2.5,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: "#38bdf8"
        },
        {
          label: "Critical Threshold (3.5 ppl/m²)",
          data: thresholdCritical,
          borderColor: "rgba(239, 68, 68, 0.65)",
          borderDash: [6, 6],
          borderWidth: 1.5,
          fill: false,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
          labels: {
            color: "#94a3b8",
            font: { family: "Inter", size: 12 }
          }
        },
        tooltip: {
          backgroundColor: "#141c2e",
          titleColor: "#f8fafc",
          bodyColor: "#94a3b8",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
          padding: 10
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#64748b", font: { family: "Inter" } }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#64748b", font: { family: "Inter" } },
          min: 0,
          max: 5.0
        }
      }
    }
  });
}

/**
 * Fetch latest crowd telemetry and alerts to update UI cards & tables
 */
async function loadDashboardData() {
  const syncBtn = document.getElementById("refresh-btn");
  if (syncBtn) syncBtn.classList.add("loading");

  try {
    // 1. Fetch Crowd Status
    const crowdRes = await getCrowdStatus();
    if (crowdRes && crowdRes.data) {
      const data = crowdRes.data;

      // Update Cards
      const totalPplElem = document.getElementById("val-total-people");
      const densityElem = document.getElementById("val-current-density");
      const riskElem = document.getElementById("val-risk-level");
      const riskScoreElem = document.getElementById("val-risk-score");

      if (totalPplElem && data.total_people !== undefined) {
        totalPplElem.textContent = Number(data.total_people).toLocaleString();
      }

      if (densityElem && data.current_density !== undefined) {
        densityElem.innerHTML = `${data.current_density} <span style="font-size: 1rem; color: var(--text-secondary);">ppl/m²</span>`;
      }

      if (riskElem && data.risk_level) {
        const badgeClass =
          data.risk_level === "CRITICAL" ? "badge-critical" :
          data.risk_level === "HIGH" ? "badge-high" :
          data.risk_level === "MODERATE" ? "badge-warning" : "badge-low";

        riskElem.innerHTML = `<span class="badge ${badgeClass}" style="font-size: 1.1rem; padding: 0.35rem 0.8rem;">${data.risk_level}</span>`;
      }

      if (riskScoreElem && data.risk_score !== undefined) {
        riskScoreElem.textContent = `${data.risk_score} / 1.0`;
      }

      // Update indicator
      const indicator = document.getElementById("system-status-indicator");
      if (indicator) {
        indicator.textContent = crowdRes.source === "backend" ? "LIVE BACKEND CONNECTED" : "STANDBY TELEMETRY";
      }
    }

    // 2. Fetch Alerts
    const alertsRes = await getAlerts();
    if (alertsRes && alertsRes.data) {
      const alerts = alertsRes.data;
      const activeCount = alerts.filter(a => !a.resolved).length;

      const activeAlertsElem = document.getElementById("val-active-alerts");
      const alertBadge = document.getElementById("alert-counter-badge");
      if (activeAlertsElem) activeAlertsElem.textContent = activeCount;
      if (alertBadge) alertBadge.textContent = `${activeCount} Active`;

      // Render alerts in table
      renderAlertsTable(alerts);
    }
  } catch (error) {
    console.error("[CrowdEye] Error loading dashboard data:", error);
  } finally {
    if (syncBtn) syncBtn.classList.remove("loading");
  }
}

/**
 * Render alerts dynamically in table
 */
function renderAlertsTable(alerts) {
  const tbody = document.getElementById("alerts-table-body");
  if (!tbody) return;

  if (!alerts || alerts.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No safety alerts recorded. All zones normal.</td></tr>`;
    return;
  }

  tbody.innerHTML = alerts.map(alert => {
    const sev = (alert.severity || "MEDIUM").toUpperCase();
    const badgeClass =
      sev === "CRITICAL" ? "badge-critical" :
      sev === "HIGH" || sev === "WARNING" ? "badge-warning" : "badge-low";

    const statusText = alert.resolved
      ? `<span style="color: var(--status-normal);">Resolved</span>`
      : `<span style="color: var(--status-critical);">Unresolved</span>`;

    const timeAgo = formatTimeAgo(alert.created_at);

    return `
      <tr>
        <td><span class="badge ${badgeClass}">${sev}</span></td>
        <td><strong>${escapeHtml(alert.zone || "Zone")}</strong></td>
        <td>${escapeHtml(alert.message || "Hazard detected")}</td>
        <td>${timeAgo}</td>
        <td>${statusText}</td>
        <td>
          <button class="btn btn-secondary" style="padding: 0.25rem 0.65rem; font-size: 0.8rem;" onclick="handleAcknowledgeAlert('${alert.id}')">
            ${alert.resolved ? "View" : "Acknowledge"}
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function handleAcknowledgeAlert(alertId) {
  alert(`Security response logged for alert ID: ${alertId}`);
}

function formatTimeAgo(dateStr) {
  if (!dateStr) return "recently";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins === 1) return "1 min ago";
  if (mins < 60) return `${mins} mins ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs} hrs ago`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
