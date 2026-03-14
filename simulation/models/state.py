from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from simulation.models.world import World
from simulation.models.agent import Agent
from simulation.market import Market
from simulation.events import Event

if TYPE_CHECKING:
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
    metrics: "TickMetrics"   # resolved at runtime once metrics.py exists
    snapshot_path: str | None = None
