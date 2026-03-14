from simulation.market import Market
from simulation.models.agent import Inventory

from simulation.market import Market, reset_tick, settle, update_prices
from simulation.models.agent import Agent, Inventory
from simulation.config import SimConfig

def make_agent(id_, wealth, food=0.0):
    return Agent(id=id_, location=(0,0), profession="farmer",
                 wealth=wealth, energy=1.0, hunger=0.0,
                 alive=True, respawn_tick=None,
                 inventory=Inventory(food=food))

def make_market(food_price=1.0):
    return Market(
        prices=Inventory(food=food_price, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )

def test_reset_tick_clears_supply_demand():
    m = make_market()
    m.supply.food = 10.0
    m.demand.food = 5.0
    m.trade_volume = 3.0
    reset_tick(m)
    assert m.supply.food == 0.0
    assert m.demand.food == 0.0
    assert m.trade_volume == 0.0

def test_settle_supply_exceeds_demand_all_buyers_fill():
    """When supply > demand, all buyers fill in full."""
    market = make_market(food_price=2.0)
    seller = make_agent("seller", wealth=0.0, food=10.0)
    buyer = make_agent("buyer", wealth=20.0, food=0.0)

    sell_orders = [{"agent_id": "seller", "resource": "food", "quantity": 5.0}]
    buy_orders  = [{"agent_id": "buyer",  "resource": "food", "quantity": 3.0}]
    agents = {"seller": seller, "buyer": buyer}

    events = settle(market, sell_orders, buy_orders, agents, tick=1)

    assert buyer.inventory.food == 3.0
    assert buyer.wealth == 20.0 - 3.0 * 2.0
    assert any(e.event_type == "trade_completed" for e in events)

def test_settle_demand_exceeds_supply_buyers_rationed():
    """When demand > supply, buyers get proportional fills."""
    market = make_market(food_price=1.0)
    seller = make_agent("seller", wealth=0.0, food=10.0)
    buyer1 = make_agent("b1", wealth=20.0)
    buyer2 = make_agent("b2", wealth=20.0)

    sell_orders = [{"agent_id": "seller", "resource": "food", "quantity": 4.0}]
    buy_orders  = [{"agent_id": "b1", "resource": "food", "quantity": 4.0},
                   {"agent_id": "b2", "resource": "food", "quantity": 4.0}]
    agents = {"seller": seller, "b1": buyer1, "b2": buyer2}

    events = settle(market, sell_orders, buy_orders, agents, tick=1)

    assert abs(buyer1.inventory.food - 2.0) < 1e-9
    assert abs(buyer2.inventory.food - 2.0) < 1e-9

def test_update_prices_rises_when_demand_exceeds_supply():
    market = make_market(food_price=1.0)
    market.supply.food = 2.0
    market.demand.food = 4.0
    config = SimConfig(price_damping=0.1, price_min=0.1, price_max=50.0)
    update_prices(market, config)
    assert market.prices.food > 1.0

def test_update_prices_clamped_to_max():
    market = make_market(food_price=49.0)
    market.supply.food = 0.0001
    market.demand.food = 1000.0
    config = SimConfig(price_damping=0.1, price_min=0.1, price_max=50.0)
    update_prices(market, config)
    assert market.prices.food <= 50.0

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
