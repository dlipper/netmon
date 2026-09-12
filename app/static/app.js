let pingChart = null;
let speedChart = null;
let currentPingHours = 24;
let isSpeedtestPolling = false;

document.addEventListener("DOMContentLoaded", () => {
  initPingChart();
  initSpeedChart();
  refreshAllData();

  // Auto-refresh ping timeline and status every 30 seconds
  setInterval(() => {
    refreshStatus();
    loadPingHistory(currentPingHours);
  }, 30000);
});

function refreshAllData() {
  refreshStatus();
  loadPingHistory(currentPingHours);
  loadSpeedtestHistory();
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();

    // Status pill
    const pill = document.getElementById("statusPill");
    const text = document.getElementById("statusText");
    if (data.is_online) {
      pill.classList.remove("offline");
      text.textContent = "Internet Online";
    } else {
      pill.classList.add("offline");
      text.textContent = "Internet Offline";
    }

    // Ping metric
    if (data.latest_ping && data.latest_ping.latency_ms !== null) {
      document.getElementById("metricPing").textContent = data.latest_ping.latency_ms.toFixed(1);
      document.getElementById("metricTarget").textContent = `Target: ${data.latest_ping.target}`;
    } else {
      document.getElementById("metricPing").textContent = "--";
    }

    // Uptime metric
    if (data.stats_24h) {
      document.getElementById("metricUptime").textContent = data.stats_24h.uptime_pct.toFixed(1);
      document.getElementById("metricUptimeSamples").textContent = `${data.stats_24h.online_samples} / ${data.stats_24h.total_samples} samples`;
    }

    // Latest Speedtest metrics
    if (data.latest_speedtest) {
      document.getElementById("metricDownload").textContent = data.latest_speedtest.download_mbps.toFixed(1);
      document.getElementById("metricUpload").textContent = data.latest_speedtest.upload_mbps.toFixed(1);
      document.getElementById("metricSpeedDate").textContent = formatDate(data.latest_speedtest.timestamp);
      document.getElementById("metricServer").textContent = data.latest_speedtest.server_name || "Server";
    }

    // Check if test is currently running
    if (data.speedtest_running && !isSpeedtestPolling) {
      startSpeedtestPolling();
    }
  } catch (err) {
    console.error("Failed to load status:", err);
  }
}

function initPingChart() {
  const ctx = document.getElementById("pingChart").getContext("2d");
  pingChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Ping Latency (ms)",
          data: [],
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.08)",
          fill: true,
          tension: 0.2,
          pointRadius: 2,
          pointHoverRadius: 5,
          pointBackgroundColor: (ctx) => {
            const raw = ctx.raw;
            return raw && raw.is_online === 0 ? "#ef4444" : "#22c55e";
          },
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: "index"
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1a2332",
          titleColor: "#94a3b8",
          bodyColor: "#f1f5f9",
          borderColor: "#2a374a",
          borderWidth: 1,
          callbacks: {
            label: (item) => {
              const pt = item.raw;
              if (!pt || pt.is_online === 0) {
                return "Status: OFFLINE (Packet Loss)";
              }
              return `Latency: ${pt.y} ms`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#64748b", maxRotation: 0, autoSkip: true, maxTicksLimit: 12 }
        },
        y: {
          beginAtZero: true,
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#64748b",
            callback: (val) => `${val} ms`
          }
        }
      }
    }
  });
}

function initSpeedChart() {
  const ctx = document.getElementById("speedChart").getContext("2d");
  speedChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "Download (Mbps)",
          data: [],
          backgroundColor: "rgba(6, 182, 212, 0.8)",
          borderColor: "#06b6d4",
          borderWidth: 1,
          borderRadius: 6
        },
        {
          label: "Upload (Mbps)",
          data: [],
          backgroundColor: "rgba(168, 85, 247, 0.8)",
          borderColor: "#a855f7",
          borderWidth: 1,
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: "index"
      },
      plugins: {
        legend: {
          labels: { color: "#94a3b8" }
        },
        tooltip: {
          backgroundColor: "#1a2332",
          titleColor: "#94a3b8",
          bodyColor: "#f1f5f9",
          borderColor: "#2a374a",
          borderWidth: 1,
          callbacks: {
            label: (item) => `${item.dataset.label}: ${item.raw} Mbps`
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#64748b", maxRotation: 45 }
        },
        y: {
          beginAtZero: true,
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#64748b",
            callback: (val) => `${val} Mbps`
          }
        }
      }
    }
  });
}

async function loadPingHistory(hours = 24) {
  try {
    const res = await fetch(`/api/ping-history?hours=${hours}`);
    if (!res.ok) return;
    const data = await res.json();

    const points = data.points || [];
    const labels = [];
    const chartData = [];

    points.forEach((p) => {
      labels.push(formatTime(p.timestamp));
      chartData.push({
        x: formatTime(p.timestamp),
        y: p.is_online ? p.latency_ms : 0,
        is_online: p.is_online
      });
    });

    pingChart.data.labels = labels;
    pingChart.data.datasets[0].data = chartData;
    pingChart.update();
  } catch (err) {
    console.error("Failed to load ping history:", err);
  }
}

async function loadSpeedtestHistory() {
  try {
    const res = await fetch("/api/speedtests?limit=25");
    if (!res.ok) return;
    const data = await res.json();
    const tests = data.speedtests || [];

    // Populate chart (oldest to newest on chart)
    const reversed = [...tests].reverse();
    speedChart.data.labels = reversed.map((t) => formatShortDate(t.timestamp));
    speedChart.data.datasets[0].data = reversed.map((t) => t.download_mbps);
    speedChart.data.datasets[1].data = reversed.map((t) => t.upload_mbps);
    speedChart.update();

    // Populate table (newest first)
    const tbody = document.getElementById("historyTableBody");
    if (tests.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No speedtests performed yet. Click "Check the speed" to run one.</td></tr>`;
      return;
    }

    tbody.innerHTML = tests.map((t) => {
      const serverLocation = [t.server_name, t.server_location].filter(Boolean).join(", ");
      const server = escapeHtml(serverLocation || "--");
      const isp = escapeHtml(t.isp || "--");
      const safeUrl = safeResultUrl(t.result_url);
      const urlHtml = safeUrl
        ? `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); text-decoration:none;">View ↗</a>`
        : "--";
      const pingText = t.ping_ms ? Number(t.ping_ms).toFixed(1) + " ms" : "--";
      const jitterText = t.jitter_ms ? ` <span style="color:#64748b; font-size:0.8rem">(${Number(t.jitter_ms).toFixed(1)}j)</span>` : "";

      return `
      <tr>
        <td><strong>${escapeHtml(formatDate(t.timestamp))}</strong></td>
        <td><span class="speed-badge-down">↓ ${Number(t.download_mbps).toFixed(1)} Mbps</span></td>
        <td><span class="speed-badge-up">↑ ${Number(t.upload_mbps).toFixed(1)} Mbps</span></td>
        <td>${pingText}${jitterText}</td>
        <td>${server}</td>
        <td>${isp}</td>
        <td>${urlHtml}</td>
      </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load speedtests:", err);
  }
}

function setPingRange(hours, buttonEl) {
  currentPingHours = hours;
  document.querySelectorAll(".range-btn").forEach((btn) => btn.classList.remove("active"));
  buttonEl.classList.add("active");
  loadPingHistory(hours);
}

async function triggerSpeedtest() {
  const btn = document.getElementById("btnSpeedtest");
  if (btn.disabled) return;

  try {
    const res = await fetch("/api/speedtest/run", { method: "POST" });
    if (res.status === 409) {
      alert("A speedtest is already in progress!");
      startSpeedtestPolling();
      return;
    }
    if (!res.ok) {
      alert("Failed to start speedtest.");
      return;
    }
    startSpeedtestPolling();
  } catch (err) {
    alert("Network error starting speedtest.");
  }
}

function startSpeedtestPolling() {
  isSpeedtestPolling = true;
  const btn = document.getElementById("btnSpeedtest");
  const banner = document.getElementById("testBanner");
  const btnIcon = document.getElementById("btnIcon");
  const btnText = document.getElementById("btnText");

  btn.disabled = true;
  banner.style.display = "flex";
  btnIcon.textContent = "⏳";
  btnText.textContent = "Testing speed...";

  const poller = setInterval(async () => {
    try {
      const res = await fetch("/api/speedtest/status");
      const data = await res.json();
      if (!data.running) {
        clearInterval(poller);
        isSpeedtestPolling = false;
        btn.disabled = false;
        banner.style.display = "none";
        btnIcon.textContent = "⚡";
        btnText.textContent = "Check the speed";
        refreshAllData();
      }
    } catch (e) {
      console.error("Polling error:", e);
    }
  }, 2000);
}

function formatTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr.endsWith("Z") ? isoStr : isoStr + "Z");
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatShortDate(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr.endsWith("Z") ? isoStr : isoStr + "Z");
  return `${d.getMonth() + 1}/${d.getDate()} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function formatDate(isoStr) {
  if (!isoStr) return "--";
  const d = new Date(isoStr.endsWith("Z") ? isoStr : isoStr + "Z");
  return d.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function safeResultUrl(url) {
  if (!url || typeof url !== "string") return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "https:") {
      return parsed.href;
    }
  } catch (e) {
    return null;
  }
  return null;
}

