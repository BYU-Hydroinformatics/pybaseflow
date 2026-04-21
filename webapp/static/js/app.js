// Baseflow Explorer — map + analyze panel logic

const MAP_CENTER = [39.5, -98.5];
const MAP_ZOOM = 4;
const FIVE_YEARS_MS = 5 * 365.25 * 24 * 3600 * 1000;

const map = L.map("map", { zoomControl: true }).setView(MAP_CENTER, MAP_ZOOM);

const basemaps = {
  "ArcGIS Topo": L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Tiles &copy; Esri", maxZoom: 19 }
  ),
  "ArcGIS Satellite": L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Tiles &copy; Esri", maxZoom: 19 }
  ),
  "ArcGIS Streets": L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Tiles &copy; Esri", maxZoom: 19 }
  ),
  "OpenStreetMap": L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors", maxZoom: 19,
  }),
  "CartoDB Positron": L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    { attribution: "&copy; CARTO", maxZoom: 19 }
  ),
};
basemaps["ArcGIS Topo"].addTo(map);
L.control.layers(basemaps, null, { position: "topright" }).addTo(map);

const markers = L.markerClusterGroup({ maxClusterRadius: 40, chunkedLoading: true });
let selectedLayer = null;
const sitesByNo = new Map();

fetch("/sites.json")
  .then(r => r.json())
  .then(sites => {
    sites.forEach(s => {
      if (s.dec_lat_va == null || s.dec_long_va == null) return;
      sitesByNo.set(s.site_no, s);
      const m = L.circleMarker([s.dec_lat_va, s.dec_long_va], {
        radius: 5, color: "#1e90ff", weight: 1, fillColor: "#1e90ff", fillOpacity: 0.75,
      });
      const name = escapeHtml(s.station_nm || "");
      m.bindTooltip(`<b>${s.site_no}</b><br>${name}`, { sticky: true });
      m.on("click", () => selectSite(s));
      markers.addLayer(m);
    });
    map.addLayer(markers);
  });

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

const panel = document.getElementById("panel");
panel.querySelector(".close-btn").addEventListener("click", closePanel);

function closePanel() {
  panel.classList.add("hidden");
  if (selectedLayer) { map.removeLayer(selectedLayer); selectedLayer = null; }
}

function selectSite(site) {
  if (selectedLayer) map.removeLayer(selectedLayer);
  selectedLayer = L.circleMarker([site.dec_lat_va, site.dec_long_va], {
    radius: 11, color: "#ffffff", weight: 2, fillColor: "#dc1414", fillOpacity: 0.95,
  }).addTo(map);

  document.getElementById("site-title").textContent =
    `${site.site_no} — ${site.station_nm || ""}`;
  const areaStr = site.drain_area_sqmi != null
    ? `${site.drain_area_sqmi.toLocaleString()} mi² (${Math.round(site.drain_area_sqmi * 2.58999).toLocaleString()} km²)`
    : "unknown";
  document.getElementById("site-meta").innerHTML = `Drainage area: ${areaStr}`;

  panel.dataset.siteId = site.site_no;
  const form = document.getElementById("analyze-form");
  if (site.drain_area_sqmi != null) {
    form.area.value = Math.round(site.drain_area_sqmi * 2.58999);
  }

  // Default date range: last 5 water years ending today
  const today = new Date();
  const start = new Date(today.getTime() - FIVE_YEARS_MS);
  form.end.value = today.toISOString().slice(0, 10);
  form.start.value = start.toISOString().slice(0, 10);

  panel.classList.remove("hidden");
  clearAnalysis();
}

function clearAnalysis() {
  document.getElementById("status").textContent = "";
  document.getElementById("summary").innerHTML = "";
  document.getElementById("chart").innerHTML = "";
  document.getElementById("bfi-panel").innerHTML = "";
  document.getElementById("download-csv").classList.add("hidden");
}

const form = document.getElementById("analyze-form");
form.addEventListener("submit", e => {
  e.preventDefault();
  runAnalysis();
});

function runAnalysis() {
  const siteId = panel.dataset.siteId;
  if (!siteId) return;
  const methods = [...form.querySelectorAll("input[name=method]:checked")].map(x => x.value);
  if (methods.length === 0) {
    setStatus("Pick at least one method.", true);
    return;
  }
  const params = new URLSearchParams({
    site_id: siteId,
    start: form.start.value,
    end: form.end.value,
    methods: methods.join(","),
    beta: form.beta.value,
    a: form.a_coef.value,
    bfi_max: form.bfi_max.value,
    area: form.area.value,
  });
  setStatus("Running…");
  fetch(`/analyze?${params}`)
    .then(async r => {
      const body = await r.json();
      if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
      return body;
    })
    .then(renderAnalysis)
    .catch(err => setStatus(`Analysis failed: ${err.message}`, true));
}

function setStatus(msg, isError = false) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.style.color = isError ? "#c62828" : "#555";
}

function renderAnalysis(data) {
  setStatus("");

  document.getElementById("summary").innerHTML = `
    <div class="summary-grid">
      <div><span class="label">Days</span><span class="value">${data.n_days.toLocaleString()}</span></div>
      <div><span class="label">Mean Q</span><span class="value">${data.mean_q.toLocaleString(undefined, {maximumFractionDigits: 1})} ft³/s</span></div>
    </div>
  `;

  const traces = [{
    x: data.dates, y: data.Q,
    name: "Streamflow", type: "scatter",
    line: { color: "#000", width: 1 },
    hovertemplate: "%{x|%Y-%m-%d}<br>%{y:.1f} ft³/s<extra>Streamflow</extra>",
  }];
  for (const [key, values] of Object.entries(data.baseflow)) {
    traces.push({
      x: data.dates, y: values,
      name: window.METHOD_LABELS[key] || key,
      type: "scatter",
      line: { width: 1.5 },
    });
  }
  Plotly.newPlot("chart", traces, {
    yaxis: { type: "log", title: "Discharge (ft³/s, log)" },
    xaxis: { title: "" },
    margin: { l: 55, r: 10, t: 10, b: 40 },
    legend: { orientation: "h", y: -0.22 },
    height: 360,
  }, { responsive: true, displaylogo: false });

  const bfiPanel = document.getElementById("bfi-panel");
  let html = "<h3>Baseflow Index</h3><table><thead><tr><th>Method</th><th>BFI</th></tr></thead><tbody>";
  for (const [key, bfi] of Object.entries(data.bfi)) {
    const lbl = window.METHOD_LABELS[key] || key;
    html += `<tr><td>${lbl}</td><td>${bfi != null ? bfi.toFixed(3) : "—"}</td></tr>`;
  }
  html += "</tbody></table>";
  if (Object.keys(data.failed || {}).length) {
    html += `<div class="failed">Failed: ${Object.keys(data.failed).map(k => window.METHOD_LABELS[k] || k).join(", ")}</div>`;
  }
  bfiPanel.innerHTML = html;

  const csvBtn = document.getElementById("download-csv");
  csvBtn.classList.remove("hidden");
  csvBtn.onclick = () => downloadCsv(data);
}

function downloadCsv(data) {
  const methodKeys = Object.keys(data.baseflow);
  const headers = ["date", "Q_cfs", ...methodKeys.map(k => window.METHOD_LABELS[k] || k)];
  const rows = [headers.join(",")];
  for (let i = 0; i < data.dates.length; i++) {
    const row = [data.dates[i], data.Q[i]];
    for (const k of methodKeys) row.push(data.baseflow[k][i]);
    rows.push(row.join(","));
  }
  const blob = new Blob([rows.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${data.site_id}_baseflow.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}
