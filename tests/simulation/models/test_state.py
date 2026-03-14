from unittest.mock import MagicMock
from simulation.models.world import Tile, World
from simulation.models.agent import Agent, Inventory
from simulation.market import Market
from simulation.models.state import SimulationState, TickResult
from simulation.models.actions import Action

def make_world():
    grid = [[Tile(x=x, y=y, tile_type="town", resource_yield=0.0)
             for x in range(3)] for y in range(3)]
    return World(grid=grid)

def make_market():
    return Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )

def test_simulation_state_holds_components():
    state = SimulationState(
        world=make_world(),
        agents=[],
        market=make_market(),
    )
    assert state.world.tick == 0
    assert state.agents == []

def test_action_has_empty_payload_by_default():
    a = Action(agent_id="a01", action_type="rest")
    assert a.payload == {}

def test_tick_result_snapshot_path_defaults_none():
    metrics_stub = MagicMock()
    result = TickResult(tick=0, events=[], metrics=metrics_stub)
    assert result.snapshot_path is None
