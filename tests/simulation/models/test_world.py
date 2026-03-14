from simulation.models.world import Tile, World

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
