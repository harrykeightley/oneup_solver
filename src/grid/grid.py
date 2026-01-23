from typing import Callable
import numpy as np
from dataclasses import dataclass
from grid.position import Direction, Position

# The number within a cell. 0 Represents empty
GridItem = np.dtype[np.int8]
type GridData = np.ndarray[tuple[int, int], GridItem]


@dataclass
class Grid:
    data: GridData

    @classmethod
    def from_empty(cls, grid_size: int):
        return cls(np.zeros(shape=(grid_size, grid_size), dtype=np.int8))

    @classmethod
    def from_list(cls, grid_size: int, data: list[int]):
        return cls(np.array(data, dtype=np.int8).reshape((grid_size, grid_size)))

    def map(self, fn: Callable[[GridData], GridData]) -> Grid:
        self.data = fn(self.data)
        return self

    def is_in_bounds(self, position: Position) -> bool:
        rows, cols = self.data.shape
        return 0 <= position.row < rows and 0 <= position.col < cols

    def get_position(self, position: Position) -> int:
        return self.data[position.as_tuple()]

    def set_position(self, position: Position, value: int) -> bool:
        """Returns true iff successful"""
        if not self.is_in_bounds(position):
            return False

        self.data[position.as_tuple()] = value
        return True

    def clear_position(self, position: Position) -> bool:
        return self.set_position(position, 0)

    def all_positions(self):
        rows, cols = self.dimensions()
        for row in range(0, rows):
            for col in range(0, cols):
                yield Position(row=row, col=col)

    def positions_in_direction(
        self, origin: Position, direction: Direction
    ) -> list[Position]:
        """Returns a list of all positions in the supplied direction which are in bounds"""

        result: list[Position] = []
        position = origin.neighbour(direction)

        while self.is_in_bounds(position):
            result.append(position)
            position = position.neighbour(direction)

        return result

    def dimensions(self) -> tuple[int, int]:
        return self.data.shape
