# UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat-color GitHub-dark UI with a cozy farming aesthetic using tilemap sprites for forest/mine/farm tiles, programmatic shapes for town/market, and programmatic agent rendering.

**Architecture:** `index.html` is restructured (toolbar → canvas+right panel → agent bar → ticker). `canvas.js` gains a tilemap image loader and a two-pass draw loop. `feed.js` becomes a horizontal ticker. `charts.js` gets a color-only reskin. `app.js` gets minor wiring updates. One static mount added to `server/main.py`.

**Tech Stack:** Vanilla JS, HTML Canvas 2D, CSS animations, FastAPI StaticFiles

**Spec:** `docs/superpowers/specs/2026-03-14-ui-redesign-design.md`

> **Note:** This is a pure frontend project. There is no JS test harness. Verification steps use the running server (`uvicorn server.main:app --factory --reload`) and a browser at `http://localhost:8000`.

---

## Chunk 1: Server static mount + HTML shell

### Task 1: Mount `tiny_village/` as a static directory

**Files:**
- Modify: `server/main.py`

`server/main.py` currently mounts `frontend/` at `/`. The tilemap PNG lives at `tiny_village/tiny_village_tilemap.png` relative to the project root. Canvas code will fetch it as `/tiny_village/tiny_village_tilemap.png`, so uvicorn must serve that directory.

- [ ] **Step 1: Add the static mount**

In `server/main.py`, after the existing `frontend` mount block (lines 38–40), add:

```python
    tiny_village = Path("tiny_village")
    if tiny_village.exists():
        app.mount("/tiny_village", StaticFiles(directory=str(tiny_village)), name="tiny_village")
```

The full updated block at the bottom of `create_app()` becomes:

```python
    frontend = Path("frontend")
    if frontend.exists():
        app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")

    tiny_village = Path("tiny_village")
    if tiny_village.exists():
        app.mount("/tiny_village", StaticFiles(directory=str(tiny_village)), name="tiny_village")

    return app
```

- [ ] **Step 2: Verify the mount works**

Start the server:
```bash
uvicorn server.main:app --factory --reload
```

Open `http://localhost:8000/tiny_village/tiny_village_tilemap.png` in a browser.
Expected: the tilemap PNG renders (432×512 pixel-art image).

- [ ] **Step 3: Commit**

```bash
git add server/main.py
git commit -m "feat: serve tiny_village/ sprites as static files"
```

---

### Task 2: Rewrite `index.html` with the new layout and cozy palette

**Files:**
- Modify: `frontend/index.html`

Replace the entire file. The new structure is:
1. Toolbar (top)
2. `#main` row: `#canvas-container` (flex 1) + `#right-panel` (220px)
3. `#agent-info` bar
4. `#ticker-bar` (event ticker at bottom)

DOM IDs that other JS files depend on — must be preserved exactly:
- `#world-canvas` (canvas.js)
- `#btn-pause`, `#btn-step`, `#btn-reset`, `#speed`, `#speed-label`, `#snapshot-select`, `#btn-replay` (app.js)
- `#tick-display` (app.js)
- `#agent-info` (canvas.js)
- `#charts-container` (charts.js)
- `#ticker-bar`, `#ticker-label`, `#ticker-track`, `#ticker-inner` (feed.js — new)

- [ ] **Step 1: Replace `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Isle of Genesis</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: #1a1208;
      color: #f5deb3;
      font-family: 'Courier New', monospace;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* ── Toolbar ── */
    #toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 7px 12px;
      background: #3d2b15;
      border-bottom: 3px solid #7a5c30;
      flex-shrink: 0;
    }
    #toolbar h1 {
      font-size: 0.85rem;
      color: #f5c842;
      margin-right: 4px;
    }
    #toolbar button {
      background: #5a3e20;
      border: 2px solid #8b6040;
      color: #f5deb3;
      padding: 3px 9px;
      cursor: pointer;
      font-family: 'Courier New', monospace;
      font-size: 0.72rem;
      border-radius: 3px;
    }
    #toolbar button:hover { background: #7a5530; border-color: #c8a87a; }
    #tick-display { font-size: 0.75rem; color: #c8a87a; margin-left: auto; }

    label { font-size: 0.72rem; color: #a08060; }
    input[type=range] { width: 70px; accent-color: #f5c842; }
    select {
      background: #5a3e20;
      border: 2px solid #8b6040;
      color: #f5deb3;
      font-size: 0.7rem;
      padding: 2px 4px;
      border-radius: 3px;
      font-family: 'Courier New', monospace;
    }

    /* ── Main row ── */
    #main {
      display: flex;
      flex: 1;
      overflow: hidden;
    }

    #canvas-container {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #1a1208;
      overflow: hidden;
    }
    canvas { display: block; image-rendering: pixelated; }

    /* ── Right panel ── */
    #right-panel {
      width: 220px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      border-left: 3px solid #7a5c30;
      background: #2d1f0e;
    }
    .panel-section {
      flex: 1;
      padding: 9px 10px;
      border-bottom: 2px solid #7a5c30;
      overflow: hidden;
    }
    .panel-section:last-child { border-bottom: none; }
    .panel-title {
      font-size: 0.7rem;
      color: #f5c842;
      margin-bottom: 6px;
    }
    .metric-row {
      display: flex;
      justify-content: space-between;
      font-size: 0.68rem;
      color: #c8a87a;
      margin-bottom: 3px;
    }
    .metric-val { color: #f5deb3; }

    /* ── Agent info bar ── */
    #agent-info {
      padding: 5px 12px;
      background: #3d2b15;
      border-top: 3px solid #7a5c30;
      font-size: 0.68rem;
      color: #c8a87a;
      flex-shrink: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* ── Event ticker ── */
    #ticker-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #1a1208;
      border-top: 2px solid #7a5c30;
      padding: 5px 12px;
      flex-shrink: 0;
      overflow: hidden;
      height: 28px;
    }
    #ticker-label {
      color: #f5c842;
      font-size: 0.65rem;
      white-space: nowrap;
      flex-shrink: 0;
    }
    #ticker-track {
      flex: 1;
      overflow: hidden;
      position: relative;
      height: 18px;
    }
    #ticker-inner {
      display: inline-flex;
      gap: 24px;
      white-space: nowrap;
      position: absolute;
      animation: ticker-scroll 30s linear infinite;
    }
    @keyframes ticker-scroll {
      0%   { transform: translateX(0); }
      100% { transform: translateX(-50%); }
    }
    .ticker-entry { font-size: 0.68rem; }
    .ev-trade    { color: #3fb950; }
    .ev-starved  { color: #f85149; }
    .ev-migrated { color: #d2a8ff; }
    .ev-produced { color: #8b949e; }
  </style>
</head>
<body>
  <div id="toolbar">
    <h1>🏡 Isle of Genesis</h1>
    <button id="btn-pause">Pause</button>
    <button id="btn-step">Step</button>
    <button id="btn-reset">Reset</button>
    <label>Speed <input type="range" id="speed" min="0.5" max="10" step="0.5" value="2"></label>
    <span id="speed-label">2 Hz</span>
    <select id="snapshot-select"><option value="">— replay —</option></select>
    <button id="btn-replay">Replay</button>
    <span id="tick-display">📅 Day 0</span>
  </div>

  <div id="main">
    <div id="canvas-container">
      <canvas id="world-canvas"></canvas>
    </div>
    <div id="right-panel">
      <div class="panel-section">
        <div class="panel-title">📊 Village Stats</div>
        <div id="charts-container"></div>
      </div>
      <div class="panel-section">
        <div class="panel-title">💰 Market Prices</div>
        <div id="prices-container"></div>
      </div>
    </div>
  </div>

  <div id="agent-info">🧑 Click an agent to inspect</div>

  <div id="ticker-bar">
    <span id="ticker-label">📜 Events</span>
    <div id="ticker-track">
      <div id="ticker-inner"></div>
    </div>
  </div>

  <script src="canvas.js"></script>
  <script src="feed.js"></script>
  <script src="charts.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify layout in browser**

With server running, open `http://localhost:8000`.
Expected:
- Dark warm-brown page loads without JS errors (check devtools console)
- Toolbar visible at top with warm brown background
- Empty canvas area taking most of the space
- Right panel visible (220px)
- Agent info bar and ticker strip visible at bottom
- No old GitHub-dark colors (`#0d1117`, `#161b22`) visible

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: reskin index.html with cozy farming layout and palette"
```

---

## Chunk 2: Canvas sprite rendering

### Task 3: Load tilemap and implement two-pass tile rendering

**Files:**
- Modify: `frontend/canvas.js`

The tilemap must be loaded before the first render. If `renderState` is called before `TILEMAP.onload`, fall back to base fill only (no overlay). Once loaded, re-render the current state.

Replace the `TILE_COLORS` block and `renderState` tile drawing loop. Keep all other existing logic (`initCanvas`, `resizeCanvas`, `onCanvasClick`, `showAgentInfo`, `selectedAgentId`) intact.

- [ ] **Step 1: Add tilemap loader and sprite constants at the top of `canvas.js`**

Replace the existing `TILE_COLORS` block (lines 1–8) with:

```js
// canvas.js — grid renderer, sprite tiles, programmatic agents

// Tilemap sprite coordinates (16×16 source tiles from tiny_village_tilemap.png)
const TILE_SPRITES = {
  forest: { sx: 272, sy: 256, sw: 16, sh: 16 },
  mine:   { sx: 160, sy: 32,  sw: 16, sh: 16 },
  farm:   { sx: 176, sy: 352, sw: 16, sh: 16 },
};

// Base fill colors for every tile type (pass 1)
const TILE_BASE = {
  farm:   "#5a7a20",
  forest: "#2a5818",
  mine:   "#3a3028",
  town:   "#4a3820",
  market: "#5a4810",
};

const AGENT_COLORS = {
  farmer:     "#4caf50",
  lumberjack: "#795548",
  miner:      "#78909c",
  trader:     "#ffd600",
};

const AGENT_ICONS = {
  farmer:     "|",
  lumberjack: "x",
  miner:      "-",
  trader:     "$",
};

// Tilemap image — loaded once; renders fall back to base fill until ready
const TILEMAP = new Image();
let tilemapReady = false;
TILEMAP.onload = () => {
  tilemapReady = true;
  if (state) renderState(state);  // re-render now that sprites are available
};
TILEMAP.src = "/tiny_village/tiny_village_tilemap.png";
```

- [ ] **Step 2: Replace the tile-drawing block inside `renderState`**

The existing tile loop (lines 41–47 in the original) draws solid `fillRect`. Replace it with a two-pass loop:

```js
function renderState(s) {
  state = s;
  if (!s || !s.world) return;
  const gridSize = s.world.grid.length;
  cellSize = canvas.width / gridSize;

  // Pass 1 + 2: base fill then sprite or programmatic overlay
  for (let y = 0; y < gridSize; y++) {
    for (let x = 0; x < gridSize; x++) {
      const tile = s.world.grid[y][x];
      const px = x * cellSize, py = y * cellSize;

      // Pass 1 — base fill
      ctx.fillStyle = TILE_BASE[tile.tile_type] || "#3a7020";
      ctx.fillRect(px, py, cellSize, cellSize);

      // Pass 2 — overlay
      const sprite = TILE_SPRITES[tile.tile_type];
      if (sprite && tilemapReady) {
        const margin = 2;
        const dSize = cellSize - margin * 2;
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(TILEMAP, sprite.sx, sprite.sy, sprite.sw, sprite.sh,
                      px + margin, py + margin, dSize, dSize);
      } else if (tile.tile_type === "town") {
        drawTownShape(px, py, cellSize);
      } else if (tile.tile_type === "market") {
        drawMarketShape(px, py, cellSize);
      }
    }
  }

  // draw agents
  for (const agent of s.agents) {
    if (!agent.alive) continue;
    const [ax, ay] = agent.location;
    drawAgent(ax * cellSize, ay * cellSize, cellSize, agent);
  }
}
```

- [ ] **Step 3: Add `drawTownShape` and `drawMarketShape` helpers**

Add these after `renderState`:

```js
function drawTownShape(px, py, cs) {
  // walls
  ctx.fillStyle = "#c8a050";
  ctx.fillRect(px + cs * 0.2, py + cs * 0.4, cs * 0.6, cs * 0.55);
  // roof (triangle)
  ctx.fillStyle = "#8b3a1a";
  ctx.beginPath();
  ctx.moveTo(px + cs * 0.1, py + cs * 0.42);
  ctx.lineTo(px + cs * 0.5, py + cs * 0.1);
  ctx.lineTo(px + cs * 0.9, py + cs * 0.42);
  ctx.closePath();
  ctx.fill();
}

function drawMarketShape(px, py, cs) {
  // awning
  ctx.fillStyle = "#e8c040";
  ctx.fillRect(px + cs * 0.1, py + cs * 0.25, cs * 0.8, cs * 0.2);
  // counter
  ctx.fillStyle = "#c8a050";
  ctx.fillRect(px + cs * 0.15, py + cs * 0.45, cs * 0.7, cs * 0.4);
}
```

- [ ] **Step 4: Verify tile rendering in browser**

Open `http://localhost:8000`. Expected:
- Farm tiles show tilled-soil sprite (brown grid pattern)
- Forest tiles show sapling/tree sprite (green on dark green)
- Mine tiles show gray boulder sprite
- Town tiles show small house shape (walls + triangle roof)
- Market tiles show awning + counter shape
- No JS errors in console

- [ ] **Step 5: Commit**

```bash
git add frontend/canvas.js
git commit -m "feat: two-pass tile rendering with tilemap sprites and programmatic shapes"
```

---

### Task 4: Programmatic agent rendering

**Files:**
- Modify: `frontend/canvas.js`

Replace the old circle+arc agent drawing with the new profession-colored circle + icon approach.

- [ ] **Step 1: Replace the agent drawing block and add `drawAgent` helper**

Remove the existing agent loop (the `for (const agent of s.agents)` block that uses `ctx.arc`). It is now called via `drawAgent()` in `renderState` (added in Task 3). Add the helper:

```js
function drawAgent(px, py, cs, agent) {
  const cx = px + cs / 2;
  const cy = py + cs / 2;
  const r  = Math.max(3, cs * 0.22);

  // selection ring (drawn first, beneath fill)
  if (agent.id === selectedAgentId) {
    ctx.beginPath();
    ctx.arc(cx, cy, r + 2, 0, Math.PI * 2);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // profession-colored circle
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fillStyle = AGENT_COLORS[agent.profession] || "#ffffff";
  ctx.fill();

  // profession icon
  const icon = AGENT_ICONS[agent.profession] || "?";
  const fontSize = Math.max(8, Math.floor(cs * 0.3));
  ctx.fillStyle = "#1a1208";
  ctx.font = `bold ${fontSize}px 'Courier New', monospace`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(icon, cx, cy);
}
```

- [ ] **Step 2: Verify agent rendering in browser**

Open `http://localhost:8000`. Expected:
- Agents appear as colored circles with small icon inside
- Farmer = green circle with `|`, lumberjack = brown with `x`, miner = slate with `-`, trader = yellow with `$`
- Clicking an agent shows a white ring around it and populates the agent info bar
- `showAgentInfo` still works (bottom bar updates with agent stats)

- [ ] **Step 3: Commit**

```bash
git add frontend/canvas.js
git commit -m "feat: programmatic agent rendering with profession icons"
```

---

## Chunk 3: Feed ticker, charts reskin, app wiring

### Task 5: Rewrite `feed.js` as a horizontal ticker

**Files:**
- Modify: `frontend/feed.js`

The ticker works by maintaining a list of event `<span>` elements inside `#ticker-inner`. To achieve a seamless loop, `#ticker-inner` contains the real entries followed by a duplicate copy. The CSS animation translates by `-50%` of the total width, which lands back at the start of the duplicates (identical to the start of the originals).

When entries are added or pruned, the duplicate copy is rebuilt from scratch.

The animation duration is recalculated on every update: `duration = scrollWidth / 60` seconds (60px/s constant speed).

- [ ] **Step 1: Replace the entire contents of `frontend/feed.js`**

```js
// feed.js — horizontal scrolling event ticker
const MAX_TICKER_ENTRIES = 100;

const EVENT_CLASS = {
  trade_completed:   "ev-trade",
  trade_failed:      "ev-trade",
  agent_starved:     "ev-starved",
  agent_migrated_in: "ev-migrated",
  resource_produced: "ev-produced",
};

const EVENT_ICON = {
  trade_completed:   "⚡",
  trade_failed:      "✗",
  agent_starved:     "💀",
  agent_migrated_in: "→",
  resource_produced: "·",
};

// Internal list of entry objects {text, cls} — kept separate from DOM
const tickerEntries = [];

function appendEvents(events, tick) {
  for (const e of events) {
    if (e.event_type === "resource_produced") continue; // too noisy
    const icon = EVENT_ICON[e.event_type] || "?";
    const t = e.tick != null ? e.tick : tick;
    const text = `[${t}] ${icon} ${e.event_type} ${e.actors.join(",")}`;
    const cls = EVENT_CLASS[e.event_type] || "";
    tickerEntries.push({ text, cls });
  }
  // prune oldest
  while (tickerEntries.length > MAX_TICKER_ENTRIES) tickerEntries.shift();
  renderTicker();
}

function renderTicker() {
  const inner = document.getElementById("ticker-inner");
  if (!inner) return;

  // Build original spans
  const originals = tickerEntries.map(e => {
    const span = document.createElement("span");
    span.className = "ticker-entry" + (e.cls ? " " + e.cls : "");
    span.textContent = e.text;
    return span;
  });

  // Build duplicate spans for seamless loop
  const duplicates = originals.map(s => s.cloneNode(true));

  inner.innerHTML = "";
  originals.forEach(s => inner.appendChild(s));
  duplicates.forEach(s => inner.appendChild(s));

  // Recalculate scroll speed (constant px/s = 60)
  // Use half the scrollWidth because content is duplicated
  requestAnimationFrame(() => {
    const halfWidth = inner.scrollWidth / 2;
    const duration = Math.max(5, halfWidth / 60);
    inner.style.animation = "none";
    // Force reflow so animation restarts cleanly
    void inner.offsetWidth;
    inner.style.animation = `ticker-scroll ${duration}s linear infinite`;
  });
}

// Reset ticker on simulation reset
function resetTicker() {
  tickerEntries.length = 0;
  const inner = document.getElementById("ticker-inner");
  if (inner) inner.innerHTML = "";
}
```

- [ ] **Step 2: Update `app.js` reset handler to call `resetTicker()`**

In `frontend/app.js`, the reset button listener currently clears `feed-list`:

```js
// OLD (line 42)
document.getElementById("feed-list").innerHTML = "";
```

Replace that line with:

```js
resetTicker();
```

The full updated listener:

```js
document.getElementById("btn-reset").addEventListener("click", () => {
  send({ type: "reset" });
  metricsHistory.length = 0;
  resetTicker();
});
```

- [ ] **Step 3: Verify ticker in browser**

Open `http://localhost:8000` and let the sim run for ~10 ticks.
Expected:
- Events scroll continuously left in the bottom bar
- Trade events are green, starvation red, migration purple
- No vertical list / old feed panel visible
- Ticker loops seamlessly (no visible jump)

- [ ] **Step 4: Commit**

```bash
git add frontend/feed.js frontend/app.js
git commit -m "feat: replace vertical event feed with horizontal scrolling ticker"
```

---

### Task 6: Reskin `charts.js` to warm palette + split into two containers

**Files:**
- Modify: `frontend/charts.js`

Two changes:
1. Update all hardcoded dark colors (`#0d1117`, `#8b949e`) to warm-palette equivalents.
2. Separate charts into two containers: `#charts-container` (Village Stats) and `#prices-container` (Market Prices). The `index.html` already has both containers.

Village Stats panel layout (per spec):
- 4 text metric rows: Population, Total Wealth, Gini, Food Supply
- 2 sparklines stacked below: population over time (green `#4caf50`) and Gini over time (amber `#f5c842`)

Sparkline width is 190px (right panel is 220px wide with 10px padding each side = 200px inner width, minus borders ≈ 190px usable).

- [ ] **Step 1: Replace the entire contents of `frontend/charts.js`**

```js
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
    const cur  = latest.prices[r];
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
```

- [ ] **Step 2: Verify charts in browser**

Open `http://localhost:8000` and let the sim run for ~20 ticks.
Expected:
- Right panel top section shows Population, Gini, Food Supply sparklines with warm-palette colors
- Right panel bottom section shows Food/Wood/Ore prices with trend arrows (▲ ▼ ─) and a three-line sparkline
- Sparkline backgrounds are dark brown (`#1a1208`), not `#0d1117`
- No JS errors in console

- [ ] **Step 3: Commit**

```bash
git add frontend/charts.js
git commit -m "feat: reskin charts to warm palette, split stats and prices panels"
```

---

### Task 7: Update `app.js` tick display

**Files:**
- Modify: `frontend/app.js`

Two small changes:
1. Change `Tick: N` to `📅 Day N` in the `onMessage` handler
2. Change `Tick: N (replay)` to `📅 Day N (replay)` in the replay handler

- [ ] **Step 1: Update tick display strings in `app.js`**

Find this line in the `onMessage` handler (inside the `if (msg.type === "tick")` branch):
```js
document.getElementById("tick-display").textContent = `Tick: ${result.tick}`;
```
Change to:
```js
document.getElementById("tick-display").textContent = `📅 Day ${result.tick}`;
```

Find this line in the `btn-replay` click handler (after `renderState(latestState)`):
```js
document.getElementById("tick-display").textContent = `Tick: ${data.final_tick} (replay)`;
```
Change to:
```js
document.getElementById("tick-display").textContent = `📅 Day ${data.final_tick} (replay)`;
```

- [ ] **Step 2: Verify in browser**

Open `http://localhost:8000`. Expected: toolbar right side shows `📅 Day 0` and increments each tick.

- [ ] **Step 3: Commit**

```bash
git add frontend/app.js
git commit -m "feat: update tick display label to Day N"
```

---

### Task 8: Final integration check

- [ ] **Step 1: Full end-to-end verification**

Start the server:
```bash
uvicorn server.main:app --factory --reload
```

Open `http://localhost:8000`. Run through this checklist:

| Check | Expected |
|-------|----------|
| Page loads | No console errors |
| Toolbar | Warm brown, buttons styled, `📅 Day N` ticking |
| Tilemap sprites | Farm/forest/mine tiles show pixel-art sprites |
| Town/market tiles | Show programmatic house / awning shapes |
| Agents | Colored circles with `|` / `x` / `-` / `$` icons |
| Click agent | White ring appears; agent info bar populates |
| Right panel top | Population / Gini / Food Supply sparklines |
| Right panel bottom | Price rows with trend arrows + sparkline |
| Bottom ticker | Events scroll left continuously, color-coded |
| Speed slider | Changing speed updates Hz label and sim speed |
| Pause / Step | Pausing stops simulation; Step advances one tick |
| Reset | Clears ticker + charts history; sim restarts |
| Replay | Select a snapshot, click Replay; canvas updates |
| Sprite PNG | `http://localhost:8000/tiny_village/tiny_village_tilemap.png` loads |

- [ ] **Step 2: Commit if any fixes were made during integration**

```bash
git add frontend/index.html frontend/canvas.js frontend/feed.js frontend/charts.js frontend/app.js server/main.py
git commit -m "fix: integration fixes from end-to-end check"
```
