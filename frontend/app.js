// app.js — WebSocket client, control bar, envelope dispatch
let ws, paused = false, latestState = null;

function connect() {
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${wsProtocol}//${location.host}/ws`);
  ws.onopen = () => { loadSnapshots(); };
  ws.onmessage = (e) => onMessage(JSON.parse(e.data));
  ws.onclose = () => setTimeout(connect, 2000);  // auto-reconnect
}

function onMessage(msg) {
  if (msg.type === "tick") {
    const result = msg.payload;
    // tick payload includes agents + market alongside TickResult fields
    // (injected by SimulationManager._tick_payload in ws.py)
    if (result.agents) {
      latestState = { agents: result.agents, market: result.market, world: result.world };
      renderState(latestState);
    }
    document.getElementById("tick-display").textContent = `📅 Day ${result.tick}`;
    if (result.events) appendEvents(result.events, result.tick);
    if (result.metrics) updateCharts(result.metrics);
  } else if (msg.type === "status") {
    paused = msg.payload.status === "paused";
    document.getElementById("btn-pause").textContent = paused ? "Resume" : "Pause";
  }
}

function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

// Control bar wiring
document.getElementById("btn-pause").addEventListener("click", () => {
  send({ type: paused ? "resume" : "pause" });
});
document.getElementById("btn-step").addEventListener("click", () => {
  send({ type: "step" });
});
document.getElementById("btn-reset").addEventListener("click", () => {
  send({ type: "reset" });
  metricsHistory.length = 0;
  resetTicker();
});

const speedSlider = document.getElementById("speed");
speedSlider.addEventListener("input", () => {
  const hz = parseFloat(speedSlider.value);
  document.getElementById("speed-label").textContent = `${hz} Hz`;
  send({ type: "set_speed", hz });
});

async function loadSnapshots() {
  const resp = await fetch("/snapshots");
  const snaps = await resp.json();
  const sel = document.getElementById("snapshot-select");
  sel.innerHTML = '<option value="">— replay —</option>';
  for (const s of snaps) {
    const opt = document.createElement("option");
    opt.value = s.snapshot_id;
    opt.textContent = `${s.snapshot_id} (tick ${s.tick})`;
    sel.appendChild(opt);
  }
}

document.getElementById("btn-replay").addEventListener("click", async () => {
  const snapshotId = document.getElementById("snapshot-select").value;
  if (!snapshotId) return;
  send({ type: "pause" });
  const resp = await fetch("/replay", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot_id: snapshotId }),
  });
  const data = await resp.json();
  latestState = data.state;
  renderState(latestState);
  if (data.metrics) data.metrics.forEach(m => updateCharts(m));
  if (data.events) appendEvents(data.events, data.final_tick);
  document.getElementById("tick-display").textContent = `📅 Day ${data.final_tick} (replay)`;
});

// init
initCanvas();
connect();
