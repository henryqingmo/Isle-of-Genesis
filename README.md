# Isle of Genesis

A minimal multi-agent world simulation. 30 agents inhabit a 20×20 grid, produce and trade three resources (food, wood, ore), and survive or die based on hunger. Emergent behaviors — specialization, trade flows, price fluctuations, wealth inequality — arise from simple deterministic heuristics.

## Demo

![Isle of Genesis frontend](docs/screenshot.png)

Grid tiles are color-coded by type; agents are colored dots by profession. The right panel shows live metrics sparklines and a scrolling event feed.

## Running

```bash
pip install -e ".[dev]"
python server/main.py
# open http://localhost:8000
```

## Controls

| Control | Action |
|---------|--------|
| Pause / Resume | Stop or start the tick loop |
| Step | Advance one tick while paused |
| Reset | Re-initialize with the same seed |
| Speed slider | Adjust tick rate (0.5–10 Hz) |
| Replay picker | Load a snapshot and fast-forward |
| Click agent dot | Inspect agent stats |

## Architecture

```
simulation/     Pure Python engine — no framework coupling
  models/       Dataclasses: Agent, Tile, World, Market, SimulationState
  engine.py     Tick loop: actions → settlement → survival → respawn
  heuristics.py Agent decision logic (scoring + survival override)
  market.py     Proportional rationing, damped price updates
  metrics.py    net_worth(), gini(), TickMetrics
  config.py     SimConfig — seed, agent count, grid size, etc.
  events.py     Event dataclass + type constants

persistence/    JSON snapshots + append-only JSONL event log
server/         FastAPI + WebSocket (uvicorn)
  ws.py         SimulationManager — async tick loop, broadcast
  routes.py     REST: /state /metrics /snapshots /events /control /replay
frontend/       Vanilla JS + HTML Canvas (no build step)
  canvas.js     Grid renderer, agent dots, click-to-inspect
  feed.js       Scrolling event feed
  charts.js     SVG sparklines
  app.js        WebSocket client, control bar
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/state` | Full simulation state + status |
| `GET` | `/metrics?from_tick&to_tick` | Metrics history |
| `GET` | `/snapshots` | Available snapshot IDs |
| `GET` | `/events?from_tick&to_tick&event_type` | Filtered event log |
| `POST` | `/control` | `{"command": "pause\|resume\|step\|reset"}` |
| `POST` | `/replay` | `{"snapshot_id": "tick_0050"}` → fast-forward replay |
| `WS` | `/ws` | Live tick stream + bidirectional control |

## Simulation

Each tick, every alive agent submits two actions chosen by scored heuristics:

- **move** — step toward profession tile or market
- **produce** — yield resources scaled by `skill × energy × tile.resource_yield`
- **trade** — post buy/sell orders at global prices (settled proportionally)
- **rest** — restore energy

Hunger increases each tick unless the agent consumes `food_per_tick` from inventory. After `starvation_death_ticks` consecutive ticks at max hunger, the agent dies and respawns later as a migrant settler with minimal wealth.

Prices update each tick using a damped demand/supply ratio:

```
price = price * (1 + damping * (demand/supply − 1))
```

## Tests

```bash
pytest -v   # 75 tests
```
