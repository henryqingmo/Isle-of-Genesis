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
