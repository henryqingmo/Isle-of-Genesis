// charts.js — SVG sparklines for metrics
const CHART_DEFS = [
  { key: "total_food_inventory", label: "Food Supply",     color: "#4caf50" },
  { key: "gini_coefficient",     label: "Gini",            color: "#f85149" },
  { key: "population",           label: "Population",      color: "#d2a8ff" },
  { key: "trade_volume",         label: "Trade Volume",    color: "#ffd600" },
];
const PRICE_COLORS = { food: "#4caf50", wood: "#795548", ore: "#78909c" };

const metricsHistory = [];
const MAX_HISTORY = 200;

function updateCharts(metrics) {
  metricsHistory.push(metrics);
  if (metricsHistory.length > MAX_HISTORY) metricsHistory.shift();

  const container = document.getElementById("charts-container");
  container.innerHTML = "";

  for (const def of CHART_DEFS) {
    container.appendChild(makeSparkline(def.label, def.color,
      metricsHistory.map(m => m[def.key])));
  }

  // price lines (3 on one chart)
  const priceEl = document.createElement("div");
  priceEl.style.marginBottom = "6px";
  const priceLabel = document.createElement("div");
  priceLabel.style.cssText = "font-size:0.65rem;color:#8b949e;margin-bottom:2px";
  priceLabel.textContent = "Prices";
  priceEl.appendChild(priceLabel);
  priceEl.appendChild(makePriceSparkline());
  container.appendChild(priceEl);
}

function makeSparkline(label, color, values) {
  const W = 240, H = 36;
  const wrapper = document.createElement("div");
  wrapper.style.marginBottom = "4px";

  const lbl = document.createElement("div");
  lbl.style.cssText = "font-size:0.65rem;color:#8b949e;margin-bottom:1px";
  const last = values.length ? values[values.length - 1] : 0;
  lbl.textContent = `${label}: ${Number(last).toFixed(2)}`;
  wrapper.appendChild(lbl);

  wrapper.appendChild(svgSparkline(W, H, [{ values, color }]));
  return wrapper;
}

function makePriceSparkline() {
  const W = 240, H = 36;
  const series = ["food", "wood", "ore"].map(r => ({
    values: metricsHistory.map(m => m.prices[r]),
    color: PRICE_COLORS[r],
  }));
  return svgSparkline(W, H, series);
}

function svgSparkline(W, H, series) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.style.background = "#0d1117";

  const allValues = series.flatMap(s => s.values);
  const min = Math.min(...allValues, 0);
  const max = Math.max(...allValues, 1);
  const range = max - min || 1;

  for (const { values, color } of series) {
    if (!values.length) continue;
    const pts = values.map((v, i) => {
      const px = (i / (values.length - 1 || 1)) * (W - 2) + 1;
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
