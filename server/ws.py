from __future__ import annotations
import asyncio
import dataclasses
import json
from typing import Literal
from fastapi import WebSocket
from simulation.engine import SimulationEngine
from simulation.models.state import TickResult


EngineStatus = Literal["running", "paused"]


class SimulationManager:
    def __init__(self, engine: SimulationEngine) -> None:
        self.engine = engine
        self.status: EngineStatus = "running"
        self._clients: list[WebSocket] = []
        self._task: asyncio.Task | None = None
        self._metrics_history: list[dict] = []

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.remove(ws)

    async def handle_message(self, msg: dict) -> None:
        mtype = msg.get("type")
        if mtype == "pause":
            self.status = "paused"
        elif mtype == "resume":
            self.status = "running"
        elif mtype == "step" and self.status == "paused":
            result = self.engine.tick()
            self._record(result)
            await self._broadcast({"type": "tick", "payload": self._tick_payload(result)})
        elif mtype == "set_speed":
            self.engine.config.tick_rate_hz = float(msg.get("hz", 2.0))
        elif mtype == "reset":
            from simulation.models.world import build_world
            from simulation.models.agent import spawn_agents, Inventory
            from simulation.market import Market
            from simulation.models.state import SimulationState
            config = self.engine.config
            world = build_world(config)
            agents = spawn_agents(config, world)
            market = Market(
                prices=Inventory(food=1.0, wood=1.0, ore=1.0),
                supply=Inventory(), demand=Inventory(), trade_volume=0.0,
            )
            self.engine.state = SimulationState(world=world, agents=agents, market=market)
            self.status = "running"
            self._metrics_history.clear()

        await self._broadcast_status()

    async def _run_loop(self) -> None:
        while True:
            hz = self.engine.config.tick_rate_hz
            sleep = 1.0 / hz if hz > 0 else 1.0
            await asyncio.sleep(sleep)
            if self.status == "running":
                result = self.engine.tick()
                self._record(result)
                await self._broadcast({"type": "tick", "payload": self._tick_payload(result)})

    def _tick_payload(self, result: TickResult) -> dict:
        """Include agent + market state alongside TickResult fields so the frontend
        can re-render the canvas on every tick without a separate /state fetch."""
        d = dataclasses.asdict(result)
        d["agents"] = dataclasses.asdict(self.engine.state)["agents"]
        d["market"] = dataclasses.asdict(self.engine.state.market)
        d["world"] = dataclasses.asdict(self.engine.state.world)
        return d

    def _record(self, result: TickResult) -> None:
        self._metrics_history.append(dataclasses.asdict(result.metrics))

    async def _broadcast(self, payload: dict) -> None:
        dead = []
        for ws in self._clients:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.remove(ws)

    async def _broadcast_status(self) -> None:
        await self._broadcast({
            "type": "status",
            "payload": {"status": self.status, "tick": self.engine.state.world.tick},
        })
