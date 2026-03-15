from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from simulation.config import SimConfig
from simulation.models.world import build_world
from simulation.models.agent import spawn_agents, Inventory
from simulation.market import Market
from simulation.models.state import SimulationState
from simulation.engine import SimulationEngine
from server.ws import SimulationManager
from server.routes import _make_router


def create_app(config: SimConfig | None = None) -> FastAPI:
    config = config or SimConfig()
    world = build_world(config)
    agents = spawn_agents(config, world)
    market = Market(
        prices=Inventory(food=1.0, wood=1.0, ore=1.0),
        supply=Inventory(), demand=Inventory(), trade_volume=0.0,
    )
    state = SimulationState(world=world, agents=agents, market=market)
    engine = SimulationEngine(config, state)
    manager = SimulationManager(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if config.tick_rate_hz > 0:
            await manager.start()
        yield
        await manager.stop()

    app = FastAPI(lifespan=lifespan)
    app.include_router(_make_router(manager))

    frontend = Path("frontend")
    if frontend.exists():
        app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")

    tiny_village = Path("tiny_village")
    if tiny_village.exists():
        app.mount("/tiny_village", StaticFiles(directory=str(tiny_village)), name="tiny_village")

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
