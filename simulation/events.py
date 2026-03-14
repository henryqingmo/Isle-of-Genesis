from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import uuid

# Event type constants
TRADE_COMPLETED   = "trade_completed"
TRADE_FAILED      = "trade_failed"
RESOURCE_PRODUCED = "resource_produced"
AGENT_STARVED     = "agent_starved"
AGENT_MIGRATED_IN = "agent_migrated_in"


@dataclass
class Event:
    tick: int
    event_type: str
    actors: list[str]
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    visibility: Literal["public", "private", "system"] = "public"
