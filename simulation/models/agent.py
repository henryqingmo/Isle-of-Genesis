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
