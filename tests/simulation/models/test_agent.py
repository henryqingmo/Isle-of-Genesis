from simulation.models.agent import Inventory, Agent

from simulation.config import SimConfig
from simulation.models.world import build_world
from simulation.models.agent import spawn_agents, fresh_settler

def test_spawn_agents_count():
    config = SimConfig(num_agents=30, seed=42, grid_size=20)
    world = build_world(config)
    agents = spawn_agents(config, world)
    assert len(agents) == 30

def test_spawn_agents_all_alive():
    config = SimConfig(num_agents=30, seed=42, grid_size=20)
    world = build_world(config)
    agents = spawn_agents(config, world)
    assert all(a.alive for a in agents)

def test_spawn_agents_on_town_tiles():
    config = SimConfig(num_agents=10, seed=42, grid_size=20)
    world = build_world(config)
    agents = spawn_agents(config, world)
    town_positions = {(t.x, t.y) for row in world.grid for t in row if t.tile_type == "town"}
    for a in agents:
        assert a.location in town_positions

def test_fresh_settler_minimal_wealth():
    import random
    rng = random.Random(1)
    world = build_world(SimConfig(grid_size=20, seed=1))
    settler = fresh_settler(rng, world, tick=10)
    assert settler.alive is True
    assert settler.wealth < 5.0
    assert settler.hunger == 0.0
    assert settler.respawn_tick is None

def test_inventory_defaults_to_zero():
    inv = Inventory()
    assert inv.food == 0.0
    assert inv.wood == 0.0
    assert inv.ore == 0.0

def test_agent_has_required_fields():
    agent = Agent(
        id="a01",
        location=(0, 0),
        profession="farmer",
        wealth=10.0,
        energy=1.0,
        hunger=0.0,
        alive=True,
        respawn_tick=None,
    )
    assert agent.id == "a01"
    assert agent.inventory.food == 0.0
    assert agent.consecutive_starving == 0
    assert agent.skill == 0.5
    assert agent.risk_aversion == 0.5

def test_agent_profession_values():
    for prof in ("farmer", "lumberjack", "miner", "trader"):
        a = Agent(id="x", location=(0,0), profession=prof,
                  wealth=0, energy=1, hunger=0, alive=True, respawn_tick=None)
        assert a.profession == prof
