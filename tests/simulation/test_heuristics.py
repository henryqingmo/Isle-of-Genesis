from simulation.heuristics import build_context, AgentContext
from simulation.models.agent import Agent, Inventory
from simulation.models.world import Tile, World
from simulation.market import Market
from simulation.models.state import SimulationState

def make_tile(x, y, tile_type="farm"):
    return Tile(x=x, y=y, tile_type=tile_type, resource_yield=1.0)

def make_world_3x3(center_type="market"):
    grid = [[make_tile(x, y) for x in range(3)] for y in range(3)]
    grid[1][1] = make_tile(1, 1, center_type)
    return World(grid=grid)

def make_agent(location=(1,1), hunger=0.0, food=5.0):
    return Agent(id="a1", location=location, profession="farmer",
                 wealth=10.0, energy=1.0, hunger=hunger, alive=True,
                 respawn_tick=None, inventory=Inventory(food=food))

def make_state(agent, world):
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    return SimulationState(world=world, agents=[agent], market=market)

def test_context_at_market_tile():
    world = make_world_3x3("market")
    agent = make_agent(location=(1,1))
    state = make_state(agent, world)
    ctx = build_context(agent, state)
    assert ctx.at_market is True

def test_context_not_at_market():
    world = make_world_3x3("farm")
    agent = make_agent(location=(1,1))
    state = make_state(agent, world)
    ctx = build_context(agent, state)
    assert ctx.at_market is False

def test_context_food_need_high_when_hungry():
    world = make_world_3x3()
    agent = make_agent(hunger=0.9, food=0.0)
    state = make_state(agent, world)
    ctx = build_context(agent, state)
    assert ctx.food_need > 0.5

def test_context_nearest_market_found():
    world = make_world_3x3("farm")
    world.grid[2][2] = make_tile(2, 2, "market")
    agent = make_agent(location=(0,0))
    state = make_state(agent, world)
    ctx = build_context(agent, state)
    assert ctx.nearest_market == (2, 2)

import random
from simulation.heuristics import decide
from simulation.config import SimConfig

def make_full_state(agent, world=None):
    if world is None:
        world = make_world_3x3()
    market = Market(
        prices=Inventory(food=1.5, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    return SimulationState(world=world, agents=[agent], market=market)

def test_decide_returns_two_actions():
    agent = make_agent()
    state = make_full_state(agent)
    actions = decide(agent, state, SimConfig(), random.Random(1))
    assert len(actions) == 2

def test_decide_starving_agent_moves_to_market():
    """A starving agent with no food should try to reach market."""
    agent = make_agent(hunger=0.9, food=0.0)
    world = make_world_3x3("farm")
    world.grid[0][0] = make_tile(0, 0, "market")
    state = make_full_state(agent, world)
    actions = decide(agent, state, SimConfig(), random.Random(1))
    assert actions[0].action_type == "move"

def test_decide_farmer_on_farm_produces():
    """A farmer on a farm tile with energy should produce."""
    world = make_world_3x3("farm")
    agent = Agent(id="a1", location=(1,1), profession="farmer",
                  wealth=10.0, energy=1.0, hunger=0.0, alive=True,
                  respawn_tick=None, inventory=Inventory(food=5.0))
    state = make_full_state(agent, world)
    actions = decide(agent, state, SimConfig(), random.Random(1))
    action_types = [a.action_type for a in actions]
    assert "produce" in action_types

def test_decide_at_market_with_surplus_sells():
    """Agent at market with surplus food should sell."""
    world = make_world_3x3("market")
    agent = Agent(id="a1", location=(1,1), profession="trader",
                  wealth=10.0, energy=1.0, hunger=0.0, alive=True,
                  respawn_tick=None, inventory=Inventory(food=8.0))
    state = make_full_state(agent, world)
    actions = decide(agent, state, SimConfig(), random.Random(1))
    action_types = [a.action_type for a in actions]
    assert "trade" in action_types
