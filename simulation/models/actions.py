from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Action:
    agent_id: str
    action_type: Literal["move", "produce", "trade", "rest"]
    payload: dict = field(default_factory=dict)
