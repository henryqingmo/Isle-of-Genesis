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

def test_snapshot_path_none_on_non_snapshot_ticks():
    """snapshot_path is None on tick 0, non-None on tick matching snapshot_interval."""
    config = SimConfig(seed=42, num_agents=3, grid_size=5, snapshot_interval=2)
    state, _ = make_state(config)
    engine = SimulationEngine(config, state)

    r0 = engine.tick()  # tick 0 — never snapshotted (tick > 0 is False)
    assert r0.snapshot_path is None

    r1 = engine.tick()  # tick 1 — not a snapshot tick
    assert r1.snapshot_path is None

    r2 = engine.tick()  # tick 2 — matches interval (2 % 2 == 0 and 2 > 0)
    assert r2.snapshot_path is not None

    r3 = engine.tick()  # tick 3 — not a snapshot tick
    assert r3.snapshot_path is None

def test_metrics_match_alive_agents():
    """TickMetrics.population and total_wealth are computed correctly from alive agents."""
    from simulation.metrics import net_worth
    state, config = make_state()
    engine = SimulationEngine(config, state)
    result = engine.tick()

    alive = [a for a in state.agents if a.alive]
    assert result.metrics.population == len(alive)
    expected_wealth = sum(net_worth(a, state.market.prices) for a in alive)
    assert abs(result.metrics.total_wealth - expected_wealth) < 1e-6

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
