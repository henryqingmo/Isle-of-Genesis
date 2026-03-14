# Isle of Genesis — Design Specification

**Date:** 2026-03-14
**Status:** Approved

---

## Overview

Isle of Genesis is a minimal multi-agent world simulation. 30 agents inhabit a 20×20 grid, produce and trade three resources (food, wood, ore), vote on tax policy, and die or migrate based on survival conditions. The system is designed to produce emergent behaviors — specialization, trade networks, price fluctuations, wealth inequality — through simple deterministic heuristics, not LLM reasoning.

**Core principles:**
- Hard rules define the world; agents act within constraints
- State is structured and fully reproducible (seeded RNG)
- All events are logged; system supports replay and debugging
- Heuristics first; LLM reasoning is a future extension point

---

## Technology Stack

- **Backend:** Python, FastAPI (uvicorn), asyncio
- **Frontend:** Vanilla JS + HTML Canvas (no build tooling)
- **Communication:** WebSockets (live tick updates) + REST (replay, metrics, control)
- **Persistence:** JSON snapshots + append-only JSONL event log

---

## Project Structure

```
isle-of-genesis/
├── simulation/
│   ├── models/
│   │   ├── world.py        # World, Tile
│   │   ├── agent.py        # Agent, Inventory
│   │   ├── state.py        # SimulationState, TickResult
│   │   └── actions.py      # Action (typed action requests)
│   ├── market.py           # Market dataclass + price update logic
│   ├── government.py       # Government dataclass + voting logic
│   ├── engine.py           # Tick loop, action execution, event dispatch
│   ├── heuristics.py       # Agent decision logic
│   ├── events.py           # EventLog, Event, event_type constants
│   ├── metrics.py          # TickMetrics, Gini, per-tick history
│   └── config.py           # SimConfig (tick rate, agent count, seed, etc.)
├── server/
│   ├── main.py             # FastAPI app, lifespan
│   ├── ws.py               # WebSocket broadcast manager + engine state machine
│   ├── routes.py           # REST endpoints
│   └── schemas.py          # Pydantic API request/response schemas
├── persistence/
│   ├── snapshots.py        # Write/read SimulationState JSON snapshots
│   └── eventlog.py         # Append Event to events.jsonl, read for replay
├── frontend/
│   ├── index.html          # Single page shell
│   ├── app.js              # WebSocket client, UI orchestration
│   ├── canvas.js           # Grid renderer, agent sprites, tile colors
│   ├── feed.js             # Event feed panel
│   └── charts.js           # Metrics time-series (plain SVG sparklines)
├── data/snapshots/         # Periodic JSON world snapshots
├── logs/events.jsonl       # Append-only structured event log
└── pyproject.toml
```

**Module boundary rule:** `simulation/` has zero knowledge of FastAPI or WebSockets. It receives inputs and returns `TickResult`. The server layer owns all network concerns.

---

## Data Models

All models are plain Python dataclasses, serializable via `dataclasses.asdict()`.

### Inventory
```python
@dataclass
class Inventory:
    food: float = 0.0
    wood: float = 0.0
    ore: float = 0.0
```

### World & Tile
```python
@dataclass
class Tile:
    x: int
    y: int
    tile_type: Literal["farm", "forest", "mine", "town", "market"]
    resource_yield: float

@dataclass
class World:
    grid: list[list[Tile]]
    tick: int = 0
```

### Agent
```python
@dataclass
class Agent:
    id: str
    location: tuple[int, int]
    profession: Literal["farmer", "lumberjack", "miner", "trader"]
    wealth: float
    energy: float                  # 0–1
    hunger: float                  # 0–1
    alive: bool
    respawn_tick: int | None
    consecutive_starving: int = 0  # ticks at hunger=1.0; death threshold from SimConfig
    inventory: Inventory = field(default_factory=Inventory)
    skill: float = 0.5
    # Personality (fixed at spawn, 0–1)
    risk_aversion: float = 0.5
    cooperation: float = 0.5
    greed: float = 0.5
    trustfulness: float = 0.5
```

### Market & Government
```python
@dataclass
class Market:
    prices: Inventory
    supply: Inventory
    demand: Inventory
    trade_volume: float
    pending_orders: list = field(default_factory=list)  # cleared each tick

@dataclass
class Government:
    tax_rate: float
    next_vote_tick: int
    vote_interval: int
    treasury: float
    last_vote_result: Literal["low", "medium", "high"] | None = None
```

### State & Results
```python
@dataclass
class SimulationState:
    world: World
    agents: list[Agent]
    market: Market
    government: Government

@dataclass
class Action:
    agent_id: str
    action_type: Literal["move", "produce", "trade", "socialize", "rest"]
    payload: dict = field(default_factory=dict)

@dataclass
class Event:
    event_id: str
    tick: int
    event_type: str   # "trade_completed" | "trade_failed" | "resource_produced" |
                      # "agent_starved" | "agent_migrated_in" | "policy_changed"
    actors: list[str]
    payload: dict
    visibility: Literal["public", "private", "system"] = "public"

@dataclass
class TickMetrics:
    tick: int
    population: int
    total_wealth: float
    gini_coefficient: float
    total_food_inventory: float
    prices: Inventory
    trade_volume: float

@dataclass
class TickResult:
    tick: int
    events: list[Event]
    metrics: TickMetrics
    snapshot_path: str | None = None
```

---

## Configuration

```python
@dataclass
class SimConfig:
    seed: int = 42
    num_agents: int = 30
    grid_size: int = 20
    tick_rate_hz: float = 2.0
    snapshot_interval: int = 50
    vote_interval: int = 50
    tax_options: tuple = (0.05, 0.15, 0.30)
    base_production: dict = field(default_factory=lambda: {
        "farmer":     {"food": 3.0},
        "lumberjack": {"wood": 2.0},
        "miner":      {"ore":  2.0},
        "trader":     {},
    })
    food_per_tick: float = 1.0
    starvation_death_ticks: int = 5
    respawn_delay: tuple[int, int] = (10, 20)
    price_damping: float = 0.1
    price_min: float = 0.1
    price_max: float = 50.0
```

---

## Simulation Engine

### Tick Loop (`simulation/engine.py`)

```python
def tick(self) -> TickResult:
    tick = self.state.world.tick
    events: list[Event] = []

    self._reset_tick_market_state()          # clear supply, demand, pending_orders
    self._prepare_tick_context()             # precompute per-agent observations

    actions = self._collect_actions_for_alive_agents()
    self._resolve_actions(actions, events)

    self._apply_upkeep_and_survival(events)  # food consumption, hunger, death
    self._resolve_market_prices()            # match orders, update prices

    self._collect_taxes(events)              # tax completed trades, redistribute treasury
    self._maybe_vote(events)                 # vote affects next tick's tax_rate
    self._process_respawns(events)           # migrate in new settlers if due

    metrics = self._compute_metrics()
    snapshot_path = self._maybe_snapshot(tick)

    result = TickResult(tick=tick, events=events, metrics=metrics, snapshot_path=snapshot_path)
    self.state.world.tick += 1
    return result
```

### Action Resolution

Each alive agent submits exactly 2 actions per tick. Global phase ordering for MVP:

1. `move` — reposition on grid
2. `produce` — `output = base_rate * skill * energy`; deposited to inventory
3. `trade` — order submission phase (buy/sell posted to `Market.pending_orders`)
4. `socialize` — small energy boost; minor cooperation effect on nearby agents
5. `rest` — restores energy; if chosen as a slot, it is an opportunity cost (no produce/trade)

Trade order matching occurs after all actions resolve (two-phase: collect then match).

### Price Update (damped)

```python
ratio = demand[r] / max(supply[r], 0.001)
prices[r] = prices[r] * (1 + damping * (ratio - 1))
prices[r] = clamp(prices[r], price_min, price_max)
```

### Hunger, Death & Migration

```python
# Per agent per tick
if inventory.food >= food_per_tick:
    inventory.food -= food_per_tick
    hunger = max(0.0, hunger - 0.2)
    consecutive_starving = 0
else:
    hunger = min(1.0, hunger + 0.25)
    if hunger >= 1.0:
        consecutive_starving += 1
    if consecutive_starving >= starvation_death_ticks:
        alive = False
        respawn_tick = tick + rng.randint(*respawn_delay)
        emit("agent_starved")

# Respawn as migrant settler
if not agent.alive and tick >= agent.respawn_tick:
    agent = fresh_settler(spawn_at=random_town_tile())
    emit("agent_migrated_in")
```

Dead agents remain in `state.agents` with `alive=False` until respawned. Fresh settlers receive: minimal starter inventory, low wealth, random profession, random personality.

### Government & Voting

- Every `vote_interval` ticks, alive agents vote on tax rate (`low=0.05`, `medium=0.15`, `high=0.30`)
- Voting heuristic: agents with high wealth prefer low tax; agents with high hunger prefer high tax
- Majority wins; `tax_rate` takes effect the **following tick**
- Tax is collected as a percentage of each completed trade value and held in `Government.treasury`
- Treasury is redistributed evenly to all alive agents at vote time

---

## Agent Decision Heuristics (`simulation/heuristics.py`)

```python
def decide(agent: Agent, state: SimulationState, config: SimConfig) -> list[Action]:
    context = build_context(agent, state)
    candidates = score_actions(agent, context, config)
    return pick_top_two(candidates)   # deterministic given seeded RNG
```

### Survival Override (hard rule, pre-scoring)
```python
if agent.hunger > 0.7 and agent.inventory.food < 1:
    # slot 1: move toward nearest market/town
    # slot 2: buy food (if at market) else rest
    return survival_actions(agent, state)
```

### Action Scoring

| Action | Base score | Key modifiers |
|--------|-----------|---------------|
| `move→profession_tile` | 0.5 | +0.2 if energy > 0.6 |
| `move→market` | 0.4 | +greed if surplus > 2; +0.3 if starving |
| `produce` | 0.6 | × energy × skill; −hunger×0.3 |
| `trade(sell)` | 0.5 | +greed; only if at_market and surplus > 1 |
| `trade(buy food)` | 0.8 | if hunger > 0.5; −risk_aversion×0.2 |
| `socialize` | 0.2 | +cooperation; only if nearby_agents |
| `rest` | 0.3 | +risk_aversion×0.4 if energy < 0.3 |

### Profession Bias

| Profession | Bonus |
|-----------|-------|
| farmer | +0.3 to `produce` on farm tile |
| lumberjack | +0.3 to `produce` on forest tile |
| miner | +0.3 to `produce` on mine tile |
| trader | +0.4 to all `trade` actions; no produce bonus |

**Trader arbitrage:** buy resource with lowest `price/demand` ratio; move to market; sell at current price. Position size scaled by `greed`; capped by `risk_aversion`.

---

## Event Log (`simulation/events.py`, `persistence/eventlog.py`)

```python
# Defined event types
TRADE_COMPLETED   = "trade_completed"
TRADE_FAILED      = "trade_failed"
RESOURCE_PRODUCED = "resource_produced"
AGENT_STARVED     = "agent_starved"
AGENT_MIGRATED_IN = "agent_migrated_in"
POLICY_CHANGED    = "policy_changed"
```

Events are appended to `logs/events.jsonl` (one JSON object per line) and also returned in `TickResult.events` for WebSocket broadcast. The event log is the source of truth for replay.

---

## Metrics (`simulation/metrics.py`)

Tracked per tick and stored in memory as `list[TickMetrics]`. Persisted in snapshots.

**Gini coefficient:**
```python
def gini(wealths: list[float]) -> float:
    n = len(wealths)
    s = sorted(wealths)
    return sum(abs(s[i] - s[j]) for i in range(n) for j in range(n)) / (2 * n * sum(s))
```

---

## Persistence (`persistence/`)

### Snapshots
- `save_snapshot(state, tick, rng_state)` → `data/snapshots/tick_{N:04d}.json`
- `load_snapshot(snapshot_id)` → `(SimulationState, rng_state)`
- Snapshot ID format: `"tick_0050"` — no raw paths exposed via API
- Taken every `snapshot_interval` ticks
- Stores full `SimulationState` + RNG state for deterministic replay

### Event Log
- `append_event(event)` → appends to `logs/events.jsonl`
- `read_events(from_tick, to_tick, event_type)` → `list[Event]`

---

## API Layer

### WebSocket — `/ws`

**Server → Client (typed envelopes):**
```json
{"type": "tick",   "payload": "<TickResult>"}
{"type": "status", "payload": {"status": "running|paused", "tick": 42}}
{"type": "error",  "payload": {"message": "..."}}
```

**Client → Server:**
```json
{"type": "pause"}
{"type": "resume"}
{"type": "step"}
{"type": "set_speed", "hz": 5.0}
{"type": "reset"}
```

**Engine state machine:**
```
RUNNING ──pause/reset──→ PAUSED
PAUSED  ──resume──→ RUNNING
PAUSED  ──step──→ PAUSED    (advances one tick)
any     ──reset──→ RUNNING  (re-initializes from SimConfig)
```

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/state` | Live state, status, config → `StateResponse` |
| `GET` | `/metrics?from_tick&to_tick` | Metrics history → `list[TickMetrics]` |
| `GET` | `/snapshots` | Available snapshots → `list[SnapshotEntry]` |
| `GET` | `/events?from_tick&to_tick&event_type` | Filtered event log |
| `POST` | `/control` | Engine control → `ControlResponse` |
| `POST` | `/replay` | Isolated replay → `ReplayResponse` |

### Pydantic Schemas (`server/schemas.py`)

```python
class StateResponse(BaseModel):
    state: dict
    status: Literal["running", "paused"]
    tick_rate_hz: float
    config: dict

class ControlCommand(BaseModel):
    command: Literal["pause", "resume", "step", "reset"]

class ControlResponse(BaseModel):
    ok: bool
    status: Literal["running", "paused"]
    tick: int

class SnapshotEntry(BaseModel):
    snapshot_id: str    # e.g. "tick_0050"
    tick: int
    timestamp: float

class ReplayRequest(BaseModel):
    snapshot_id: str
    to_tick: int | None = None

class ReplayResponse(BaseModel):
    final_tick: int
    state: dict
    metrics: list[dict] | None = None
    events: list[dict] | None = None
```

**Replay determinism:** Server loads snapshot (including RNG state), runs engine in fast-forward with no sleep, returns `ReplayResponse`. No broadcast to live WebSocket clients. Live sim remains paused during replay.

---

## Frontend Visualization

**Layout:** Map-dominant (Option A). Grid takes left 70% of viewport; right column has metrics panel (top) and event feed (bottom).

### Files

| File | Responsibility |
|------|---------------|
| `index.html` | Shell, layout, control bar (pause/resume/step/speed slider/replay picker) |
| `app.js` | WebSocket client, typed envelope dispatch, control message sending |
| `canvas.js` | 20×20 grid on `<canvas>`; tile colors by type; agents as profession-colored dots; click to inspect |
| `feed.js` | Scrolling event feed; color-coded by event type; max 100 DOM entries |
| `charts.js` | Plain SVG sparklines for food supply, prices (3 lines), Gini, population |

### Tile Color Scheme
| Tile type | Color |
|-----------|-------|
| farm | green |
| forest | dark green |
| mine | grey |
| town | tan |
| market | gold |

### Agent Dot Colors (by profession)
| Profession | Color |
|-----------|-------|
| farmer | light green |
| lumberjack | brown |
| miner | slate |
| trader | yellow |

Dead agents are not rendered. Migrant arrival is shown as a brief spawn animation.

---

## Replay & Debugging

- **Timeline scrubbing:** UI provides a slider over available snapshot IDs. Selecting one calls `POST /replay` and displays the returned state statically.
- **Step mode:** Pause sim, then click Step to advance one tick at a time. Useful for debugging heuristic decisions.
- **Event filter:** Event feed supports filtering by type via dropdown.
- **Metrics export:** `GET /metrics` returns full history; can be saved as JSON for external analysis.

---

## Emergent Behaviors Expected

| Behavior | Mechanism |
|---------|-----------|
| Specialization | Profession bias + tile proximity → agents cluster on matching tiles |
| Trade networks | Traders arbitrage price differentials → move between producers and market |
| Price fluctuations | Supply/demand imbalance + starvation events spike food prices |
| Wealth inequality | Traders accumulate; new migrants start poor → Gini rises over time |
| Tax cycles | High inequality → majority votes high tax → redistribution → inequality drops |

---

## Implementation Order

1. Data models (`simulation/models/`, `market.py`, `government.py`, `config.py`)
2. Simulation engine skeleton (`engine.py`, `events.py`, `metrics.py`)
3. Agent heuristics (`heuristics.py`)
4. Persistence layer (`persistence/`)
5. FastAPI server + WebSocket (`server/`)
6. Frontend canvas + event feed + charts (`frontend/`)
