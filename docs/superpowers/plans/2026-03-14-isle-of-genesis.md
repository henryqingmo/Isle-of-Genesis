# Isle of Genesis Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal multi-agent world simulation with 30 agents, 3 resources, a simple market economy, and a browser-based 2D visualization.

**Architecture:** Python simulation engine (pure functions, no framework coupling) runs as an asyncio background task inside a FastAPI server. Each tick produces a `TickResult` broadcast over WebSocket to a vanilla JS browser frontend. Replay is supported via periodic JSON snapshots + RNG state.

**Tech Stack:** Python 3.12+, FastAPI, uvicorn, asyncio, websockets; Vanilla JS + HTML Canvas (no build tooling); pytest for tests.

---

## File Map

```
isle-of-genesis/
├── simulation/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── world.py        # Tile, World
│   │   ├── agent.py        # Inventory, Agent
│   │   ├── state.py        # SimulationState, TickResult
│   │   └── actions.py      # Action
│   ├── config.py           # SimConfig
│   ├── events.py           # Event, event type constants
│   ├── market.py           # Market, settlement logic
│   ├── metrics.py          # TickMetrics, net_worth(), gini()
│   ├── engine.py           # SimulationEngine, tick loop
│   └── heuristics.py       # decide(), score_actions(), build_context()
├── persistence/
│   ├── __init__.py
│   ├── snapshots.py        # save_snapshot(), load_snapshot()
│   └── eventlog.py         # append_event(), read_events()
├── server/
│   ├── __init__.py
│   ├── schemas.py          # Pydantic request/response models
│   ├── ws.py               # WebSocket manager + engine state machine
│   ├── routes.py           # REST endpoints
│   └── main.py             # FastAPI app, lifespan, router mounting
├── frontend/
│   ├── index.html          # Shell, layout, control bar
│   ├── app.js              # WebSocket client, envelope dispatch
│   ├── canvas.js           # Grid + agent renderer
│   ├── feed.js             # Event feed panel
│   └── charts.js           # SVG sparklines
├── tests/
│   ├── simulation/
│   │   ├── models/
│   │   │   ├── test_world.py
│   │   │   ├── test_agent.py
│   │   │   └── test_state.py
│   │   ├── test_market.py
│   │   ├── test_metrics.py
│   │   ├── test_engine.py
│   │   └── test_heuristics.py
│   ├── persistence/
│   │   ├── test_snapshots.py
│   │   └── test_eventlog.py
│   └── server/
│       └── test_routes.py
├── data/
│   └── snapshots/
├── logs/
├── .gitignore
└── pyproject.toml
```

---

## Chunk 1: Project Setup & Data Models

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `simulation/__init__.py`, `simulation/models/__init__.py`
- Create: `persistence/__init__.py`, `server/__init__.py`
- Create: `data/snapshots/.gitkeep`, `logs/.gitkeep`
- Create: `tests/__init__.py`, `tests/simulation/__init__.py`, `tests/simulation/models/__init__.py`, `tests/persistence/__init__.py`, `tests/server/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "isle-of-genesis"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
data/snapshots/*.json
logs/events.jsonl
.superpowers/
```

- [ ] **Step 3: Create directory structure and empty `__init__.py` files**

```bash
mkdir -p simulation/models persistence server frontend tests/simulation/models tests/persistence tests/server data/snapshots logs
touch simulation/__init__.py simulation/models/__init__.py
touch persistence/__init__.py server/__init__.py
touch tests/__init__.py tests/simulation/__init__.py tests/simulation/models/__init__.py
touch tests/persistence/__init__.py tests/server/__init__.py
touch data/snapshots/.gitkeep logs/.gitkeep
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -e ".[dev]"
```

Expected: no errors, `fastapi`, `uvicorn`, `pytest` available.

- [ ] **Step 5: Verify pytest runs on empty suite**

```bash
pytest
```

Expected: `no tests ran` or `0 passed`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore simulation/ persistence/ server/ frontend/ tests/ data/ logs/
git commit -m "chore: project scaffold, pyproject.toml, directory structure"
```

---

### Task 2: `Inventory` and `Agent` models

**Files:**
- Create: `simulation/models/agent.py`
- Create: `tests/simulation/models/test_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/simulation/models/test_agent.py
from simulation.models.agent import Inventory, Agent

def test_inventory_defaults_to_zero():
    inv = Inventory()
    assert inv.food == 0.0
    assert inv.wood == 0.0
    assert inv.ore == 0.0

def test_agent_has_required_fields():
    agent = Agent(
        id="a01",
        location=(0, 0),
        profession="farmer",
        wealth=10.0,
        energy=1.0,
        hunger=0.0,
        alive=True,
        respawn_tick=None,
    )
    assert agent.id == "a01"
    assert agent.inventory.food == 0.0
    assert agent.consecutive_starving == 0
    assert agent.skill == 0.5
    assert agent.risk_aversion == 0.5

def test_agent_profession_values():
    for prof in ("farmer", "lumberjack", "miner", "trader"):
        a = Agent(id="x", location=(0,0), profession=prof,
                  wealth=0, energy=1, hunger=0, alive=True, respawn_tick=None)
        assert a.profession == prof
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/models/test_agent.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 3: Implement `simulation/models/agent.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Inventory:
    food: float = 0.0
    wood: float = 0.0
    ore: float = 0.0


@dataclass
class Agent:
    id: str
    location: tuple[int, int]
    profession: Literal["farmer", "lumberjack", "miner", "trader"]
    wealth: float          # cash only; net_worth is derived when needed
    energy: float          # 0–1
    hunger: float          # 0–1
    alive: bool
    respawn_tick: int | None
    consecutive_starving: int = 0
    inventory: Inventory = field(default_factory=Inventory)
    skill: float = 0.5
    risk_aversion: float = 0.5  # only personality scalar in v1
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/simulation/models/test_agent.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add simulation/models/agent.py tests/simulation/models/test_agent.py
git commit -m "feat: Inventory and Agent dataclasses"
```

---

### Task 3: `Tile` and `World` models

**Files:**
- Create: `simulation/models/world.py`
- Create: `tests/simulation/models/test_world.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/simulation/models/test_world.py
from simulation.models.world import Tile, World

def test_tile_has_required_fields():
    t = Tile(x=0, y=0, tile_type="farm", resource_yield=1.0)
    assert t.tile_type == "farm"
    assert t.resource_yield == 1.0

def test_world_starts_at_tick_zero():
    grid = [[Tile(x=x, y=y, tile_type="town", resource_yield=0.0)
             for x in range(3)] for y in range(3)]
    world = World(grid=grid)
    assert world.tick == 0

def test_world_grid_dimensions():
    grid = [[Tile(x=x, y=y, tile_type="farm", resource_yield=1.0)
             for x in range(5)] for y in range(5)]
    world = World(grid=grid)
    assert len(world.grid) == 5
    assert len(world.grid[0]) == 5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/models/test_world.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `simulation/models/world.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


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

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/simulation/models/test_world.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add simulation/models/world.py tests/simulation/models/test_world.py
git commit -m "feat: Tile and World dataclasses"
```

---

### Task 4: `Market` model

**Files:**
- Create: `simulation/market.py`
- Create: `tests/simulation/test_market.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/simulation/test_market.py
from simulation.market import Market
from simulation.models.agent import Inventory

def test_market_default_prices():
    m = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(),
        demand=Inventory(),
        trade_volume=0.0,
    )
    assert m.prices.food == 1.0
    assert m.trade_volume == 0.0

def test_market_supply_demand_start_zero():
    m = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(),
        demand=Inventory(),
        trade_volume=0.0,
    )
    assert m.supply.food == 0.0
    assert m.demand.wood == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/test_market.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `simulation/market.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from simulation.models.agent import Inventory


@dataclass
class Market:
    prices: Inventory
    supply: Inventory
    demand: Inventory
    trade_volume: float
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/simulation/test_market.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add simulation/market.py tests/simulation/test_market.py
git commit -m "feat: Market dataclass"
```

---

### Task 5: `SimConfig`

**Files:**
- Create: `simulation/config.py`

No dedicated test file — `SimConfig` is pure data with defaults; it will be exercised by engine tests. Verify it imports and defaults are correct inline.

- [ ] **Step 1: Implement `simulation/config.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SimConfig:
    seed: int = 42
    num_agents: int = 30
    grid_size: int = 20
    tick_rate_hz: float = 2.0
    snapshot_interval: int = 50
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

- [ ] **Step 2: Verify import**

```bash
python -c "from simulation.config import SimConfig; c = SimConfig(); print(c.seed, c.num_agents)"
```

Expected: `42 30`.

- [ ] **Step 3: Commit**

```bash
git add simulation/config.py
git commit -m "feat: SimConfig dataclass"
```

---

### Task 6: `Event` model and constants

**Files:**
- Create: `simulation/events.py`

- [ ] **Step 1: Implement `simulation/events.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import uuid

# Event type constants
TRADE_COMPLETED   = "trade_completed"
TRADE_FAILED      = "trade_failed"
RESOURCE_PRODUCED = "resource_produced"
AGENT_STARVED     = "agent_starved"
AGENT_MIGRATED_IN = "agent_migrated_in"


@dataclass
class Event:
    tick: int
    event_type: str
    actors: list[str]
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    visibility: Literal["public", "private", "system"] = "public"
```

- [ ] **Step 2: Verify constants and instantiation**

```bash
python -c "
from simulation.events import Event, TRADE_COMPLETED
e = Event(tick=1, event_type=TRADE_COMPLETED, actors=['a01'], payload={'qty': 2})
print(e.event_type, e.event_id[:8])
"
```

Expected: `trade_completed` followed by a UUID prefix.

- [ ] **Step 3: Commit**

```bash
git add simulation/events.py
git commit -m "feat: Event dataclass and event type constants"
```

---

### Task 7: `SimulationState`, `TickResult`, `Action`

**Files:**
- Create: `simulation/models/state.py`
- Create: `simulation/models/actions.py`
- Create: `tests/simulation/models/test_state.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/simulation/models/test_state.py
from unittest.mock import MagicMock
from simulation.models.world import Tile, World
from simulation.models.agent import Agent, Inventory
from simulation.market import Market
from simulation.models.state import SimulationState, TickResult
from simulation.models.actions import Action

def make_world():
    grid = [[Tile(x=x, y=y, tile_type="town", resource_yield=0.0)
             for x in range(3)] for y in range(3)]
    return World(grid=grid)

def make_market():
    return Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )

def test_simulation_state_holds_components():
    state = SimulationState(
        world=make_world(),
        agents=[],
        market=make_market(),
    )
    assert state.world.tick == 0
    assert state.agents == []

def test_action_has_empty_payload_by_default():
    a = Action(agent_id="a01", action_type="rest")
    assert a.payload == {}

def test_tick_result_snapshot_path_defaults_none():
    # TickMetrics not yet defined in Chunk 1 — use a stub
    metrics_stub = MagicMock()
    result = TickResult(tick=0, events=[], metrics=metrics_stub)
    assert result.snapshot_path is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/models/test_state.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `simulation/models/actions.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Action:
    agent_id: str
    action_type: Literal["move", "produce", "trade", "rest"]
    payload: dict = field(default_factory=dict)
```

- [ ] **Step 4: Implement `simulation/models/state.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from simulation.models.world import World
from simulation.models.agent import Agent
from simulation.market import Market
from simulation.events import Event

if TYPE_CHECKING:
    # TickMetrics is defined in simulation/metrics.py (Chunk 2).
    # TYPE_CHECKING guard avoids a circular import at runtime;
    # `from __future__ import annotations` makes the annotation a string.
    from simulation.metrics import TickMetrics


@dataclass
class SimulationState:
    world: World
    agents: list[Agent]
    market: Market


@dataclass
class TickResult:
    tick: int
    events: list[Event]
    metrics: TickMetrics   # resolved at runtime once metrics.py exists
    snapshot_path: str | None = None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/simulation/models/test_state.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Run full test suite**

```bash
pytest -v
```

Expected: all tests pass, no errors.

- [ ] **Step 7: Commit**

```bash
git add simulation/models/actions.py simulation/models/state.py tests/simulation/models/test_state.py
git commit -m "feat: Action, SimulationState, TickResult dataclasses"
```

---

## Chunk 2: Metrics, Engine Core & Market Settlement

### Task 8: `metrics.py` — `net_worth`, `gini`, `TickMetrics`

**Files:**
- Create: `simulation/metrics.py`
- Create: `tests/simulation/test_metrics.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/simulation/test_metrics.py
from simulation.metrics import net_worth, gini, TickMetrics
from simulation.models.agent import Agent, Inventory

def make_agent(wealth, food=0.0, wood=0.0, ore=0.0):
    return Agent(
        id="x", location=(0,0), profession="farmer",
        wealth=wealth, energy=1.0, hunger=0.0,
        alive=True, respawn_tick=None,
        inventory=Inventory(food=food, wood=wood, ore=ore),
    )

def test_net_worth_cash_only():
    a = make_agent(wealth=10.0)
    prices = Inventory(food=1.0, wood=1.0, ore=1.0)
    assert net_worth(a, prices) == 10.0

def test_net_worth_includes_inventory():
    a = make_agent(wealth=5.0, food=3.0, wood=2.0, ore=1.0)
    prices = Inventory(food=2.0, wood=1.0, ore=4.0)
    # 5 + 3*2 + 2*1 + 1*4 = 5 + 6 + 2 + 4 = 17
    assert net_worth(a, prices) == 17.0

def test_gini_equal_wealth_is_zero():
    assert gini([10.0, 10.0, 10.0]) == 0.0

def test_gini_max_inequality():
    # one agent has everything, rest have nothing
    result = gini([0.0, 0.0, 0.0, 100.0])
    assert result > 0.7   # close to 0.75

def test_gini_zero_total_wealth():
    assert gini([0.0, 0.0, 0.0]) == 0.0

def test_gini_two_agents():
    # one has 0, one has 100 → gini = 0.5
    assert abs(gini([0.0, 100.0]) - 0.5) < 1e-9
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/test_metrics.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `simulation/metrics.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from simulation.models.agent import Agent, Inventory


def net_worth(agent: Agent, prices: Inventory) -> float:
    return (agent.wealth
            + agent.inventory.food * prices.food
            + agent.inventory.wood * prices.wood
            + agent.inventory.ore  * prices.ore)


def gini(wealths: list[float]) -> float:
    n = len(wealths)
    if n == 0:
        return 0.0
    s = sorted(wealths)
    total = sum(s)
    if total == 0:
        return 0.0
    return sum(abs(s[i] - s[j]) for i in range(n) for j in range(n)) / (2 * n * total)


@dataclass
class TickMetrics:
    tick: int
    population: int
    total_wealth: float          # sum of net_worth across all alive agents
    gini_coefficient: float
    total_food_inventory: float
    prices: Inventory
    trade_volume: float
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/simulation/test_metrics.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add simulation/metrics.py tests/simulation/test_metrics.py
git commit -m "feat: net_worth(), gini(), TickMetrics"
```

---

### Task 9: World generator — `build_world()`

**Files:**
- Modify: `simulation/models/world.py` — add `build_world(config)`

- [ ] **Step 1: Write failing test**

```python
# add to tests/simulation/models/test_world.py
from simulation.config import SimConfig
from simulation.models.world import build_world

def test_build_world_correct_size():
    config = SimConfig(grid_size=20)
    world = build_world(config)
    assert len(world.grid) == 20
    assert len(world.grid[0]) == 20

def test_build_world_contains_all_tile_types():
    config = SimConfig(grid_size=20, seed=42)
    world = build_world(config)
    types = {world.grid[y][x].tile_type for y in range(20) for x in range(20)}
    assert types == {"farm", "forest", "mine", "town", "market"}

def test_build_world_is_reproducible():
    config = SimConfig(grid_size=20, seed=99)
    w1 = build_world(config)
    w2 = build_world(config)
    assert w1.grid[5][5].tile_type == w2.grid[5][5].tile_type
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/models/test_world.py -v
```

Expected: 3 existing pass, 3 new fail.

- [ ] **Step 3: Implement `build_world()` in `simulation/models/world.py`**

```python
import random

# Tile type distribution for a 20×20 grid
_TILE_WEIGHTS = {
    "farm":   0.30,
    "forest": 0.25,
    "mine":   0.20,
    "town":   0.15,
    "market": 0.10,
}

def build_world(config) -> "World":
    rng = random.Random(config.seed)
    tile_types = list(_TILE_WEIGHTS.keys())
    weights = list(_TILE_WEIGHTS.values())
    grid = []
    for y in range(config.grid_size):
        row = []
        for x in range(config.grid_size):
            tile_type = rng.choices(tile_types, weights=weights)[0]
            resource_yield = rng.uniform(0.8, 1.2)
            row.append(Tile(x=x, y=y, tile_type=tile_type, resource_yield=resource_yield))
        grid.append(row)
    return World(grid=grid)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/simulation/models/test_world.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add simulation/models/world.py tests/simulation/models/test_world.py
git commit -m "feat: build_world() — deterministic grid generator"
```

---

### Task 10: Agent factory — `spawn_agents()`, `fresh_settler()`

**Files:**
- Create: `simulation/models/agent.py` — add `spawn_agents()`, `fresh_settler()`

- [ ] **Step 1: Write failing tests**

```python
# add to tests/simulation/models/test_agent.py
from simulation.config import SimConfig
from simulation.models.world import build_world
from simulation.models.agent import spawn_agents, fresh_settler

def test_spawn_agents_count():
    config = SimConfig(num_agents=30, seed=42, grid_size=20)
    world = build_world(config)
    agents = spawn_agents(config, world)
    assert len(agents) == 30

def test_spawn_agents_all_alive():
    config = SimConfig(num_agents=30, seed=42, grid_size=20)
    world = build_world(config)
    agents = spawn_agents(config, world)
    assert all(a.alive for a in agents)

def test_spawn_agents_on_town_tiles():
    config = SimConfig(num_agents=10, seed=42, grid_size=20)
    world = build_world(config)
    agents = spawn_agents(config, world)
    town_positions = {(t.x, t.y) for row in world.grid for t in row if t.tile_type == "town"}
    for a in agents:
        assert a.location in town_positions

def test_fresh_settler_minimal_wealth():
    import random
    rng = random.Random(1)
    world = build_world(SimConfig(grid_size=20, seed=1))
    settler = fresh_settler(rng, world, tick=10)
    assert settler.alive is True
    assert settler.wealth < 5.0
    assert settler.hunger == 0.0
    assert settler.respawn_tick is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/models/test_agent.py -v
```

Expected: 3 existing pass, 4 new fail.

- [ ] **Step 3: Implement `spawn_agents()` and `fresh_settler()` in `simulation/models/agent.py`**

```python
import random as _random

_PROFESSIONS = ["farmer", "lumberjack", "miner", "trader"]

def fresh_settler(rng: _random.Random, world: "World", tick: int) -> Agent:
    town_tiles = [t for row in world.grid for t in row if t.tile_type == "town"]
    spawn_tile = rng.choice(town_tiles)
    return Agent(
        id=f"agent_{tick}_{rng.randint(1000, 9999)}",
        location=(spawn_tile.x, spawn_tile.y),
        profession=rng.choice(_PROFESSIONS),
        wealth=rng.uniform(0.5, 2.0),
        energy=1.0,
        hunger=0.0,
        alive=True,
        respawn_tick=None,
        inventory=Inventory(food=rng.uniform(1.0, 3.0)),
        skill=rng.uniform(0.3, 0.7),
        risk_aversion=rng.random(),
    )

def spawn_agents(config: "SimConfig", world: "World") -> list[Agent]:
    rng = _random.Random(config.seed + 1)
    return [fresh_settler(rng, world, tick=0) for _ in range(config.num_agents)]
```

Add the forward-reference import guard at the top of `agent.py`:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from simulation.models.world import World
    from simulation.config import SimConfig
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/simulation/models/test_agent.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add simulation/models/agent.py tests/simulation/models/test_agent.py
git commit -m "feat: spawn_agents() and fresh_settler() agent factories"
```

---

### Task 11: Market settlement logic

**Files:**
- Modify: `simulation/market.py` — add `reset_tick()`, `settle()`, `update_prices()`

- [ ] **Step 1: Write failing tests**

```python
# add to tests/simulation/test_market.py
from simulation.market import Market, reset_tick, settle, update_prices
from simulation.models.agent import Agent, Inventory
from simulation.config import SimConfig

def make_agent(id_, wealth, food=0.0):
    return Agent(id=id_, location=(0,0), profession="farmer",
                 wealth=wealth, energy=1.0, hunger=0.0,
                 alive=True, respawn_tick=None,
                 inventory=Inventory(food=food))

def make_market(food_price=1.0):
    return Market(
        prices=Inventory(food=food_price, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )

def test_reset_tick_clears_supply_demand():
    m = make_market()
    m.supply.food = 10.0
    m.demand.food = 5.0
    m.trade_volume = 3.0
    reset_tick(m)
    assert m.supply.food == 0.0
    assert m.demand.food == 0.0
    assert m.trade_volume == 0.0

def test_settle_supply_exceeds_demand_all_buyers_fill():
    """When supply > demand, all buyers fill in full."""
    config = SimConfig()
    market = make_market(food_price=2.0)
    seller = make_agent("seller", wealth=0.0, food=10.0)
    buyer = make_agent("buyer", wealth=20.0, food=0.0)

    # seller offers 5 food, buyer wants 3
    sell_orders = [{"agent_id": "seller", "resource": "food", "quantity": 5.0}]
    buy_orders  = [{"agent_id": "buyer",  "resource": "food", "quantity": 3.0}]
    agents = {"seller": seller, "buyer": buyer}

    events = settle(market, sell_orders, buy_orders, agents, tick=1)

    assert buyer.inventory.food == 3.0
    assert buyer.wealth == 20.0 - 3.0 * 2.0   # paid full quantity
    assert any(e.event_type == "trade_completed" for e in events)

def test_settle_demand_exceeds_supply_buyers_rationed():
    """When demand > supply, buyers get proportional fills."""
    config = SimConfig()
    market = make_market(food_price=1.0)
    seller = make_agent("seller", wealth=0.0, food=10.0)
    buyer1 = make_agent("b1", wealth=20.0)
    buyer2 = make_agent("b2", wealth=20.0)

    # only 4 food available, each buyer wants 4 → each gets 2
    sell_orders = [{"agent_id": "seller", "resource": "food", "quantity": 4.0}]
    buy_orders  = [{"agent_id": "b1", "resource": "food", "quantity": 4.0},
                   {"agent_id": "b2", "resource": "food", "quantity": 4.0}]
    agents = {"seller": seller, "b1": buyer1, "b2": buyer2}

    events = settle(market, sell_orders, buy_orders, agents, tick=1)

    assert abs(buyer1.inventory.food - 2.0) < 1e-9
    assert abs(buyer2.inventory.food - 2.0) < 1e-9

def test_update_prices_rises_when_demand_exceeds_supply():
    market = make_market(food_price=1.0)
    market.supply.food = 2.0
    market.demand.food = 4.0
    config = SimConfig(price_damping=0.1, price_min=0.1, price_max=50.0)
    update_prices(market, config)
    assert market.prices.food > 1.0

def test_update_prices_clamped_to_max():
    market = make_market(food_price=49.0)
    market.supply.food = 0.0001
    market.demand.food = 1000.0
    config = SimConfig(price_damping=0.1, price_min=0.1, price_max=50.0)
    update_prices(market, config)
    assert market.prices.food <= 50.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/test_market.py -v
```

Expected: 2 existing pass, 5 new fail.

- [ ] **Step 3: Implement market functions in `simulation/market.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from simulation.models.agent import Inventory
from simulation.events import Event, TRADE_COMPLETED, TRADE_FAILED


@dataclass
class Market:
    prices: Inventory
    supply: Inventory
    demand: Inventory
    trade_volume: float


def reset_tick(market: Market) -> None:
    market.supply = Inventory()
    market.demand = Inventory()
    market.trade_volume = 0.0


def settle(
    market: Market,
    sell_orders: list[dict],
    buy_orders: list[dict],
    agents: dict,
    tick: int,
) -> list[Event]:
    events = []
    for resource in ("food", "wood", "ore"):
        sells = [o for o in sell_orders if o["resource"] == resource]
        buys  = [o for o in buy_orders  if o["resource"] == resource]
        total_supply = sum(o["quantity"] for o in sells)
        total_demand = sum(o["quantity"] for o in buys)
        price = getattr(market.prices, resource)

        setattr(market.supply, resource, getattr(market.supply, resource) + total_supply)
        setattr(market.demand, resource, getattr(market.demand, resource) + total_demand)

        if total_demand == 0 or total_supply == 0:
            continue

        if total_demand <= total_supply:
            # all buyers fill in full; sellers fill proportionally
            fill_ratio_sellers = total_demand / total_supply if total_supply > 0 else 0.0
            for o in buys:
                buyer = agents[o["agent_id"]]
                qty = o["quantity"]
                cost = qty * price
                buyer.wealth -= cost
                setattr(buyer.inventory, resource,
                        getattr(buyer.inventory, resource) + qty)
                market.trade_volume += qty
            for o in sells:
                seller = agents[o["agent_id"]]
                qty_sold = o["quantity"] * fill_ratio_sellers
                revenue = qty_sold * price
                seller.wealth += revenue
                setattr(seller.inventory, resource,
                        getattr(seller.inventory, resource) - qty_sold)
                events.append(Event(
                    tick=tick, event_type=TRADE_COMPLETED,
                    actors=[o["agent_id"]],
                    payload={"resource": resource, "qty": qty_sold, "price": price},
                ))
        else:
            # demand > supply: buyers rationed proportionally; sellers fill in full
            fill_ratio = total_supply / total_demand
            for o in buys:
                buyer = agents[o["agent_id"]]
                qty = o["quantity"] * fill_ratio
                cost = qty * price
                if cost > buyer.wealth + 1e-9:
                    events.append(Event(
                        tick=tick, event_type=TRADE_FAILED,
                        actors=[o["agent_id"]],
                        payload={"resource": resource, "reason": "insufficient_funds"},
                    ))
                    continue
                buyer.wealth -= cost
                setattr(buyer.inventory, resource,
                        getattr(buyer.inventory, resource) + qty)
                market.trade_volume += qty
            for o in sells:
                seller = agents[o["agent_id"]]
                revenue = o["quantity"] * price
                seller.wealth += revenue
                setattr(seller.inventory, resource,
                        getattr(seller.inventory, resource) - o["quantity"])
                events.append(Event(
                    tick=tick, event_type=TRADE_COMPLETED,
                    actors=[o["agent_id"]],
                    payload={"resource": resource, "qty": o["quantity"], "price": price},
                ))
    return events


def update_prices(market: Market, config) -> None:
    for resource in ("food", "wood", "ore"):
        supply = getattr(market.supply, resource)
        demand = getattr(market.demand, resource)
        price  = getattr(market.prices, resource)
        ratio  = demand / max(supply, 0.001)
        new_price = price * (1 + config.price_damping * (ratio - 1))
        new_price = max(config.price_min, min(config.price_max, new_price))
        setattr(market.prices, resource, new_price)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/simulation/test_market.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add simulation/market.py tests/simulation/test_market.py
git commit -m "feat: market settlement — proportional rationing, damped price update"
```

---

### Task 12: `SimulationEngine` — tick loop, survival, respawn

**Files:**
- Create: `simulation/engine.py`
- Create: `tests/simulation/test_engine.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/simulation/test_engine.py
import random
from simulation.config import SimConfig
from simulation.models.world import build_world
from simulation.models.agent import spawn_agents, Inventory
from simulation.market import Market
from simulation.models.state import SimulationState
from simulation.engine import SimulationEngine

def make_state(config=None):
    config = config or SimConfig(seed=42, num_agents=5, grid_size=10)
    world = build_world(config)
    agents = spawn_agents(config, world)
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    return SimulationState(world=world, agents=agents, market=market), config

def test_tick_increments_world_tick():
    state, config = make_state()
    engine = SimulationEngine(config, state)
    result = engine.tick()
    assert result.tick == 0
    assert state.world.tick == 1

def test_tick_returns_tick_result():
    from simulation.models.state import TickResult
    state, config = make_state()
    engine = SimulationEngine(config, state)
    result = engine.tick()
    assert isinstance(result, TickResult)
    assert result.metrics.population > 0

def test_agent_starves_when_no_food():
    config = SimConfig(seed=1, num_agents=1, grid_size=5,
                       food_per_tick=1.0, starvation_death_ticks=2)
    world = build_world(config)
    agents = spawn_agents(config, world)
    # drain all food
    for a in agents:
        a.inventory.food = 0.0
        a.hunger = 1.0
        a.consecutive_starving = 1  # one tick away from death
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    state = SimulationState(world=world, agents=agents, market=market)
    engine = SimulationEngine(config, state)
    result = engine.tick()
    dead = [a for a in state.agents if not a.alive]
    assert len(dead) == 1
    assert any(e.event_type == "agent_starved" for e in result.events)

def test_respawn_occurs_after_delay():
    config = SimConfig(seed=2, num_agents=1, grid_size=5,
                       starvation_death_ticks=1, respawn_delay=(2, 2))
    world = build_world(config)
    agents = spawn_agents(config, world)
    for a in agents:
        a.inventory.food = 0.0
        a.hunger = 1.0
        a.consecutive_starving = 0
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    state = SimulationState(world=world, agents=agents, market=market)
    engine = SimulationEngine(config, state)
    engine.tick()   # tick 0: dies, respawn_tick = 2
    engine.tick()   # tick 1: still dead
    assert not state.agents[0].alive
    engine.tick()   # tick 2: respawns
    assert state.agents[0].alive
    assert any(e.event_type == "agent_migrated_in"
               for tick_events in [engine._last_events] for e in tick_events)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/test_engine.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `simulation/engine.py`**

```python
from __future__ import annotations
import random
import dataclasses
from simulation.config import SimConfig
from simulation.models.state import SimulationState, TickResult
from simulation.models.agent import Agent, Inventory, fresh_settler
from simulation.market import reset_tick, settle, update_prices
from simulation.events import Event, AGENT_STARVED, AGENT_MIGRATED_IN, RESOURCE_PRODUCED
from simulation.metrics import TickMetrics, net_worth, gini
from simulation.heuristics import decide


class SimulationEngine:
    def __init__(self, config: SimConfig, state: SimulationState) -> None:
        self.config = config
        self.state = state
        self.rng = random.Random(config.seed)
        self._last_events: list[Event] = []

    def tick(self) -> TickResult:
        tick = self.state.world.tick
        events: list[Event] = []

        reset_tick(self.state.market)

        sell_orders: list[dict] = []
        buy_orders: list[dict] = []
        alive_agents = [a for a in self.state.agents if a.alive]

        for agent in alive_agents:
            actions = decide(agent, self.state, self.config, self.rng)
            for action in actions:
                self._execute_action(agent, action, sell_orders, buy_orders, events, tick)

        trade_events = settle(
            self.state.market, sell_orders, buy_orders,
            {a.id: a for a in self.state.agents}, tick,
        )
        events.extend(trade_events)

        self._apply_upkeep_and_survival(alive_agents, events, tick)
        update_prices(self.state.market, self.config)
        self._process_respawns(events, tick)

        metrics = self._compute_metrics(tick)
        snapshot_path = self._maybe_snapshot(tick)

        self._last_events = events
        self.state.world.tick += 1
        return TickResult(tick=tick, events=events, metrics=metrics, snapshot_path=snapshot_path)

    def _execute_action(self, agent: Agent, action, sell_orders, buy_orders, events, tick):
        atype = action.action_type
        payload = action.payload

        if atype == "move":
            dx, dy = payload.get("dx", 0), payload.get("dy", 0)
            x, y = agent.location
            nx = max(0, min(self.config.grid_size - 1, x + dx))
            ny = max(0, min(self.config.grid_size - 1, y + dy))
            agent.location = (nx, ny)

        elif atype == "produce":
            tile = self.state.world.grid[agent.location[1]][agent.location[0]]
            base = self.config.base_production.get(agent.profession, {})
            for resource, base_rate in base.items():
                qty = base_rate * agent.skill * agent.energy * tile.resource_yield
                setattr(agent.inventory, resource,
                        getattr(agent.inventory, resource) + qty)
                events.append(Event(
                    tick=tick, event_type=RESOURCE_PRODUCED,
                    actors=[agent.id],
                    payload={"resource": resource, "qty": qty},
                ))

        elif atype == "trade":
            side = payload.get("side", "sell")
            resource = payload.get("resource", "food")
            quantity = payload.get("quantity", 0.0)
            if side == "sell":
                sell_orders.append({"agent_id": agent.id, "resource": resource, "quantity": quantity})
            else:
                buy_orders.append({"agent_id": agent.id, "resource": resource, "quantity": quantity})

        elif atype == "rest":
            agent.energy = min(1.0, agent.energy + 0.3)

    def _apply_upkeep_and_survival(self, agents: list[Agent], events: list[Event], tick: int):
        for agent in agents:
            if agent.inventory.food >= self.config.food_per_tick:
                agent.inventory.food -= self.config.food_per_tick
                agent.hunger = max(0.0, agent.hunger - 0.2)
                agent.consecutive_starving = 0
            else:
                agent.hunger = min(1.0, agent.hunger + 0.25)
                if agent.hunger >= 1.0:
                    agent.consecutive_starving += 1
                if agent.consecutive_starving >= self.config.starvation_death_ticks:
                    agent.alive = False
                    delay = self.rng.randint(*self.config.respawn_delay)
                    agent.respawn_tick = tick + delay
                    events.append(Event(
                        tick=tick, event_type=AGENT_STARVED,
                        actors=[agent.id], payload={},
                    ))
            # energy depletes slightly each tick
            agent.energy = max(0.1, agent.energy - 0.05)

    def _process_respawns(self, events: list[Event], tick: int):
        for i, agent in enumerate(self.state.agents):
            if not agent.alive and agent.respawn_tick is not None and tick >= agent.respawn_tick:
                new_agent = fresh_settler(self.rng, self.state.world, tick)
                self.state.agents[i] = new_agent
                events.append(Event(
                    tick=tick, event_type=AGENT_MIGRATED_IN,
                    actors=[new_agent.id], payload={},
                ))

    def _compute_metrics(self, tick: int) -> TickMetrics:
        alive = [a for a in self.state.agents if a.alive]
        nw = [net_worth(a, self.state.market.prices) for a in alive]
        return TickMetrics(
            tick=tick,
            population=len(alive),
            total_wealth=sum(nw),
            gini_coefficient=gini(nw),
            total_food_inventory=sum(a.inventory.food for a in alive),
            prices=dataclasses.replace(self.state.market.prices),
            trade_volume=self.state.market.trade_volume,
        )

    def _maybe_snapshot(self, tick: int) -> str | None:
        if tick % self.config.snapshot_interval == 0 and tick > 0:
            # persistence layer handles the actual write; engine just signals
            return f"tick_{tick:04d}"
        return None
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/simulation/test_engine.py -v
```

Expected: 4 passed. (Note: `heuristics` module is imported — a stub is needed first.)

> **Stub needed:** If `heuristics.py` doesn't exist yet, create a minimal stub before running:
> ```python
> # simulation/heuristics.py (stub)
> def decide(agent, state, config, rng):
>     return []
> ```

- [ ] **Step 5: Run full suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add simulation/engine.py tests/simulation/test_engine.py
git commit -m "feat: SimulationEngine tick loop — action execution, survival, respawn"
```

---

## Chunk 3: Agent Heuristics

### Task 13: `build_context()` — agent observation

**Files:**
- Create: `simulation/heuristics.py`
- Create: `tests/simulation/test_heuristics.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/simulation/test_heuristics.py
from simulation.heuristics import build_context, AgentContext
from simulation.models.agent import Agent, Inventory
from simulation.models.world import Tile, World
from simulation.market import Market
from simulation.models.state import SimulationState

def make_tile(x, y, tile_type="farm"):
    return Tile(x=x, y=y, tile_type=tile_type, resource_yield=1.0)

def make_world_3x3(center_type="market"):
    grid = [[make_tile(x, y) for x in range(3)] for y in range(3)]
    grid[1][1] = make_tile(1, 1, center_type)
    return World(grid=grid)

def make_agent(location=(1,1), hunger=0.0, food=5.0):
    return Agent(id="a1", location=location, profession="farmer",
                 wealth=10.0, energy=1.0, hunger=hunger, alive=True,
                 respawn_tick=None, inventory=Inventory(food=food))

def make_state(agent, world):
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    return SimulationState(world=world, agents=[agent], market=market)

def test_context_at_market_tile():
    world = make_world_3x3("market")
    agent = make_agent(location=(1,1))
    state = make_state(agent, world)
    ctx = build_context(agent, state)
    assert ctx.at_market is True

def test_context_not_at_market():
    world = make_world_3x3("farm")
    agent = make_agent(location=(1,1))
    state = make_state(agent, world)
    ctx = build_context(agent, state)
    assert ctx.at_market is False

def test_context_food_need_high_when_hungry():
    world = make_world_3x3()
    agent = make_agent(hunger=0.9, food=0.0)
    state = make_state(agent, world)
    ctx = build_context(agent, state)
    assert ctx.food_need > 0.5

def test_context_nearest_market_found():
    world = make_world_3x3("farm")
    # place a market at (2,2)
    world.grid[2][2] = make_tile(2, 2, "market")
    agent = make_agent(location=(0,0))
    state = make_state(agent, world)
    ctx = build_context(agent, state)
    assert ctx.nearest_market == (2, 2)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/test_heuristics.py::test_context_at_market_tile -v
```

Expected: `ImportError` or `AttributeError`.

- [ ] **Step 3: Implement `build_context()` in `simulation/heuristics.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from simulation.models.agent import Agent
from simulation.models.state import SimulationState
from simulation.models.actions import Action
from simulation.config import SimConfig
import random


@dataclass
class AgentContext:
    current_tile_type: str
    at_market: bool
    food_need: float          # 0–1 urgency to acquire food
    nearest_market: tuple[int, int] | None
    nearest_profession_tile: tuple[int, int] | None
    surplus_resource: str | None   # resource with most inventory
    surplus_qty: float


def build_context(agent: Agent, state: SimulationState) -> AgentContext:
    x, y = agent.location
    tile = state.world.grid[y][x]
    at_market = (tile.tile_type == "market")

    # food need: blend hunger and low inventory
    food_inv = agent.inventory.food
    food_need = agent.hunger * 0.7 + max(0.0, (2.0 - food_inv) / 2.0) * 0.3
    food_need = min(1.0, food_need)

    # profession→tile mapping
    prof_tile = {
        "farmer": "farm", "lumberjack": "forest",
        "miner": "mine", "trader": "market",
    }
    target_tile_type = prof_tile.get(agent.profession, "market")

    nearest_market = _nearest_tile(agent.location, state, "market")
    nearest_profession_tile = _nearest_tile(agent.location, state, target_tile_type)

    inv = agent.inventory
    surplus_map = {"food": inv.food, "wood": inv.wood, "ore": inv.ore}
    surplus_resource = max(surplus_map, key=surplus_map.get)
    surplus_qty = surplus_map[surplus_resource]

    return AgentContext(
        current_tile_type=tile.tile_type,
        at_market=at_market,
        food_need=food_need,
        nearest_market=nearest_market,
        nearest_profession_tile=nearest_profession_tile,
        surplus_resource=surplus_resource,
        surplus_qty=surplus_qty,
    )


def _nearest_tile(location: tuple[int,int], state: SimulationState, tile_type: str) -> tuple[int,int] | None:
    x, y = location
    best, best_dist = None, float("inf")
    for row in state.world.grid:
        for tile in row:
            if tile.tile_type == tile_type:
                d = abs(tile.x - x) + abs(tile.y - y)
                if d < best_dist:
                    best_dist = d
                    best = (tile.x, tile.y)
    return best
```

- [ ] **Step 4: Run context tests**

```bash
pytest tests/simulation/test_heuristics.py -k "context" -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add simulation/heuristics.py tests/simulation/test_heuristics.py
git commit -m "feat: heuristics build_context() — agent observation"
```

---

### Task 14: `score_actions()`, `survival_actions()`, `decide()`

**Files:**
- Modify: `simulation/heuristics.py` — add scoring and decision functions

- [ ] **Step 1: Write failing tests**

```python
# add to tests/simulation/test_heuristics.py
import random
from simulation.heuristics import decide
from simulation.config import SimConfig

def make_full_state(agent, world=None):
    if world is None:
        world = make_world_3x3()
    market = Market(
        prices=Inventory(food=1.5, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    return SimulationState(world=world, agents=[agent], market=market)

def test_decide_returns_two_actions():
    agent = make_agent()
    state = make_full_state(agent)
    actions = decide(agent, state, SimConfig(), random.Random(1))
    assert len(actions) == 2

def test_decide_starving_agent_moves_to_market():
    """A starving agent with no food should try to reach market."""
    agent = make_agent(hunger=0.9, food=0.0)
    world = make_world_3x3("farm")
    world.grid[0][0] = make_tile(0, 0, "market")
    state = make_full_state(agent, world)
    actions = decide(agent, state, SimConfig(), random.Random(1))
    # first action should be move (survival override)
    assert actions[0].action_type == "move"

def test_decide_farmer_on_farm_produces():
    """A farmer on a farm tile with energy should produce."""
    world = make_world_3x3("farm")
    agent = Agent(id="a1", location=(1,1), profession="farmer",
                  wealth=10.0, energy=1.0, hunger=0.0, alive=True,
                  respawn_tick=None, inventory=Inventory(food=5.0))
    state = make_full_state(agent, world)
    actions = decide(agent, state, SimConfig(), random.Random(1))
    action_types = [a.action_type for a in actions]
    assert "produce" in action_types

def test_decide_at_market_with_surplus_sells():
    """Agent at market with surplus food should sell."""
    world = make_world_3x3("market")
    agent = Agent(id="a1", location=(1,1), profession="trader",
                  wealth=10.0, energy=1.0, hunger=0.0, alive=True,
                  respawn_tick=None, inventory=Inventory(food=8.0))
    state = make_full_state(agent, world)
    actions = decide(agent, state, SimConfig(), random.Random(1))
    action_types = [a.action_type for a in actions]
    assert "trade" in action_types
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/simulation/test_heuristics.py -k "decide" -v
```

Expected: fail (stub `decide` returns `[]`).

- [ ] **Step 3: Implement `score_actions()`, `survival_actions()`, `decide()` in `simulation/heuristics.py`**

```python
def decide(agent: Agent, state: SimulationState, config: SimConfig, rng: random.Random) -> list[Action]:
    ctx = build_context(agent, state)

    # survival override
    if agent.hunger > 0.7 and agent.inventory.food < 1.0:
        return _survival_actions(agent, ctx, state)

    candidates = _score_actions(agent, ctx, state, config)
    candidates.sort(key=lambda x: x[1], reverse=True)

    chosen = []
    seen_types = set()
    for action, score in candidates:
        if action.action_type not in seen_types:
            chosen.append(action)
            seen_types.add(action.action_type)
        if len(chosen) == 2:
            break

    # pad with rest if fewer than 2
    while len(chosen) < 2:
        chosen.append(Action(agent_id=agent.id, action_type="rest"))

    return chosen


def _survival_actions(agent: Agent, ctx: AgentContext, state: SimulationState) -> list[Action]:
    actions = []
    if ctx.at_market:
        actions.append(Action(agent_id=agent.id, action_type="trade",
                              payload={"side": "buy", "resource": "food", "quantity": 3.0}))
        actions.append(Action(agent_id=agent.id, action_type="rest"))
    else:
        target = ctx.nearest_market
        if target:
            dx = _sign(target[0] - agent.location[0])
            dy = _sign(target[1] - agent.location[1])
            actions.append(Action(agent_id=agent.id, action_type="move",
                                  payload={"dx": dx, "dy": 0}))
            actions.append(Action(agent_id=agent.id, action_type="move",
                                  payload={"dx": 0, "dy": dy}))
        else:
            actions = [Action(agent_id=agent.id, action_type="rest"),
                       Action(agent_id=agent.id, action_type="rest")]
    return actions


def _score_actions(agent: Agent, ctx: AgentContext, state: SimulationState, config: SimConfig) -> list[tuple[Action, float]]:
    scores = []
    aid = agent.id

    # move toward profession tile
    if ctx.nearest_profession_tile and ctx.nearest_profession_tile != agent.location:
        move_score = 0.5 + (0.2 if agent.energy > 0.6 else 0.0)
        tx, ty = ctx.nearest_profession_tile
        dx = _sign(tx - agent.location[0])
        dy = _sign(ty - agent.location[1])
        scores.append((Action(agent_id=aid, action_type="move", payload={"dx": dx, "dy": 0}), move_score))

    # move toward market
    if ctx.nearest_market and not ctx.at_market:
        mkt_score = 0.4 + (0.3 if ctx.surplus_qty > 2 else 0.0)
        mx, my = ctx.nearest_market
        dx = _sign(mx - agent.location[0])
        dy = _sign(my - agent.location[1])
        scores.append((Action(agent_id=aid, action_type="move", payload={"dx": dx, "dy": 0}), mkt_score))

    # produce
    prof_bonus = {"farmer": 0.3, "lumberjack": 0.3, "miner": 0.3, "trader": 0.0}
    on_profession_tile = (ctx.current_tile_type == {
        "farmer": "farm", "lumberjack": "forest", "miner": "mine", "trader": "market"
    }.get(agent.profession))
    produce_score = (0.6 * agent.energy * agent.skill - agent.hunger * 0.3
                     + (prof_bonus.get(agent.profession, 0) if on_profession_tile else 0))
    if agent.profession != "trader":
        scores.append((Action(agent_id=aid, action_type="produce"), produce_score))

    # trade sell
    if ctx.at_market and ctx.surplus_qty > 1.0:
        sell_score = 0.5
        scores.append((Action(agent_id=aid, action_type="trade", payload={
            "side": "sell", "resource": ctx.surplus_resource, "quantity": ctx.surplus_qty * 0.5,
        }), sell_score))

    # trade buy food
    if ctx.at_market and agent.hunger > 0.5:
        buy_score = 0.8 - agent.risk_aversion * 0.2
        scores.append((Action(agent_id=aid, action_type="trade", payload={
            "side": "buy", "resource": "food", "quantity": 3.0,
        }), buy_score))

    # rest
    rest_score = 0.3 + (agent.risk_aversion * 0.4 if agent.energy < 0.3 else 0.0)
    scores.append((Action(agent_id=aid, action_type="rest"), rest_score))

    return scores


def _sign(n: float) -> int:
    return 1 if n > 0 else (-1 if n < 0 else 0)
```

- [ ] **Step 4: Run all heuristic tests**

```bash
pytest tests/simulation/test_heuristics.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Run full suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add simulation/heuristics.py tests/simulation/test_heuristics.py
git commit -m "feat: heuristics score_actions(), survival override, decide()"
```

---

## Chunk 4: Persistence Layer

### Task 15: Event log — `append_event()`, `read_events()`

**Files:**
- Create: `persistence/eventlog.py`
- Create: `tests/persistence/test_eventlog.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/persistence/test_eventlog.py
import json
import tempfile
from pathlib import Path
from simulation.events import Event, TRADE_COMPLETED
from persistence.eventlog import append_event, read_events

def make_event(tick, event_type=TRADE_COMPLETED):
    return Event(tick=tick, event_type=event_type, actors=["a01"], payload={"qty": 1})

def test_append_event_creates_file(tmp_path):
    log_path = tmp_path / "events.jsonl"
    e = make_event(tick=1)
    append_event(e, log_path)
    assert log_path.exists()

def test_append_event_valid_json(tmp_path):
    log_path = tmp_path / "events.jsonl"
    append_event(make_event(tick=1), log_path)
    line = log_path.read_text().strip()
    data = json.loads(line)
    assert data["tick"] == 1
    assert data["event_type"] == TRADE_COMPLETED

def test_read_events_returns_all(tmp_path):
    log_path = tmp_path / "events.jsonl"
    for t in range(5):
        append_event(make_event(tick=t), log_path)
    events = read_events(log_path)
    assert len(events) == 5

def test_read_events_filter_by_tick_range(tmp_path):
    log_path = tmp_path / "events.jsonl"
    for t in range(10):
        append_event(make_event(tick=t), log_path)
    events = read_events(log_path, from_tick=3, to_tick=6)
    assert all(3 <= e.tick <= 6 for e in events)
    assert len(events) == 4

def test_read_events_filter_by_type(tmp_path):
    log_path = tmp_path / "events.jsonl"
    append_event(make_event(tick=1, event_type=TRADE_COMPLETED), log_path)
    append_event(make_event(tick=2, event_type="agent_starved"), log_path)
    events = read_events(log_path, event_type=TRADE_COMPLETED)
    assert len(events) == 1
    assert events[0].event_type == TRADE_COMPLETED
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/persistence/test_eventlog.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `persistence/eventlog.py`**

```python
from __future__ import annotations
import json
import dataclasses
from pathlib import Path
from simulation.events import Event


def append_event(event: Event, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(json.dumps(dataclasses.asdict(event)) + "\n")


def read_events(
    log_path: Path,
    from_tick: int = 0,
    to_tick: int | None = None,
    event_type: str | None = None,
) -> list[Event]:
    if not log_path.exists():
        return []
    events = []
    with log_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data["tick"] < from_tick:
                continue
            if to_tick is not None and data["tick"] > to_tick:
                continue
            if event_type is not None and data["event_type"] != event_type:
                continue
            events.append(Event(**data))
    return events
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/persistence/test_eventlog.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add persistence/eventlog.py tests/persistence/test_eventlog.py
git commit -m "feat: event log — append_event(), read_events() with filtering"
```

---

### Task 16: Snapshots — `save_snapshot()`, `load_snapshot()`

**Files:**
- Create: `persistence/snapshots.py`
- Create: `tests/persistence/test_snapshots.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/persistence/test_snapshots.py
import random
from pathlib import Path
from simulation.config import SimConfig
from simulation.models.world import build_world
from simulation.models.agent import spawn_agents, Inventory
from simulation.market import Market
from simulation.models.state import SimulationState
from persistence.snapshots import save_snapshot, load_snapshot, list_snapshots

def make_state():
    config = SimConfig(seed=42, num_agents=3, grid_size=5)
    world = build_world(config)
    agents = spawn_agents(config, world)
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    return SimulationState(world=world, agents=agents, market=market)

def test_save_snapshot_creates_file(tmp_path):
    state = make_state()
    rng = random.Random(42)
    save_snapshot(state, tick=50, rng=rng, snapshot_dir=tmp_path)
    files = list(tmp_path.glob("tick_*.json"))
    assert len(files) == 1

def test_load_snapshot_restores_state(tmp_path):
    state = make_state()
    rng = random.Random(42)
    save_snapshot(state, tick=50, rng=rng, snapshot_dir=tmp_path)
    restored_state, restored_rng = load_snapshot("tick_0050", snapshot_dir=tmp_path)
    assert restored_state.world.tick == state.world.tick
    assert len(restored_state.agents) == len(state.agents)
    assert restored_state.agents[0].id == state.agents[0].id

def test_load_snapshot_restores_rng_state(tmp_path):
    state = make_state()
    rng = random.Random(99)
    rng.random()  # advance state
    save_snapshot(state, tick=10, rng=rng, snapshot_dir=tmp_path)
    _, restored_rng = load_snapshot("tick_0010", snapshot_dir=tmp_path)
    # both RNGs should produce identical sequences
    assert rng.random() == restored_rng.random()

def test_list_snapshots(tmp_path):
    state = make_state()
    rng = random.Random(1)
    save_snapshot(state, tick=50, rng=rng, snapshot_dir=tmp_path)
    save_snapshot(state, tick=100, rng=rng, snapshot_dir=tmp_path)
    entries = list_snapshots(tmp_path)
    assert len(entries) == 2
    assert entries[0]["snapshot_id"] == "tick_0050"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/persistence/test_snapshots.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `persistence/snapshots.py`**

```python
from __future__ import annotations
import json
import random
import dataclasses
from pathlib import Path
from simulation.models.state import SimulationState
from simulation.models.world import World, Tile
from simulation.models.agent import Agent, Inventory
from simulation.market import Market


def save_snapshot(state: SimulationState, tick: int, rng: random.Random, snapshot_dir: Path) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / f"tick_{tick:04d}.json"
    data = {
        "tick": tick,
        "rng_state": list(rng.getstate()[1]),   # mersenne twister state
        "state": dataclasses.asdict(state),
    }
    path.write_text(json.dumps(data, default=str))
    return path


def load_snapshot(snapshot_id: str, snapshot_dir: Path) -> tuple[SimulationState, random.Random]:
    path = snapshot_dir / f"{snapshot_id}.json"
    data = json.loads(path.read_text())

    rng = random.Random()
    # restore mersenne twister state
    rng_state = (3, tuple(int(x) for x in data["rng_state"]), None)
    rng.setstate(rng_state)

    s = data["state"]
    grid = [
        [Tile(**t) for t in row]
        for row in s["world"]["grid"]
    ]
    world = World(grid=grid, tick=s["world"]["tick"])
    agents = [_agent_from_dict(a) for a in s["agents"]]
    market = Market(
        prices=Inventory(**s["market"]["prices"]),
        supply=Inventory(**s["market"]["supply"]),
        demand=Inventory(**s["market"]["demand"]),
        trade_volume=s["market"]["trade_volume"],
    )
    state = SimulationState(world=world, agents=agents, market=market)
    return state, rng


def list_snapshots(snapshot_dir: Path) -> list[dict]:
    if not snapshot_dir.exists():
        return []
    entries = []
    for path in sorted(snapshot_dir.glob("tick_*.json")):
        data = json.loads(path.read_text())
        entries.append({
            "snapshot_id": path.stem,
            "tick": data["tick"],
            "timestamp": path.stat().st_mtime,
        })
    return entries


def _agent_from_dict(d: dict) -> Agent:
    d["inventory"] = Inventory(**d["inventory"])
    d["location"] = tuple(d["location"])
    return Agent(**d)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/persistence/test_snapshots.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run full suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add persistence/snapshots.py tests/persistence/test_snapshots.py
git commit -m "feat: snapshot persistence — save/load SimulationState + RNG state"
```

---

## Chunk 5: FastAPI Server & WebSocket

### Task 17: Pydantic schemas

**Files:**
- Create: `server/schemas.py`

- [ ] **Step 1: Implement `server/schemas.py`**

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal


class ControlCommand(BaseModel):
    command: Literal["pause", "resume", "step", "reset"]

class ControlResponse(BaseModel):
    ok: bool
    status: Literal["running", "paused"]
    tick: int

class StateResponse(BaseModel):
    state: dict          # full SimulationState serialization
    status: Literal["running", "paused"]
    tick_rate_hz: float
    config: dict

class SnapshotEntry(BaseModel):
    snapshot_id: str
    tick: int
    timestamp: float

class ReplayRequest(BaseModel):
    snapshot_id: str
    to_tick: int | None = None

class ReplayResponse(BaseModel):
    final_tick: int
    state: dict
    metrics: list[dict]
    events: list[dict]
```

- [ ] **Step 2: Verify import**

```bash
python -c "from server.schemas import StateResponse, ReplayRequest; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add server/schemas.py
git commit -m "feat: Pydantic API schemas"
```

---

### Task 18: WebSocket manager + engine state machine

**Files:**
- Create: `server/ws.py`
- Create: `tests/server/test_routes.py` (WebSocket integration test added here)

- [ ] **Step 1: Write failing test**

```python
# tests/server/test_routes.py
import pytest
from fastapi.testclient import TestClient
from server.main import create_app
from simulation.config import SimConfig

@pytest.fixture
def client():
    app = create_app(SimConfig(seed=42, num_agents=5, grid_size=5, tick_rate_hz=0))
    return TestClient(app)

def test_get_state_returns_200(client):
    resp = client.get("/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("running", "paused")

def test_post_control_pause(client):
    resp = client.post("/control", json={"command": "pause"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"

def test_post_control_resume(client):
    client.post("/control", json={"command": "pause"})
    resp = client.post("/control", json={"command": "resume"})
    assert resp.json()["status"] == "running"

def test_get_snapshots_empty(client):
    resp = client.get("/snapshots")
    assert resp.status_code == 200
    assert resp.json() == []

def test_get_metrics_returns_list(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/server/test_routes.py -v
```

Expected: `ImportError` — `server.main` doesn't exist yet.

- [ ] **Step 3: Implement `server/ws.py`**

```python
from __future__ import annotations
import asyncio
import dataclasses
import json
from typing import Literal
from fastapi import WebSocket
from simulation.engine import SimulationEngine
from simulation.models.state import TickResult


EngineStatus = Literal["running", "paused"]


class SimulationManager:
    def __init__(self, engine: SimulationEngine) -> None:
        self.engine = engine
        self.status: EngineStatus = "running"
        self._clients: list[WebSocket] = []
        self._task: asyncio.Task | None = None
        self._metrics_history: list[dict] = []

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.remove(ws)

    async def handle_message(self, msg: dict) -> None:
        mtype = msg.get("type")
        if mtype == "pause":
            self.status = "paused"
        elif mtype == "resume":
            self.status = "running"
        elif mtype == "step" and self.status == "paused":
            result = self.engine.tick()
            self._record(result)
            await self._broadcast({"type": "tick", "payload": self._tick_payload(result)})
        elif mtype == "set_speed":
            self.engine.config.tick_rate_hz = float(msg.get("hz", 2.0))
        elif mtype == "reset":
            from simulation.models.world import build_world
            from simulation.models.agent import spawn_agents, Inventory
            from simulation.market import Market
            from simulation.models.state import SimulationState
            config = self.engine.config
            world = build_world(config)
            agents = spawn_agents(config, world)
            market = Market(
                prices=Inventory(food=1.0, wood=1.0, ore=1.0),
                supply=Inventory(), demand=Inventory(), trade_volume=0.0,
            )
            self.engine.state = SimulationState(world=world, agents=agents, market=market)
            self.status = "running"
            self._metrics_history.clear()

        await self._broadcast_status()

    async def _run_loop(self) -> None:
        while True:
            hz = self.engine.config.tick_rate_hz
            sleep = 1.0 / hz if hz > 0 else 1.0
            await asyncio.sleep(sleep)
            if self.status == "running":
                result = self.engine.tick()
                self._record(result)
                await self._broadcast({"type": "tick", "payload": self._tick_payload(result)})

    def _tick_payload(self, result: TickResult) -> dict:
        """Include agent + market state alongside tick result so the frontend
        can re-render the canvas on every tick without a separate /state fetch."""
        d = dataclasses.asdict(result)
        d["agents"] = dataclasses.asdict(self.engine.state)["agents"]
        d["market"] = dataclasses.asdict(self.engine.state.market)
        return d

    def _record(self, result: TickResult) -> None:
        self._metrics_history.append(dataclasses.asdict(result.metrics))

    async def _broadcast(self, payload: dict) -> None:
        dead = []
        for ws in self._clients:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.remove(ws)

    async def _broadcast_status(self) -> None:
        await self._broadcast({
            "type": "status",
            "payload": {"status": self.status, "tick": self.engine.state.world.tick},
        })


def _serialize(obj) -> dict:
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    return obj
```

- [ ] **Step 4: Implement `server/routes.py`**

```python
from __future__ import annotations
import dataclasses
from pathlib import Path
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from server.schemas import (
    ControlCommand, ControlResponse, StateResponse,
    ReplayRequest, ReplayResponse,
)
from persistence.snapshots import list_snapshots, load_snapshot, save_snapshot
from persistence.eventlog import read_events

router = APIRouter()
SNAPSHOT_DIR = Path("data/snapshots")
LOG_PATH = Path("logs/events.jsonl")


def _make_router(manager):
    r = APIRouter()

    @r.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                msg = await ws.receive_json()
                await manager.handle_message(msg)
        except WebSocketDisconnect:
            manager.disconnect(ws)

    @r.get("/state", response_model=StateResponse)
    async def get_state():
        return StateResponse(
            state=dataclasses.asdict(manager.engine.state),
            status=manager.status,
            tick_rate_hz=manager.engine.config.tick_rate_hz,
            config=dataclasses.asdict(manager.engine.config),
        )

    @r.get("/metrics")
    async def get_metrics(from_tick: int = 0, to_tick: int | None = None):
        history = manager._metrics_history
        if to_tick is not None:
            history = [m for m in history if from_tick <= m["tick"] <= to_tick]
        else:
            history = [m for m in history if m["tick"] >= from_tick]
        return history

    @r.get("/snapshots")
    async def get_snapshots():
        return list_snapshots(SNAPSHOT_DIR)

    @r.get("/events")
    async def get_events(from_tick: int = 0, to_tick: int | None = None, event_type: str | None = None):
        events = read_events(LOG_PATH, from_tick=from_tick, to_tick=to_tick, event_type=event_type)
        return [dataclasses.asdict(e) for e in events]

    @r.post("/control", response_model=ControlResponse)
    async def post_control(cmd: ControlCommand):
        await manager.handle_message({"type": cmd.command})
        return ControlResponse(ok=True, status=manager.status, tick=manager.engine.state.world.tick)

    @r.post("/replay", response_model=ReplayResponse)
    async def post_replay(req: ReplayRequest):
        try:
            state, rng = load_snapshot(req.snapshot_id, SNAPSHOT_DIR)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        from simulation.engine import SimulationEngine
        # replay_engine.state is the same object as `state` (reference, not copy)
        # so replay_engine.state.world.tick increments as ticks run
        replay_engine = SimulationEngine(manager.engine.config, state)
        replay_engine.rng = rng
        replay_events = []
        replay_metrics = []
        start_tick = replay_engine.state.world.tick
        target = req.to_tick if req.to_tick is not None else (start_tick + 100)
        while replay_engine.state.world.tick < target:
            result = replay_engine.tick()
            replay_events.extend([dataclasses.asdict(e) for e in result.events])
            replay_metrics.append(dataclasses.asdict(result.metrics))

        return ReplayResponse(
            final_tick=replay_engine.state.world.tick,
            state=dataclasses.asdict(replay_engine.state),
            metrics=replay_metrics,
            events=replay_events,
        )

    return r
```

- [ ] **Step 5: Implement `server/main.py`**

```python
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from simulation.config import SimConfig
from simulation.models.world import build_world
from simulation.models.agent import spawn_agents, Inventory
from simulation.market import Market
from simulation.models.state import SimulationState
from simulation.engine import SimulationEngine
from server.ws import SimulationManager
from server.routes import _make_router


def create_app(config: SimConfig | None = None) -> FastAPI:
    config = config or SimConfig()
    world = build_world(config)
    agents = spawn_agents(config, world)
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    state = SimulationState(world=world, agents=agents, market=market)
    engine = SimulationEngine(config, state)
    manager = SimulationManager(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if config.tick_rate_hz > 0:
            await manager.start()
        yield
        await manager.stop()

    app = FastAPI(lifespan=lifespan)
    app.include_router(_make_router(manager))

    frontend = Path("frontend")
    if frontend.exists():
        app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
```

- [ ] **Step 6: Run server tests**

```bash
pytest tests/server/test_routes.py -v
```

Expected: 5 passed.

- [ ] **Step 7: Run full suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 8: Manual smoke test**

```bash
python server/main.py
```

Open `http://localhost:8000/state` — should return JSON with simulation state.
Open `http://localhost:8000/docs` — FastAPI auto-docs should show all endpoints.

- [ ] **Step 9: Commit**

```bash
git add server/ tests/server/
git commit -m "feat: FastAPI server — WebSocket manager, REST endpoints, lifespan"
```

---

## Chunk 6: Frontend

### Task 19: `index.html` — shell and layout

**Files:**
- Create: `frontend/index.html`

- [ ] **Step 1: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Isle of Genesis</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0d1117; color: #c9d1d9; font-family: monospace; height: 100vh; display: flex; flex-direction: column; }

    #toolbar {
      display: flex; align-items: center; gap: 12px;
      padding: 8px 16px; background: #161b22; border-bottom: 1px solid #30363d;
      flex-shrink: 0;
    }
    #toolbar h1 { font-size: 0.9rem; color: #58a6ff; margin-right: 8px; }
    #toolbar button {
      background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
      padding: 4px 10px; cursor: pointer; font-family: monospace; font-size: 0.8rem;
    }
    #toolbar button:hover { background: #30363d; }
    #tick-display { font-size: 0.8rem; color: #8b949e; margin-left: auto; }

    #main {
      display: flex; flex: 1; overflow: hidden;
    }
    #canvas-container {
      flex: 1; display: flex; align-items: center; justify-content: center;
      background: #0d1117; overflow: hidden;
    }
    canvas { display: block; }

    #right-panel {
      width: 280px; flex-shrink: 0; display: flex; flex-direction: column;
      border-left: 1px solid #30363d; background: #161b22;
    }
    #metrics-panel {
      flex: 1; padding: 10px; border-bottom: 1px solid #30363d; overflow: hidden;
    }
    #metrics-panel h2 { font-size: 0.75rem; color: #58a6ff; margin-bottom: 8px; }
    #feed-panel { flex: 1; padding: 10px; overflow: hidden; display: flex; flex-direction: column; }
    #feed-panel h2 { font-size: 0.75rem; color: #58a6ff; margin-bottom: 8px; }
    #feed-list { flex: 1; overflow-y: auto; font-size: 0.7rem; line-height: 1.5; }
    .feed-entry { border-bottom: 1px solid #21262d; padding: 2px 0; }
    .feed-trade { color: #3fb950; }
    .feed-starved { color: #f85149; }
    .feed-migrated { color: #d2a8ff; }
    .feed-produced { color: #8b949e; }

    #agent-info {
      padding: 8px 16px; background: #0d1117; border-top: 1px solid #30363d;
      font-size: 0.72rem; color: #8b949e; flex-shrink: 0; min-height: 48px;
    }

    label { font-size: 0.75rem; color: #8b949e; }
    input[type=range] { width: 80px; }
    select { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; font-size: 0.75rem; padding: 2px; }
  </style>
</head>
<body>
  <div id="toolbar">
    <h1>Isle of Genesis</h1>
    <button id="btn-pause">Pause</button>
    <button id="btn-step">Step</button>
    <button id="btn-reset">Reset</button>
    <label>Speed <input type="range" id="speed" min="0.5" max="10" step="0.5" value="2"></label>
    <span id="speed-label">2 Hz</span>
    <select id="snapshot-select"><option value="">— replay —</option></select>
    <button id="btn-replay">Replay</button>
    <span id="tick-display">Tick: 0</span>
  </div>

  <div id="main">
    <div id="canvas-container">
      <canvas id="world-canvas"></canvas>
    </div>
    <div id="right-panel">
      <div id="metrics-panel">
        <h2>Metrics</h2>
        <div id="charts-container"></div>
      </div>
      <div id="feed-panel">
        <h2>Events</h2>
        <div id="feed-list"></div>
      </div>
    </div>
  </div>
  <div id="agent-info">Click an agent to inspect</div>

  <script src="canvas.js"></script>
  <script src="feed.js"></script>
  <script src="charts.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify it renders**

Start the server and open `http://localhost:8000`. Should display the dark shell with toolbar and panels (canvas empty, no WebSocket yet).

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: frontend shell — layout, toolbar, panels"
```

---

### Task 20: `canvas.js` — grid and agent renderer

**Files:**
- Create: `frontend/canvas.js`

- [ ] **Step 1: Create `frontend/canvas.js`**

```javascript
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/canvas.js
git commit -m "feat: canvas.js — grid tile renderer and agent dots"
```

---

### Task 21: `feed.js` — event feed panel

**Files:**
- Create: `frontend/feed.js`

- [ ] **Step 1: Create `frontend/feed.js`**

```javascript
// feed.js — scrolling event feed
const MAX_FEED_ENTRIES = 100;
const EVENT_CLASS = {
  trade_completed:   "feed-trade",
  trade_failed:      "feed-trade",
  agent_starved:     "feed-starved",
  agent_migrated_in: "feed-migrated",
  resource_produced: "feed-produced",
};
const EVENT_ICON = {
  trade_completed:   "⚡",
  trade_failed:      "✗",
  agent_starved:     "💀",
  agent_migrated_in: "→",
  resource_produced: "·",
};

function appendEvents(events, tick) {
  const list = document.getElementById("feed-list");
  for (const e of events) {
    if (e.event_type === "resource_produced") continue; // too noisy
    const div = document.createElement("div");
    div.className = "feed-entry " + (EVENT_CLASS[e.event_type] || "");
    const icon = EVENT_ICON[e.event_type] || "?";
    div.textContent = `[${tick}] ${icon} ${e.event_type} ${e.actors.join(",")}`;
    list.prepend(div);
  }
  // cap DOM entries
  while (list.children.length > MAX_FEED_ENTRIES) {
    list.removeChild(list.lastChild);
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/feed.js
git commit -m "feat: feed.js — scrolling color-coded event feed"
```

---

### Task 22: `charts.js` — SVG sparklines

**Files:**
- Create: `frontend/charts.js`

- [ ] **Step 1: Create `frontend/charts.js`**

```javascript
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/charts.js
git commit -m "feat: charts.js — SVG sparklines for metrics history"
```

---

### Task 23: `app.js` — WebSocket client and controls

**Files:**
- Create: `frontend/app.js`

- [ ] **Step 1: Create `frontend/app.js`**

```javascript
// app.js — WebSocket client, control bar, envelope dispatch
let ws, paused = false, latestState = null;

function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);
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
      latestState = { agents: result.agents, market: result.market };
      renderState(latestState);
    }
    if (result.events) appendEvents(result.events, result.tick);
    if (result.metrics) updateCharts(result.metrics);
    document.getElementById("tick-display").textContent = `Tick: ${result.tick}`;
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
  document.getElementById("feed-list").innerHTML = "";
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
  document.getElementById("tick-display").textContent = `Tick: ${data.final_tick} (replay)`;
});

// init
initCanvas();
connect();
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app.js
git commit -m "feat: app.js — WebSocket client, control bar, replay integration"
```

---

### Task 24: End-to-end smoke test

- [ ] **Step 1: Start the server**

```bash
python server/main.py
```

- [ ] **Step 2: Open browser at `http://localhost:8000`**

Verify:
- Grid renders with colored tiles
- Agent dots appear and move each tick
- Event feed shows trade/production events
- Metrics sparklines update
- Pause/Resume/Step buttons work
- Speed slider changes tick rate

- [ ] **Step 3: Run full test suite one final time**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Final commit**

```bash
git add frontend/app.js frontend/canvas.js frontend/feed.js frontend/charts.js frontend/index.html
git commit -m "feat: complete Isle of Genesis v1 — simulation + API + frontend"
```
