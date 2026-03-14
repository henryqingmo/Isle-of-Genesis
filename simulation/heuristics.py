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

    food_inv = agent.inventory.food
    food_need = agent.hunger * 0.7 + max(0.0, (2.0 - food_inv) / 2.0) * 0.3
    food_need = min(1.0, food_need)

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

    if ctx.nearest_profession_tile and ctx.nearest_profession_tile != agent.location:
        move_score = 0.5 + (0.2 if agent.energy > 0.6 else 0.0)
        tx, ty = ctx.nearest_profession_tile
        dx = _sign(tx - agent.location[0])
        dy = _sign(ty - agent.location[1])
        scores.append((Action(agent_id=aid, action_type="move", payload={"dx": dx, "dy": dy}), move_score))

    if ctx.nearest_market and not ctx.at_market:
        mkt_score = 0.4 + (0.3 if ctx.surplus_qty > 2 else 0.0)
        mx, my = ctx.nearest_market
        dx = _sign(mx - agent.location[0])
        dy = _sign(my - agent.location[1])
        scores.append((Action(agent_id=aid, action_type="move", payload={"dx": dx, "dy": dy}), mkt_score))

    prof_bonus = {"farmer": 0.3, "lumberjack": 0.3, "miner": 0.3, "trader": 0.0}
    on_profession_tile = (ctx.current_tile_type == {
        "farmer": "farm", "lumberjack": "forest", "miner": "mine", "trader": "market"
    }.get(agent.profession))
    produce_score = (0.6 * agent.energy * agent.skill - agent.hunger * 0.3
                     + (prof_bonus.get(agent.profession, 0) if on_profession_tile else 0))
    if agent.profession != "trader":
        scores.append((Action(agent_id=aid, action_type="produce"), produce_score))

    if ctx.at_market and ctx.surplus_qty > 1.0:
        sell_score = 0.5
        scores.append((Action(agent_id=aid, action_type="trade", payload={
            "side": "sell", "resource": ctx.surplus_resource, "quantity": ctx.surplus_qty * 0.5,
        }), sell_score))

    if ctx.at_market and agent.hunger > 0.5:
        buy_score = 0.8 - agent.risk_aversion * 0.2
        scores.append((Action(agent_id=aid, action_type="trade", payload={
            "side": "buy", "resource": "food", "quantity": 3.0,
        }), buy_score))

    rest_score = 0.3 + (agent.risk_aversion * 0.4 if agent.energy < 0.3 else 0.0)
    scores.append((Action(agent_id=aid, action_type="rest"), rest_score))

    return scores


def _sign(n: float) -> int:
    return 1 if n > 0 else (-1 if n < 0 else 0)
