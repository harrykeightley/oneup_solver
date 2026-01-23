from dataclasses import dataclass
from enum import Enum, StrEnum


class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)


def opposite_direction(direction: Direction) -> Direction:
    match direction:
        case Direction.UP:
            return Direction.DOWN
        case Direction.DOWN:
            return Direction.UP
        case Direction.LEFT:
            return Direction.RIGHT
        case _:
            return Direction.LEFT


class Alignment(StrEnum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    NONE = "none"


@dataclass
class Position:
    row: int
    col: int

    @classmethod
    def from_tuple(cls, data: tuple[int, int]):
        row, col = data
        return cls(row=row, col=col)

    def add(self, delta: Position) -> Position:
        return Position(row=self.row + delta.row, col=self.col + delta.col)

    def scale(self, scalar: int) -> Position:
        return Position(row=self.row * scalar, col=self.col * scalar)

    def negate(self) -> Position:
        return self.scale(-1)

    def subtract(self, amount: Position) -> Position:
        return self.add(amount.negate())

    def as_tuple(self) -> tuple[int, int]:
        return (self.row, self.col)

    def neighbour(self, direction: Direction) -> Position:
        return self.add(Position.from_tuple(direction.value))

    @classmethod
    def neighbour_offsets(cls):
        for d in Direction:
            yield Position.from_tuple(d.value)

    def neighbours(self):
        for offset in self.neighbour_offsets():
            yield self.add(offset)

    def is_neighbour(self, position: Position) -> bool:
        return self.manhattan_distance(position) == 1

    def manhattan_distance(self, target: Position) -> int:
        return abs(self.row - target.row) + abs(self.col - target.col)

    def alignment(self, position: Position) -> Alignment:
        if self.row == position.row:
            return Alignment.HORIZONTAL

        if self.col == position.col:
            return Alignment.VERTICAL

        return Alignment.NONE

    @staticmethod
    def group_alignment(
        position: Position, other_position: Position, *extra: Position
    ) -> Alignment:
        """Returns the alignment of the supplied positions.

        If the positions aren't all vertically or horizontally aligned, returns Alignment.NONE
        """
        result = position.alignment(other_position)
        if result == Alignment.NONE:
            return result

        last_position = other_position

        for position in extra:
            step_alignment = last_position.alignment(position)
            if step_alignment == Alignment.NONE or step_alignment != result:
                return Alignment.NONE
            last_position = position

        return result

    def __eq__(self, position: object, /) -> bool:
        if not isinstance(position, Position):
            return False

        return self.row == position.row and self.col == position.col

    def __hash__(self) -> int:
        return hash((self.row, self.col))

    def __neg__(self) -> Position:
        return self.negate()

    def __add__(self, other: Position) -> Position:
        return self.add(other)

    def __sub__(self, other: Position) -> Position:
        return self.subtract(other)

    def __lt__(self, other: Position) -> bool:
        return self.as_tuple() < other.as_tuple()
