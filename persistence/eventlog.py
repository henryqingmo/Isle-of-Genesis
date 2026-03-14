from __future__ import annotations
import json
import dataclasses
from pathlib import Path
from simulation.events import Event


def append_event(event: Event, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(json.dumps(dataclasses.asdict(event)) + "\n")


def read_events(
    log_path: Path,
    from_tick: int = 0,
    to_tick: int | None = None,
    event_type: str | None = None,
) -> list[Event]:
    if not log_path.exists():
        return []
    events = []
    with log_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data["tick"] < from_tick:
                continue
            if to_tick is not None and data["tick"] > to_tick:
                continue
            if event_type is not None and data["event_type"] != event_type:
                continue
            events.append(Event(**data))
    return events
