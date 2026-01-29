from typing import TYPE_CHECKING

from grid.position import Position
from oneup.actions import Action, ActionResult

if TYPE_CHECKING:
    from .solver import OneUpSolver

SolverAction = Action["OneUpSolver"]


class AddHint(SolverAction):
    def __init__(self, position: Position, value: int) -> None:
        self.position = position
        self.value = value

    def perform(self, solver: OneUpSolver) -> ActionResult:
        success = self.value not in solver.hints[self.position]
        solver.hints[self.position].add(self.value)

        def undo(solver: OneUpSolver):
            if success:
                solver.hints[self.position].remove(self.value)

        return ActionResult(
            summary=f"Add hint of {self.value} to {self.position.as_tuple()}",
            succeeded=success,
            next_actions=[],
            undo=undo,
        )


class RemoveHint(SolverAction):
    def __init__(self, position: Position, value: int) -> None:
        self.position = position
        self.value = value

    def perform(self, solver: OneUpSolver) -> ActionResult:
        success = self.value in solver.hints[self.position]
        solver.hints[self.position].remove(self.value)

        def undo(solver: OneUpSolver):
            if success:
                solver.hints[self.position].add(self.value)

        return ActionResult(
            summary=f"Remove hint: {self.value} from {self.position.as_tuple()}",
            succeeded=success,
            next_actions=[],
            undo=undo,
        )


class AddPossibleValue(SolverAction):
    def __init__(self, position: Position, value: int) -> None:
        self.position = position
        self.value = value

    def perform(self, solver: OneUpSolver) -> ActionResult:
        success = self.value not in solver.possible_values[self.position]
        solver.possible_values[self.position].add(self.value)

        def undo(solver: OneUpSolver):
            if success:
                solver.possible_values[self.position].remove(self.value)

        return ActionResult(
            summary=f"Add possible value of {self.value} to {self.position.as_tuple()}",
            succeeded=success,
            next_actions=[],
            undo=undo,
        )


class RemovePossibleValue(SolverAction):
    def __init__(self, position: Position, value: int) -> None:
        self.position = position
        self.value = value

    def perform(self, solver: OneUpSolver) -> ActionResult:
        success = self.value in solver.possible_values[self.position]
        if success:
            solver.possible_values[self.position].remove(self.value)

        def undo(solver: OneUpSolver):
            if success:
                solver.possible_values[self.position].add(self.value)

        return ActionResult(
            summary=f"Remove possible value of {self.value} from {self.position.as_tuple()}",
            succeeded=success,
            next_actions=[],
            undo=undo,
        )


class SetPossibleValues(SolverAction):
    def __init__(self, position: Position, values: set[int]) -> None:
        self.position = position
        self.values = values

    def perform(self, solver: OneUpSolver) -> ActionResult:
        old_values = solver.possible_values[self.position]
        solver.possible_values[self.position] = self.values

        def undo(solver: OneUpSolver):
            solver.possible_values[self.position] = old_values

        return ActionResult(
            summary=f"Set possible values of {self.position.as_tuple()} to {self.values}",
            succeeded=True,
            next_actions=[],
            undo=undo,
        )


class PropagateValue(SolverAction):
    def __init__(self, position: Position) -> None:
        self.position = position

    def perform(self, solver: OneUpSolver) -> ActionResult:
        # Ensure we have a value at the position
        value = solver.game.grid.get_position(self.position)
        if value == 0:
            return ActionResult(
                summary=f"Propagate value <empty> from {self.position.as_tuple()}",
                succeeded=False,
                next_actions=[],
            )

        changed_positions: set[Position] = set()
        for visible_position in solver.game.other_visible_positions(self.position):
            possibilities = solver.possible_values[visible_position]
            if value in possibilities:
                changed_positions.add(visible_position)
                possibilities.remove(value)

        def undo(solver: OneUpSolver):
            for position in changed_positions:
                solver.possible_values[position].add(value)

        return ActionResult(
            summary=f"Propagate value {value} from {self.position.as_tuple()}",
            succeeded=True,
            next_actions=[],
            undo=undo,
        )


class SetPosition(SolverAction):
    def __init__(self, position: Position, value: int) -> None:
        self.position = position
        self.value = value

    def perform(self, solver: OneUpSolver) -> ActionResult:
        current = solver.game.grid.get_position(self.position)
        if current == self.value:
            return ActionResult(
                summary=f"Set position {self.position.as_tuple()} to {self.value}",
                succeeded=False,
                next_actions=[],
            )

        solver.game.grid.set_position(self.position, self.value)

        def undo(solver: OneUpSolver):
            solver.game.grid.set_position(self.position, current)

        return ActionResult(
            summary=f"Set position {self.position.as_tuple()} to {self.value}",
            succeeded=True,
            next_actions=[
                SetPossibleValues(self.position, set([self.value])),
                PropagateValue(self.position),
            ],
            undo=undo,
        )
