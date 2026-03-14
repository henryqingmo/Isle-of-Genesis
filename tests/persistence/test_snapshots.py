import random
from pathlib import Path
from simulation.config import SimConfig
from simulation.models.world import build_world
from simulation.models.agent import spawn_agents, Inventory
from simulation.market import Market
from simulation.models.state import SimulationState
from persistence.snapshots import save_snapshot, load_snapshot, list_snapshots

def make_state():
    config = SimConfig(seed=42, num_agents=3, grid_size=5)
    world = build_world(config)
    agents = spawn_agents(config, world)
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    return SimulationState(world=world, agents=agents, market=market)

def test_save_snapshot_creates_file(tmp_path):
    state = make_state()
    rng = random.Random(42)
    save_snapshot(state, tick=50, rng=rng, snapshot_dir=tmp_path)
    files = list(tmp_path.glob("tick_*.json"))
    assert len(files) == 1

def test_load_snapshot_restores_state(tmp_path):
    state = make_state()
    rng = random.Random(42)
    save_snapshot(state, tick=50, rng=rng, snapshot_dir=tmp_path)
    restored_state, restored_rng = load_snapshot("tick_0050", snapshot_dir=tmp_path)
    assert restored_state.world.tick == state.world.tick
    assert len(restored_state.agents) == len(state.agents)
    assert restored_state.agents[0].id == state.agents[0].id

def test_load_snapshot_restores_rng_state(tmp_path):
    state = make_state()
    rng = random.Random(99)
    rng.random()  # advance state
    save_snapshot(state, tick=10, rng=rng, snapshot_dir=tmp_path)
    _, restored_rng = load_snapshot("tick_0010", snapshot_dir=tmp_path)
    # both RNGs should produce identical sequences
    assert rng.random() == restored_rng.random()

def test_list_snapshots(tmp_path):
    state = make_state()
    rng = random.Random(1)
    save_snapshot(state, tick=50, rng=rng, snapshot_dir=tmp_path)
    save_snapshot(state, tick=100, rng=rng, snapshot_dir=tmp_path)
    entries = list_snapshots(tmp_path)
    assert len(entries) == 2
    assert entries[0]["snapshot_id"] == "tick_0050"
