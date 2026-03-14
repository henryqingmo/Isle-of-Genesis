from simulation.models.agent import Inventory, Agent

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
