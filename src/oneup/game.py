import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import cast
from functools import cached_property
from collections import defaultdict

from grid import Grid, Position
from grid.position import Alignment, Direction, opposite_direction


@dataclass
class Wall:
    bounds: tuple[Position, Position]

    @classmethod
    def from_positions(cls, a: Position, b: Position):
        if a == b:
            raise ValueError("Positions cannot be equal")

        if not a.is_neighbour(b):
            raise ValueError(
                "Positions must be neighbours to contain a wall between them"
            )

        bounds = cast(tuple[Position, Position], tuple(sorted((a, b))))
        return cls(bounds=bounds)

    @classmethod
    def from_json(cls, data: tuple[tuple[int, int], tuple[int, int]]):
        t1, t2 = data
        p1 = Position.from_tuple(t1)
        p2 = Position.from_tuple(t2)
        return cls.from_positions(p1, p2)

    def alignment(self) -> Alignment:
        a, b = self.bounds
        return a.alignment(b)

    def to_json(self) -> tuple[tuple[int, int], tuple[int, int]]:
        a, b = self.bounds
        return (a.as_tuple(), b.as_tuple())

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Wall):
            return False

        return self.bounds == value.bounds

    def __hash__(self) -> int:
        return hash(self.bounds)


@dataclass
class OneUp:
    grid: Grid
    walls: set[Wall]
    blocked_positions: set[Position] = field(default_factory=set)
    fixed_positions: set[Position] = field(default_factory=set)
    """Positions which have values in the original game state."""

    def __post_init__(self):
        for position in self.free_positions():
            if self.grid.get_position(position) > 0:
                self.fixed_positions.add(position)

    @property
    def size(self) -> int:
        return self.grid.dimensions()[0]

    def free_positions(self):
        for position in self.grid.all_positions():
            if position not in self.blocked_positions:
                yield position

    def is_complete(self) -> bool:
        for position in self.grid.all_positions():
            # Skip if blocked
            if position in self.blocked_positions:
                continue

            value = self.grid.get_position(position)

            # Check if empty cell
            if value == 0:
                return False

            # Check if violates constraints
            if value > self.max_allowed_value(position):
                return False

            # Check no other visible position contains this number
            for visible_position in self.vision[position]:
                if visible_position == position:
                    continue

                if value == self.grid.get_position(visible_position):
                    return False

        return True

    def max_allowed_value(self, position: Position) -> int:
        return min(
            len(self.horizontal_vision[position]), len(self.vertical_vision[position])
        )

    def other_visible_positions(self, position: Position) -> dict[Position, int]:
        """Returns all other visible positions (except the supplied one) from the supplied position."""
        result = self.vision[position].copy()
        result.remove(position)
        return {position: self.grid.get_position(position) for position in result}

    @cached_property
    def horizontal_vision(self) -> dict[Position, set[Position]]:
        seen: set[Position] = set()
        result: dict[Position, set[Position]] = defaultdict(set)

        for position in self.free_positions():
            # Add all in the horizontal group if we haven't seen this position
            if position not in seen:
                group = self._find_horizontal_group(position)
                # Add nodes to visibility and seens
                for p1 in group:
                    seen.add(p1)
                    for p2 in group:
                        result[p1].add(p2)
                        result[p2].add(p1)

        return result

    @cached_property
    def vertical_vision(self) -> dict[Position, set[Position]]:
        seen: set[Position] = set()
        result: dict[Position, set[Position]] = defaultdict(set)

        for position in self.free_positions():
            # Add all in the vertical group if we haven't seen this position
            if position not in seen:
                group = self._find_vertical_group(position)
                # Add nodes to visibility and seens
                for p1 in group:
                    seen.add(p1)
                    for p2 in group:
                        result[p1].add(p2)
                        result[p2].add(p1)

        return result

    @cached_property
    def vision(self) -> dict[Position, set[Position]]:
        return {
            position: self.vertical_vision[position] | self.horizontal_vision[position]
            for position in self.free_positions()
        }

    def _find_visible_positions_in_direction(
        self, origin: Position, direction: Direction
    ) -> set[Position]:
        result: set[Position] = set()
        if origin in self.blocked_positions:
            return result

        result.add(origin)
        for position in self.grid.positions_in_direction(origin, direction):
            # Check if square is blocked
            if position in self.blocked_positions:
                break

            # Check if a wall blocks it
            wall = Wall.from_positions(
                position.neighbour(opposite_direction(direction)), position
            )
            if wall in self.walls:
                break

            # Otherwise add it
            result.add(position)

        return result

    def _find_vertical_group(self, position: Position) -> set[Position]:
        return self._find_visible_positions_in_direction(
            position, Direction.UP
        ) | self._find_visible_positions_in_direction(position, Direction.DOWN)

    def _find_horizontal_group(self, position: Position) -> set[Position]:
        return self._find_visible_positions_in_direction(
            position, Direction.LEFT
        ) | self._find_visible_positions_in_direction(position, Direction.RIGHT)

    def all_vision_groups(self):
        vert_seen = set[Position]()
        horizontal_seen = set[Position]()

        for position in self.free_positions():
            if position not in vert_seen:
                group = self._find_vertical_group(position)
                yield group
                vert_seen |= group

            if position not in horizontal_seen:
                group = self._find_horizontal_group(position)
                yield group
                horizontal_seen |= group

    def __str__(self) -> str:
        lines: list[str] = []

        header = "#" * (2 * self.size + 1)
        lines.append(header)

        for row in range(self.size):
            row_str = "#"
            # Number row
            for col in range(self.size):
                position = Position(row, col)
                next_position = Position(row, col + 1)

                # Add the position
                char = (
                    str(self.grid.get_position(position))
                    if position not in self.blocked_positions
                    else "#"
                )
                if char == "0":
                    char = "."
                row_str += char

                # Add any horizontal wall if it exists
                if not self.grid.is_in_bounds(next_position):
                    continue

                wall = Wall.from_positions(position, next_position)
                if wall in self.walls:
                    row_str += "|"
                else:
                    row_str += " "

            row_str += "#"
            lines.append(row_str)

            # Don't add this line for the final row
            if row == self.size - 1:
                break

            wall_str = "#"
            for col in range(self.size):
                position = Position(row, col)
                below_position = Position(row + 1, col)

                # Add any vertical wall if it exists
                wall = Wall.from_positions(position, below_position)
                char = "-" if wall in self.walls else " "
                wall_str += char
                # Empty space for wall column
                if col < self.size - 1:
                    wall_str += " "

            wall_str += "#"
            lines.append(wall_str)

        lines.append(header)
        return "\n".join(lines)


class OneUpSerializer:
    BLOCKING = "#"
    EMPTY = " "

    @classmethod
    def data_dict(cls, game: OneUp) -> dict:
        return {
            "size": game.size,
            "values": [int(x) for x in game.grid.data.flatten()],
            "walls": [wall.to_json() for wall in game.walls],
            "blocking": [position.as_tuple() for position in game.blocked_positions],
        }

    @classmethod
    def save(cls, game: OneUp, path: Path):
        if path.is_dir():
            raise ValueError("Path is dir")

        with open(path, "w") as output:
            json.dump(OneUpSerializer.data_dict(game), output)

    @classmethod
    def load(cls, path: Path) -> OneUp:
        with open(path) as in_file:
            data: dict = json.load(in_file)

        grid = Grid.from_list(data["size"], data["values"])
        walls = {
            Wall.from_positions(Position.from_tuple(a), Position.from_tuple(b))
            for a, b in data["walls"]
        }

        blocking = {Position.from_tuple(p) for p in data["blocking"]}
        game = OneUp(grid=grid, walls=walls, blocked_positions=blocking)
        return game
