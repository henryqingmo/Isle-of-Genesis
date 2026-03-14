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
