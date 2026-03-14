import json
import tempfile
from pathlib import Path
from simulation.events import Event, TRADE_COMPLETED
from persistence.eventlog import append_event, read_events

def make_event(tick, event_type=TRADE_COMPLETED):
    return Event(tick=tick, event_type=event_type, actors=["a01"], payload={"qty": 1})

def test_append_event_creates_file(tmp_path):
    log_path = tmp_path / "events.jsonl"
    e = make_event(tick=1)
    append_event(e, log_path)
    assert log_path.exists()

def test_append_event_valid_json(tmp_path):
    log_path = tmp_path / "events.jsonl"
    append_event(make_event(tick=1), log_path)
    line = log_path.read_text().strip()
    data = json.loads(line)
    assert data["tick"] == 1
    assert data["event_type"] == TRADE_COMPLETED

def test_read_events_returns_all(tmp_path):
    log_path = tmp_path / "events.jsonl"
    for t in range(5):
        append_event(make_event(tick=t), log_path)
    events = read_events(log_path)
    assert len(events) == 5

def test_read_events_filter_by_tick_range(tmp_path):
    log_path = tmp_path / "events.jsonl"
    for t in range(10):
        append_event(make_event(tick=t), log_path)
    events = read_events(log_path, from_tick=3, to_tick=6)
    assert all(3 <= e.tick <= 6 for e in events)
    assert len(events) == 4

def test_read_events_filter_by_type(tmp_path):
    log_path = tmp_path / "events.jsonl"
    append_event(make_event(tick=1, event_type=TRADE_COMPLETED), log_path)
    append_event(make_event(tick=2, event_type="agent_starved"), log_path)
    events = read_events(log_path, event_type=TRADE_COMPLETED)
    assert len(events) == 1
    assert events[0].event_type == TRADE_COMPLETED
