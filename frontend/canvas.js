// canvas.js — grid renderer and agent dots
const TILE_COLORS = {
  farm:    "#1a3a1a",
  forest:  "#0d2b0d",
  mine:    "#2a2a2a",
  town:    "#3a3020",
  market:  "#3a3000",
};
const AGENT_COLORS = {
  farmer:     "#4caf50",
  lumberjack: "#795548",
  miner:      "#78909c",
  trader:     "#ffd600",
};

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

  // draw tiles
  for (let y = 0; y < gridSize; y++) {
    for (let x = 0; x < gridSize; x++) {
      const tile = s.world.grid[y][x];
      ctx.fillStyle = TILE_COLORS[tile.tile_type] || "#111";
      ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
    }
  }

  // draw agents
  const r = Math.max(2, cellSize * 0.25);
  for (const agent of s.agents) {
    if (!agent.alive) continue;
    const [ax, ay] = agent.location;
    const cx = ax * cellSize + cellSize / 2;
    const cy = ay * cellSize + cellSize / 2;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = AGENT_COLORS[agent.profession] || "#fff";
    if (agent.id === selectedAgentId) {
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
    ctx.fill();
  }
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
