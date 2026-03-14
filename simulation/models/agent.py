from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, TYPE_CHECKING
if TYPE_CHECKING:
    from simulation.models.world import World
    from simulation.config import SimConfig


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


import random as _random

_PROFESSIONS = ["farmer", "lumberjack", "miner", "trader"]

def fresh_settler(rng: "_random.Random", world: "World", tick: int) -> Agent:
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
