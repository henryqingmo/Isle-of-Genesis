from __future__ import annotations
import random
import dataclasses
from simulation.config import SimConfig
from simulation.models.state import SimulationState, TickResult
from simulation.models.agent import Agent, Inventory, fresh_settler
from simulation.market import reset_tick, settle, update_prices
from simulation.events import Event, AGENT_STARVED, AGENT_MIGRATED_IN, RESOURCE_PRODUCED
from simulation.metrics import TickMetrics, net_worth, gini
from simulation.heuristics import decide


class SimulationEngine:
    def __init__(self, config: SimConfig, state: SimulationState) -> None:
        self.config = config
        self.state = state
        self.rng = random.Random(config.seed)
        self._last_events: list[Event] = []

    def tick(self) -> TickResult:
        tick = self.state.world.tick
        events: list[Event] = []

        reset_tick(self.state.market)

        sell_orders: list[dict] = []
        buy_orders: list[dict] = []
        alive_agents = [a for a in self.state.agents if a.alive]

        for agent in alive_agents:
            actions = decide(agent, self.state, self.config, self.rng)
            for action in actions:
                self._execute_action(agent, action, sell_orders, buy_orders, events, tick)

        trade_events = settle(
            self.state.market, sell_orders, buy_orders,
            {a.id: a for a in self.state.agents}, tick,
        )
        events.extend(trade_events)

        self._apply_upkeep_and_survival(alive_agents, events, tick)
        update_prices(self.state.market, self.config)
        self._process_respawns(events, tick)

        metrics = self._compute_metrics(tick)
        snapshot_path = self._maybe_snapshot(tick)

        self._last_events = events
        self.state.world.tick += 1
        return TickResult(tick=tick, events=events, metrics=metrics, snapshot_path=snapshot_path)

    def _execute_action(self, agent: Agent, action, sell_orders, buy_orders, events, tick):
        atype = action.action_type
        payload = action.payload

        if atype == "move":
            dx, dy = payload.get("dx", 0), payload.get("dy", 0)
            x, y = agent.location
            nx = max(0, min(self.config.grid_size - 1, x + dx))
            ny = max(0, min(self.config.grid_size - 1, y + dy))
            agent.location = (nx, ny)

        elif atype == "produce":
            tile = self.state.world.grid[agent.location[1]][agent.location[0]]
            base = self.config.base_production.get(agent.profession, {})
            for resource, base_rate in base.items():
                qty = base_rate * agent.skill * agent.energy * tile.resource_yield
                setattr(agent.inventory, resource,
                        getattr(agent.inventory, resource) + qty)
                events.append(Event(
                    tick=tick, event_type=RESOURCE_PRODUCED,
                    actors=[agent.id],
                    payload={"resource": resource, "qty": qty},
                ))

        elif atype == "trade":
            side = payload.get("side", "sell")
            resource = payload.get("resource", "food")
            quantity = payload.get("quantity", 0.0)
            if side == "sell":
                sell_orders.append({"agent_id": agent.id, "resource": resource, "quantity": quantity})
            else:
                buy_orders.append({"agent_id": agent.id, "resource": resource, "quantity": quantity})

        elif atype == "rest":
            agent.energy = min(1.0, agent.energy + 0.3)

    def _apply_upkeep_and_survival(self, agents: list[Agent], events: list[Event], tick: int):
        for agent in agents:
            if agent.inventory.food >= self.config.food_per_tick:
                agent.inventory.food -= self.config.food_per_tick
                agent.hunger = max(0.0, agent.hunger - 0.2)
                agent.consecutive_starving = 0
            else:
                agent.hunger = min(1.0, agent.hunger + 0.25)
                if agent.hunger >= 1.0:
                    agent.consecutive_starving += 1
                if agent.consecutive_starving >= self.config.starvation_death_ticks:
                    agent.alive = False
                    delay = self.rng.randint(*self.config.respawn_delay)
                    agent.respawn_tick = tick + delay
                    events.append(Event(
                        tick=tick, event_type=AGENT_STARVED,
                        actors=[agent.id], payload={},
                    ))
            agent.energy = max(0.1, agent.energy - 0.05)

    def _process_respawns(self, events: list[Event], tick: int):
        for i, agent in enumerate(self.state.agents):
            if not agent.alive and agent.respawn_tick is not None and tick >= agent.respawn_tick:
                new_agent = fresh_settler(self.rng, self.state.world, tick)
                self.state.agents[i] = new_agent
                events.append(Event(
                    tick=tick, event_type=AGENT_MIGRATED_IN,
                    actors=[new_agent.id], payload={},
                ))

    def _compute_metrics(self, tick: int) -> TickMetrics:
        alive = [a for a in self.state.agents if a.alive]
        nw = [net_worth(a, self.state.market.prices) for a in alive]
        return TickMetrics(
            tick=tick,
            population=len(alive),
            total_wealth=sum(nw),
            gini_coefficient=gini(nw),
            total_food_inventory=sum(a.inventory.food for a in alive),
            prices=dataclasses.replace(self.state.market.prices),
            trade_volume=self.state.market.trade_volume,
        )

    def _maybe_snapshot(self, tick: int) -> str | None:
        if tick % self.config.snapshot_interval == 0 and tick > 0:
            return f"tick_{tick:04d}"
        return None
