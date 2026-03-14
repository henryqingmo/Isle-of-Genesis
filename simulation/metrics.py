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
