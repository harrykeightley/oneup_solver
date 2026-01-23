from grid.grid import Grid
from grid.position import Position
from oneup.game import OneUp, Wall


def build_game(
    size: int,
    values: dict[Position, int],
    wall_positions: list[tuple[Position, Position]],
    blocking_positions: set[Position] = set(),
) -> OneUp:
    walls = set[Wall]()
    for a, b in wall_positions:
        walls.add(Wall.from_positions(a, b))

    game = OneUp(
        grid=Grid.from_empty(size), walls=walls, blocked_positions=blocking_positions
    )
    for position, value in values.items():
        game.grid.set_position(position, value)
    return game


def practice_1() -> OneUp:
    values: dict[Position, int] = {
        Position(0, 0): 5,
        Position(4, 4): 1,
    }

    wall_positions: list[tuple[Position, Position]] = [
        (Position(1, 0), Position(1, 1)),
        (Position(0, 2), Position(1, 2)),
        (Position(1, 2), Position(1, 3)),
        (Position(1, 3), Position(2, 3)),
        (Position(2, 2), Position(3, 2)),
        (Position(3, 1), Position(3, 2)),
    ]

    return build_game(5, values, wall_positions)


def practice_2() -> OneUp:
    values: dict[Position, int] = {
        Position(2, 0): 4,
        Position(2, 1): 3,
    }

    wall_positions: list[tuple[Position, Position]] = [
        (Position(1, 0), Position(1, 1)),
        (Position(1, 2), Position(1, 3)),
        (Position(1, 3), Position(2, 3)),
        (Position(2, 2), Position(3, 2)),
        (Position(3, 2), Position(3, 3)),
        (Position(3, 3), Position(4, 3)),
    ]

    return build_game(5, values, wall_positions)


def practice_10() -> OneUp:
    values: dict[Position, int] = {}

    wall_positions: list[tuple[Position, Position]] = [
        (Position(1, 0), Position(2, 0)),
        (Position(1, 1), Position(1, 2)),
        (Position(1, 3), Position(2, 3)),
        (Position(2, 3), Position(2, 4)),
        (Position(2, 4), Position(3, 4)),
        (Position(3, 1), Position(3, 2)),
        (Position(3, 1), Position(4, 1)),
        (Position(4, 2), Position(4, 3)),
    ]

    return build_game(5, values, wall_positions)


def round_of_16() -> OneUp:
    values: dict[Position, int] = {
        Position(0, 0): 1,
        Position(0, 1): 5,
        Position(0, 4): 4,
        Position(1, 6): 2,
        Position(1, 7): 5,
        Position(3, 0): 3,
        Position(4, 7): 4,
        Position(6, 2): 7,
        Position(6, 5): 2,
    }

    wall_positions: list[tuple[Position, Position]] = [
        (Position(2, 2), Position(2, 3)),
        (Position(2, 0), Position(3, 0)),
        (Position(3, 4), Position(3, 5)),
        (Position(3, 4), Position(4, 4)),
        (Position(4, 1), Position(5, 1)),
        (Position(4, 2), Position(4, 3)),
        (Position(4, 6), Position(5, 6)),
        (Position(5, 3), Position(5, 4)),
    ]

    blocking = set([Position(7, 7)])

    return build_game(8, values, wall_positions, blocking)


def puzzle_15_4() -> OneUp:
    values: dict[Position, int] = {
        Position(0, 1): 8,
        Position(0, 4): 6,
        Position(3, 0): 2,
        Position(5, 6): 3,
        Position(6, 1): 4,
        Position(6, 3): 5,
        Position(7, 2): 6,
        Position(7, 4): 7,
        Position(7, 6): 8,
    }

    wall_positions: list[tuple[Position, Position]] = [
        (Position(1, 5), Position(2, 5)),
        (Position(2, 3), Position(2, 4)),
        (Position(2, 4), Position(2, 5)),
        (Position(2, 5), Position(3, 5)),
        (Position(3, 3), Position(3, 4)),
        (Position(3, 5), Position(3, 6)),
        (Position(3, 5), Position(4, 5)),
        (Position(3, 7), Position(4, 7)),
        #
        (Position(3, 0), Position(4, 0)),
        (Position(4, 0), Position(5, 0)),
        (Position(5, 1), Position(5, 2)),
        (Position(5, 2), Position(5, 3)),
        (Position(5, 3), Position(5, 4)),
        (Position(5, 7), Position(6, 7)),
    ]

    return build_game(8, values, wall_positions)


def final() -> OneUp:
    values: dict[Position, int] = {
        Position(0, 1): 1,
        Position(0, 2): 5,
        Position(1, 4): 4,
        Position(1, 6): 2,
        Position(1, 7): 5,
        Position(2, 0): 2,
        Position(3, 2): 8,
        Position(3, 8): 3,
        Position(4, 7): 3,
        Position(5, 3): 4,
        Position(6, 4): 4,
        Position(7, 3): 1,
        Position(7, 7): 9,
        Position(8, 6): 4,
        Position(9, 5): 1,
        Position(9, 7): 6,
    }

    wall_positions: list[tuple[Position, Position]] = [
        (Position(1, 2), Position(1, 3)),
        (Position(2, 3), Position(3, 3)),
        (Position(4, 1), Position(5, 1)),
        (Position(3, 4), Position(4, 4)),
        (Position(4, 1), Position(5, 1)),
        (Position(6, 6), Position(6, 7)),
    ]

    blocking = set(
        [
            Position(0, 0),
            Position(0, 8),
            Position(0, 9),
            Position(1, 8),
            Position(1, 9),
            Position(4, 4),
            Position(5, 5),
            Position(8, 0),
            Position(8, 1),
            Position(8, 9),
            Position(9, 0),
            Position(9, 1),
            Position(9, 8),
            Position(9, 9),
        ]
    )

    return build_game(10, values, wall_positions, blocking)
