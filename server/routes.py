from __future__ import annotations
import dataclasses
from pathlib import Path
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from server.schemas import (
    ControlCommand, ControlResponse, StateResponse,
    ReplayRequest, ReplayResponse,
)
from persistence.snapshots import list_snapshots, load_snapshot
from persistence.eventlog import read_events

SNAPSHOT_DIR = Path("data/snapshots")
LOG_PATH = Path("logs/events.jsonl")


def _make_router(manager):
    r = APIRouter()

    @r.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                msg = await ws.receive_json()
                await manager.handle_message(msg)
        except WebSocketDisconnect:
            manager.disconnect(ws)

    @r.get("/state", response_model=StateResponse)
    async def get_state():
        return StateResponse(
            state=dataclasses.asdict(manager.engine.state),
            status=manager.status,
            tick_rate_hz=manager.engine.config.tick_rate_hz,
            config=dataclasses.asdict(manager.engine.config),
        )

    @r.get("/metrics")
    async def get_metrics(from_tick: int = 0, to_tick: int | None = None):
        history = manager._metrics_history
        if to_tick is not None:
            history = [m for m in history if from_tick <= m["tick"] <= to_tick]
        else:
            history = [m for m in history if m["tick"] >= from_tick]
        return history

    @r.get("/snapshots")
    async def get_snapshots():
        return list_snapshots(SNAPSHOT_DIR)

    @r.get("/events")
    async def get_events(from_tick: int = 0, to_tick: int | None = None, event_type: str | None = None):
        events = read_events(LOG_PATH, from_tick=from_tick, to_tick=to_tick, event_type=event_type)
        return [dataclasses.asdict(e) for e in events]

    @r.post("/control", response_model=ControlResponse)
    async def post_control(cmd: ControlCommand):
        await manager.handle_message({"type": cmd.command})
        return ControlResponse(ok=True, status=manager.status, tick=manager.engine.state.world.tick)

    @r.post("/replay", response_model=ReplayResponse)
    async def post_replay(req: ReplayRequest):
        try:
            state, rng = load_snapshot(req.snapshot_id, SNAPSHOT_DIR)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        from simulation.engine import SimulationEngine
        replay_engine = SimulationEngine(manager.engine.config, state)
        replay_engine.rng = rng
        replay_events = []
        replay_metrics = []
        start_tick = replay_engine.state.world.tick
        target = req.to_tick if req.to_tick is not None else (start_tick + 100)
        while replay_engine.state.world.tick < target:
            result = replay_engine.tick()
            replay_events.extend([dataclasses.asdict(e) for e in result.events])
            replay_metrics.append(dataclasses.asdict(result.metrics))

        return ReplayResponse(
            final_tick=replay_engine.state.world.tick,
            state=dataclasses.asdict(replay_engine.state),
            metrics=replay_metrics,
            events=replay_events,
        )

    return r
