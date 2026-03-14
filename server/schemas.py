from __future__ import annotations
from pydantic import BaseModel
from typing import Literal


class ControlCommand(BaseModel):
    command: Literal["pause", "resume", "step", "reset"]

class ControlResponse(BaseModel):
    ok: bool
    status: Literal["running", "paused"]
    tick: int

class StateResponse(BaseModel):
    state: dict          # full SimulationState serialization
    status: Literal["running", "paused"]
    tick_rate_hz: float
    config: dict

class SnapshotEntry(BaseModel):
    snapshot_id: str
    tick: int
    timestamp: float

class ReplayRequest(BaseModel):
    snapshot_id: str
    to_tick: int | None = None

class ReplayResponse(BaseModel):
    final_tick: int
    state: dict
    metrics: list[dict]
    events: list[dict]
