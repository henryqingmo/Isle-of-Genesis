from __future__ import annotations
from dataclasses import dataclass
from simulation.models.agent import Inventory


@dataclass
class Market:
    prices: Inventory
    supply: Inventory
    demand: Inventory
    trade_volume: float
