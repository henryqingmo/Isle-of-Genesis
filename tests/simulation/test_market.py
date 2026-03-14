from simulation.market import Market
from simulation.models.agent import Inventory

def test_market_default_prices():
    m = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(),
        demand=Inventory(),
        trade_volume=0.0,
    )
    assert m.prices.food == 1.0
    assert m.trade_volume == 0.0

def test_market_supply_demand_start_zero():
    m = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(),
        demand=Inventory(),
        trade_volume=0.0,
    )
    assert m.supply.food == 0.0
    assert m.demand.wood == 0.0
