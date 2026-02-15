from collections import defaultdict

from grid.position import Position
from oneup.actions import ActionQueue
from oneup.game import OneUp
from oneup.solver.actions import SolverAction

from .strategy import SolverStrategy, default_solver_strategy
from .types import SolverState


class OneUpSolver:
    def __init__(self, game: OneUp) -> None:
        self.game = game
        self.reset()

    def reset(self):
        self.possible_values: dict[Position, set[int]] = defaultdict(set)
        """A set of possible values for each position in the game."""
        self.initialize_possible_values()

        self.hints: dict[Position, set[int]] = defaultdict(set)
        """A set of user supplied values for each position in the game."""

        self.state = SolverState.SOLVING

        self.action_queue = ActionQueue[OneUpSolver]()

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
        actions = strategy(self)
        if actions == []:
            self.state = SolverState.HALTED
            print("HALTED")
            return

        self.perform_actions(actions)
        if self.game.is_complete():
            print("COMPLETE")
            self.state = SolverState.COMPLETE

    def perform_actions(self, actions: list[SolverAction]):
        self.action_queue.perform_actions(actions, self)

    def perform_action(self, action: SolverAction):
        return self.perform_actions([action])

    def undo(self):
        self.action_queue.undo(self)

    def redo(self):
        self.action_queue.redo(self)
