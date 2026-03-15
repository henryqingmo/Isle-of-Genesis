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

let canvas, ctx, cellSize, state = null, selectedAgentId = null;

function initCanvas() {
  canvas = document.getElementById("world-canvas");
  ctx = canvas.getContext("2d");
  canvas.addEventListener("click", onCanvasClick);
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();
}

function resizeCanvas() {
  const container = document.getElementById("canvas-container");
  const size = Math.min(container.clientWidth, container.clientHeight) - 20;
  canvas.width = size;
  canvas.height = size;
  if (state) renderState(state);
}

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

function onCanvasClick(e) {
  if (!state) return;
  const rect = canvas.getBoundingClientRect();
  const px = e.clientX - rect.left;
  const py = e.clientY - rect.top;
  const gx = Math.floor(px / cellSize);
  const gy = Math.floor(py / cellSize);

  let closest = null, closestDist = Infinity;
  for (const agent of state.agents) {
    if (!agent.alive) continue;
    const [ax, ay] = agent.location;
    const d = Math.abs(ax - gx) + Math.abs(ay - gy);
    if (d < closestDist) { closestDist = d; closest = agent; }
  }
  if (closest && closestDist <= 1) {
    selectedAgentId = closest.id;
    showAgentInfo(closest);
    renderState(state);
  }
}

function showAgentInfo(agent) {
  const el = document.getElementById("agent-info");
  const inv = agent.inventory;
  el.textContent = `${agent.id} | ${agent.profession} | wealth: $${agent.wealth.toFixed(2)} | `
    + `food: ${inv.food.toFixed(1)} wood: ${inv.wood.toFixed(1)} ore: ${inv.ore.toFixed(1)} | `
    + `hunger: ${(agent.hunger * 100).toFixed(0)}% energy: ${(agent.energy * 100).toFixed(0)}%`;
}
