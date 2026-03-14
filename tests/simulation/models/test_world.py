from simulation.models.world import Tile, World

from simulation.config import SimConfig
from simulation.models.world import build_world

def test_build_world_correct_size():
    config = SimConfig(grid_size=20)
    world = build_world(config)
    assert len(world.grid) == 20
    assert len(world.grid[0]) == 20

def test_build_world_contains_all_tile_types():
    config = SimConfig(grid_size=20, seed=42)
    world = build_world(config)
    types = {world.grid[y][x].tile_type for y in range(20) for x in range(20)}
    assert types == {"farm", "forest", "mine", "town", "market"}

def test_build_world_is_reproducible():
    config = SimConfig(grid_size=20, seed=99)
    w1 = build_world(config)
    w2 = build_world(config)
    assert w1.grid[5][5].tile_type == w2.grid[5][5].tile_type

def test_tile_has_required_fields():
    t = Tile(x=0, y=0, tile_type="farm", resource_yield=1.0)
    assert t.tile_type == "farm"
    assert t.resource_yield == 1.0

def test_world_starts_at_tick_zero():
    grid = [[Tile(x=x, y=y, tile_type="town", resource_yield=0.0)
             for x in range(3)] for y in range(3)]
    world = World(grid=grid)
    assert world.tick == 0

def test_world_grid_dimensions():
    grid = [[Tile(x=x, y=y, tile_type="farm", resource_yield=1.0)
             for x in range(5)] for y in range(5)]
    world = World(grid=grid)
    assert len(world.grid) == 5
    assert len(world.grid[0]) == 5
