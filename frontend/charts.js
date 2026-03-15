// charts.js — SVG sparklines, warm palette
const PRICE_COLORS = { food: "#90c86a", wood: "#c8a87a", ore: "#78909c" };
const SPARKLINE_BG = "#1a1208";
const LABEL_COLOR  = "#a08060";

const metricsHistory = [];
const MAX_HISTORY = 200;

function updateCharts(metrics) {
  metricsHistory.push(metrics);
  if (metricsHistory.length > MAX_HISTORY) metricsHistory.shift();
  renderStatsPanel(metrics);
  renderPricesPanel(metrics);
}

function renderStatsPanel(latest) {
  const container = document.getElementById("charts-container");
  if (!container) return;
  container.innerHTML = "";

  // 4 text metric rows
  const stats = [
    { label: "Population",   value: latest.population,             fmt: v => Math.round(v) },
    { label: "Total Wealth", value: latest.total_wealth,           fmt: v => `$${v.toFixed(0)}` },
    { label: "Gini",         value: latest.gini_coefficient,       fmt: v => v.toFixed(3) },
    { label: "Food/agent",   value: latest.total_food_inventory /
                                    Math.max(1, latest.population), fmt: v => v.toFixed(1) },
  ];
  for (const s of stats) {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;justify-content:space-between;font-size:0.65rem;margin-bottom:2px;";
    row.innerHTML =
      `<span style="color:${LABEL_COLOR}">${s.label}</span>` +
      `<span style="color:#f5deb3">${s.fmt(s.value)}</span>`;
    container.appendChild(row);
  }

  // 2 stacked sparklines: population (green) and Gini (amber)
  container.appendChild(makeSparkline("Population trend", "#4caf50",
    metricsHistory.map(m => m.population)));
  container.appendChild(makeSparkline("Gini trend", "#f5c842",
    metricsHistory.map(m => m.gini_coefficient)));
}

function renderPricesPanel(latest) {
  const container = document.getElementById("prices-container");
  if (!container) return;
  container.innerHTML = "";

  // Current prices with trend arrows
  const resources = ["food", "wood", "ore"];
  const labels    = { food: "🌾 Food", wood: "🪵 Wood", ore: "🪨 Ore" };
  const prev = metricsHistory.length >= 2
    ? metricsHistory[metricsHistory.length - 2].prices
    : null;

  for (const r of resources) {
    const cur  = latest.prices?.[r] ?? 0;
    const row  = document.createElement("div");
    row.style.cssText = "display:flex;justify-content:space-between;font-size:0.65rem;margin-bottom:3px;";
    const trend = prev == null ? "─"
      : cur > prev[r] ? "▲"
      : cur < prev[r] ? "▼"
      : "─";
    row.innerHTML =
      `<span style="color:${PRICE_COLORS[r]}">${labels[r]}</span>` +
      `<span style="color:#f5deb3">$${cur.toFixed(2)} ${trend}</span>`;
    container.appendChild(row);
  }

  // Price sparkline (3 lines)
  const series = resources.map(r => ({
    values: metricsHistory.map(m => m.prices[r]),
    color: PRICE_COLORS[r],
  }));
  container.appendChild(svgSparkline(190, 36, series));
}

function makeSparkline(label, color, values) {
  const wrapper = document.createElement("div");
  wrapper.style.marginBottom = "5px";

  const lbl = document.createElement("div");
  lbl.style.cssText = `font-size:0.65rem;color:${LABEL_COLOR};margin-bottom:1px`;
  const last = values.length ? values[values.length - 1] : 0;
  lbl.textContent = `${label}: ${Number(last).toFixed(2)}`;
  wrapper.appendChild(lbl);
  wrapper.appendChild(svgSparkline(190, 32, [{ values, color }]));
  return wrapper;
}

function svgSparkline(W, H, series) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", W);
  svg.setAttribute("height", H);
  svg.style.background = SPARKLINE_BG;
  svg.style.display = "block";

  const allValues = series.flatMap(s => s.values);
  const min = Math.min(...allValues, 0);
  const max = Math.max(...allValues, 1);
  const range = max - min || 1;

  for (const { values, color } of series) {
    if (values.length < 2) continue;
    const pts = values.map((v, i) => {
      const px = (i / (values.length - 1)) * (W - 2) + 1;
      const py = H - 2 - ((v - min) / range) * (H - 4);
      return `${px.toFixed(1)},${py.toFixed(1)}`;
    });
    const poly = document.createElementNS(ns, "polyline");
    poly.setAttribute("points", pts.join(" "));
    poly.setAttribute("fill", "none");
    poly.setAttribute("stroke", color);
    poly.setAttribute("stroke-width", "1.2");
    svg.appendChild(poly);
  }
  return svg;
}
