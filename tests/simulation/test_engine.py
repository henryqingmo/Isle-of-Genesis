import random
from simulation.config import SimConfig
from simulation.models.world import build_world
from simulation.models.agent import spawn_agents, Inventory
from simulation.market import Market
from simulation.models.state import SimulationState
from simulation.engine import SimulationEngine

def make_state(config=None):
    config = config or SimConfig(seed=42, num_agents=5, grid_size=10)
    world = build_world(config)
    agents = spawn_agents(config, world)
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    return SimulationState(world=world, agents=agents, market=market), config

def test_tick_increments_world_tick():
    state, config = make_state()
    engine = SimulationEngine(config, state)
    result = engine.tick()
    assert result.tick == 0
    assert state.world.tick == 1

def test_tick_returns_tick_result():
    from simulation.models.state import TickResult
    state, config = make_state()
    engine = SimulationEngine(config, state)
    result = engine.tick()
    assert isinstance(result, TickResult)
    assert result.metrics.population > 0

def test_agent_starves_when_no_food():
    config = SimConfig(seed=1, num_agents=1, grid_size=5,
                       food_per_tick=1.0, starvation_death_ticks=2)
    world = build_world(config)
    agents = spawn_agents(config, world)
    for a in agents:
        a.inventory.food = 0.0
        a.hunger = 1.0
        a.consecutive_starving = 1
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    state = SimulationState(world=world, agents=agents, market=market)
    engine = SimulationEngine(config, state)
    result = engine.tick()
    dead = [a for a in state.agents if not a.alive]
    assert len(dead) == 1
    assert any(e.event_type == "agent_starved" for e in result.events)

def test_respawn_occurs_after_delay():
    config = SimConfig(seed=2, num_agents=1, grid_size=5,
                       starvation_death_ticks=1, respawn_delay=(2, 2))
    world = build_world(config)
    agents = spawn_agents(config, world)
    for a in agents:
        a.inventory.food = 0.0
        a.hunger = 1.0
        a.consecutive_starving = 0
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    state = SimulationState(world=world, agents=agents, market=market)
    engine = SimulationEngine(config, state)
    engine.tick()   # tick 0: dies, respawn_tick = 2
    engine.tick()   # tick 1: still dead
    assert not state.agents[0].alive
    engine.tick()   # tick 2: respawns
    assert state.agents[0].alive
    assert any(e.event_type == "agent_migrated_in"
               for tick_events in [engine._last_events] for e in tick_events)
