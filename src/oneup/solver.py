from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from functools import reduce
from typing import Callable, Optional
from grid.position import Position
from oneup.game import OneUp
from heapq import heapify
import operator


class SolverState(StrEnum):
    SOLVING = "solving"
    COMPLETE = "complete"
    HALTED = "halted"


type SolverStrategy = Callable[[OneUpSolver], list[SolverAction]]


def default_solver_strategy(solver: OneUpSolver) -> list[SolverAction]:
    entropic_positions = [
        (solver.entropy(position), i, position)
        for i, position in enumerate(solver._non_fixed_positions())
    ]
    heapify(entropic_positions)

    if len(entropic_positions) == 0:
        return []

    (entropy, _, position) = entropic_positions.pop(0)
    # If invalid state
    if entropy < 0:
        solver.state = SolverState.HALTED
        return []

    # Check for easy collapses
    if entropy == 0:
        value = list(solver.possible_values[position])[0]
        return [SetPosition(position, value)]

    # Identify mutually-exclusive rounds
    for vision_group in solver.game.all_vision_groups():
        group_data = {
            position: solver.possible_values[position]
            for position in vision_group
            if len(solver.possible_values[position]) > 1
        }
        if len(group_data) == 0:
            continue

        for round_size in range(2, len(group_data)):
            group_positions = detect_groups(round_size, group_data)
            if group_positions is None:
                continue

            round_values: set[int] = reduce(
                operator.or_,
                [solver.possible_values[position] for position in group_positions],
                set(),
            )

            print(f"Detected {round_size}-Group, ({round_values}) at {group_positions}")

            non_round_positions = vision_group - group_positions

            # Check if we're actually going to update anything with this
            result = []
            for position in non_round_positions:
                for value in round_values:
                    if value in solver.possible_values[position]:
                        result.append(RemovePossibleValue(position, value))

            if len(result) == 0:
                continue

            return result

    return []


type RoundDetector = Callable[[int, dict[Position, set[int]]], Optional[set[int]]]


def detect_groups(
    size: int, group: dict[Position, set[int]]
) -> Optional[set[Position]]:
    return _detect_group(size, group, set(), set())


def _detect_group(
    size: int,
    group: dict[Position, set[int]],
    included: set[Position],
    excluded: set[Position],
) -> Optional[set[Position]]:
    values = [group[position] for position in included]
    if _is_round(values):
        return included

    included_values: set[int] = reduce(operator.or_, values, initial=set())
    if len(included_values) > size:
        return None

    def overlaps(position: Position) -> bool:
        return len(included_values.intersection(group[position])) > 0

    remaining_positions = [
        position
        for position in set(group.keys()) - included - excluded
        if len(group[position]) <= size and (len(included) == 0 or overlaps(position))
    ]

    if len(remaining_positions) == 0:
        return None

    next_position = remaining_positions.pop()
    result_with_next_position = _detect_group(
        size, group, included | set([next_position]), excluded
    )

    if result_with_next_position is not None:
        return result_with_next_position

    # Detect the round without this next number
    return _detect_group(size, group, included, excluded | set([next_position]))


def _is_round(values: list[set[int]]) -> bool:
    combined_values: set[int] = reduce(operator.or_, values, set())
    return 0 < len(combined_values) == len(values)


class OneUpSolver:
    def __init__(self, game: OneUp) -> None:
        self.game = game
        self.possible_values: dict[Position, set[int]] = defaultdict(set)
        """A set of possible values for each position in the game."""
        self.initialize_possible_values()

        self.hints: dict[Position, set[int]] = defaultdict(set)
        """A set of user supplied values for each position in the game."""

        self.state = SolverState.SOLVING

        self.action_result_stack: list[ActionResult] = []

    def initialize_possible_values(self):
        for position in self.game.free_positions():
            value = self.game.grid.get_position(position)
            if value != 0:
                self.possible_values[position] = set([value])

            else:
                # Initialise with all possible values from 1 to the max
                self.possible_values[position] = set(
                    range(1, self.game.max_allowed_value(position) + 1)
                )

            # Remove values which directly conflict with visible other positions
            blocked_values = set(self.game.other_visible_positions(position).values())
            self.possible_values[position] -= blocked_values

    def _non_fixed_positions(self):
        for position in self.game.free_positions():
            if self.game.grid.get_position(position) == 0:
                yield position

    def entropy(self, position: Position) -> int:
        return len(self.possible_values[position]) - 1

    def step_solver(self, strategy: SolverStrategy = default_solver_strategy):
        if self.state == SolverState.COMPLETE:
            return

        actions = strategy(self)
        if actions == []:
            self.state = SolverState.HALTED
            return

        self.perform_actions(actions)
        if self.game.is_complete():
            self.state = SolverState.COMPLETE

    def perform_actions(self, actions: list[SolverAction]):
        action_queue: list[SolverAction] = actions
        while len(action_queue) > 0:
            action = action_queue.pop()
            result = action.perform(self)
            if not result.succeeded:
                continue

            print(result.summary)

            self.action_result_stack.append(result)
            action_queue.extend(result.next_actions)

    def perform_action(self, action: SolverAction):
        return self.perform_actions([action])

    def undo(self):
        if len(self.action_result_stack) == 0:
            return

        last_action = self.action_result_stack.pop()
        if last_action.succeeded and last_action.undo is not None:
            print(f"Undoing: {last_action.summary}")
            last_action.undo(self)


class SolverAction(ABC):
    @abstractmethod
    def perform(self, solver: OneUpSolver) -> ActionResult: ...


@dataclass
class ActionResult:
    succeeded: bool
    summary: str
    next_actions: list[SolverAction]
    undo: Optional[Callable[[OneUpSolver]]] = None


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
        solver.game.grid.set_position(self.position, self.value)

        def undo(solver: OneUpSolver):
            solver.game.grid.set_position(self.position, 0)

        return ActionResult(
            summary=f"Set position {self.position.as_tuple()} to {self.value}",
            succeeded=True,
            next_actions=[
                SetPossibleValues(self.position, set([self.value])),
                PropagateValue(self.position),
            ],
            undo=undo,
        )
