from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import random


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
