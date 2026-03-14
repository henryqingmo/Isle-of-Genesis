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
