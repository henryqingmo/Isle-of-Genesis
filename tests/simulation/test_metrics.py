from simulation.metrics import net_worth, gini, TickMetrics
from simulation.models.agent import Agent, Inventory

def make_agent(wealth, food=0.0, wood=0.0, ore=0.0):
    return Agent(
        id="x", location=(0,0), profession="farmer",
        wealth=wealth, energy=1.0, hunger=0.0,
        alive=True, respawn_tick=None,
        inventory=Inventory(food=food, wood=wood, ore=ore),
    )

def test_net_worth_cash_only():
    a = make_agent(wealth=10.0)
    prices = Inventory(food=1.0, wood=1.0, ore=1.0)
    assert net_worth(a, prices) == 10.0

def test_net_worth_includes_inventory():
    a = make_agent(wealth=5.0, food=3.0, wood=2.0, ore=1.0)
    prices = Inventory(food=2.0, wood=1.0, ore=4.0)
    # 5 + 3*2 + 2*1 + 1*4 = 5 + 6 + 2 + 4 = 17
    assert net_worth(a, prices) == 17.0

def test_gini_equal_wealth_is_zero():
    assert gini([10.0, 10.0, 10.0]) == 0.0

def test_gini_max_inequality():
    result = gini([0.0, 0.0, 0.0, 100.0])
    assert result > 0.7

def test_gini_zero_total_wealth():
    assert gini([0.0, 0.0, 0.0]) == 0.0

def test_gini_two_agents():
    assert abs(gini([0.0, 100.0]) - 0.5) < 1e-9
