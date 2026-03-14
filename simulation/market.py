from __future__ import annotations
from dataclasses import dataclass
from simulation.models.agent import Inventory
from simulation.events import Event, TRADE_COMPLETED, TRADE_FAILED


@dataclass
class Market:
    prices: Inventory
    supply: Inventory
    demand: Inventory
    trade_volume: float


def reset_tick(market: Market) -> None:
    market.supply = Inventory()
    market.demand = Inventory()
    market.trade_volume = 0.0


def settle(
    market: Market,
    sell_orders: list[dict],
    buy_orders: list[dict],
    agents: dict,
    tick: int,
) -> list[Event]:
    events = []
    for resource in ("food", "wood", "ore"):
        sells = [o for o in sell_orders if o["resource"] == resource]
        buys  = [o for o in buy_orders  if o["resource"] == resource]
        total_supply = sum(o["quantity"] for o in sells)
        total_demand = sum(o["quantity"] for o in buys)
        price = getattr(market.prices, resource)

        setattr(market.supply, resource, getattr(market.supply, resource) + total_supply)
        setattr(market.demand, resource, getattr(market.demand, resource) + total_demand)

        if total_demand == 0 or total_supply == 0:
            continue

        if total_demand <= total_supply:
            fill_ratio_sellers = total_demand / total_supply if total_supply > 0 else 0.0
            for o in buys:
                buyer = agents[o["agent_id"]]
                qty = o["quantity"]
                cost = qty * price
                if cost > buyer.wealth + 1e-9:
                    events.append(Event(
                        tick=tick, event_type=TRADE_FAILED,
                        actors=[o["agent_id"]],
                        payload={"resource": resource, "reason": "insufficient_funds"},
                    ))
                    continue
                buyer.wealth -= cost
                setattr(buyer.inventory, resource,
                        getattr(buyer.inventory, resource) + qty)
                market.trade_volume += qty
            for o in sells:
                seller = agents[o["agent_id"]]
                qty_sold = min(o["quantity"] * fill_ratio_sellers,
                               getattr(seller.inventory, resource))
                revenue = qty_sold * price
                seller.wealth += revenue
                setattr(seller.inventory, resource,
                        getattr(seller.inventory, resource) - qty_sold)
                events.append(Event(
                    tick=tick, event_type=TRADE_COMPLETED,
                    actors=[o["agent_id"]],
                    payload={"resource": resource, "qty": qty_sold, "price": price},
                ))
        else:
            fill_ratio = total_supply / total_demand
            for o in buys:
                buyer = agents[o["agent_id"]]
                qty = o["quantity"] * fill_ratio
                cost = qty * price
                if cost > buyer.wealth + 1e-9:
                    events.append(Event(
                        tick=tick, event_type=TRADE_FAILED,
                        actors=[o["agent_id"]],
                        payload={"resource": resource, "reason": "insufficient_funds"},
                    ))
                    continue
                buyer.wealth -= cost
                setattr(buyer.inventory, resource,
                        getattr(buyer.inventory, resource) + qty)
                market.trade_volume += qty
            for o in sells:
                seller = agents[o["agent_id"]]
                qty_sold = min(o["quantity"], getattr(seller.inventory, resource))
                revenue = qty_sold * price
                seller.wealth += revenue
                setattr(seller.inventory, resource,
                        getattr(seller.inventory, resource) - qty_sold)
                events.append(Event(
                    tick=tick, event_type=TRADE_COMPLETED,
                    actors=[o["agent_id"]],
                    payload={"resource": resource, "qty": qty_sold, "price": price},
                ))
    return events


def update_prices(market: Market, config) -> None:
    for resource in ("food", "wood", "ore"):
        supply = getattr(market.supply, resource)
        demand = getattr(market.demand, resource)
        price  = getattr(market.prices, resource)
        ratio  = demand / max(supply, 0.001)
        new_price = price * (1 + config.price_damping * (ratio - 1))
        new_price = max(config.price_min, min(config.price_max, new_price))
        setattr(market.prices, resource, new_price)
