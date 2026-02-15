from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional


class Action[T](ABC):
    @abstractmethod
    def perform(self, solver: T) -> ActionResult[T]: ...


@dataclass
class ActionResult[T]:
    succeeded: bool
    summary: str
    """A string describing the action"""
    next_actions: list[Action[T]]
    undo: Optional[Callable[[T]]] = None


class ActionQueue[T]:
    def __init__(self) -> None:
        self.actions: list[Action[T]] = []
        self.action_results: list[ActionResult[T]] = []
        self.action_index = 0

        self.save_points: list[int] = []

    def is_current(self):
        return self.action_index == len(self.actions)

    def _create_savepoint(self):
        self.save_points.append(len(self.action_results))

    def _is_at_savepoint(self):
        return self.action_index in self.save_points

    def _drop_future(self):
        self.actions = self.actions[: self.action_index]
        self.action_results = self.action_results[: self.action_index]
        self.save_points = [s for s in self.save_points if s <= self.action_index]

    def perform_actions(self, actions: list[Action[T]], data: T):
        if len(actions) == 0:
            return

        # If we're not up to date, drop the future history
        if not self.is_current():
            self._drop_future()

        # Create savepoint
        if not self._is_at_savepoint():
            self._create_savepoint()

        action_stack = actions[::-1]
        while len(action_stack) > 0:
            action = action_stack.pop()
            result = action.perform(data)

            if not result.succeeded:
                print(f"Failed: {result.summary}")
                continue

            self.actions.append(action)
            self.action_results.append(result)

            self.action_index += 1
            action_stack.extend(result.next_actions)

        print("Action Index post actions", self.action_index)

    def previous_savepoint(self) -> Optional[int]:
        return max([s for s in self.save_points if s < self.action_index], default=None)

    def next_savepoint(self) -> Optional[int]:
        return min([s for s in self.save_points if s > self.action_index], default=None)

    def _move_to_index(self, target_action_index: int, data: T):
        # Clamp action index
        target_action_index = min(len(self.actions), max(0, target_action_index))
        if self.action_index == target_action_index:
            return

        if target_action_index < self.action_index:
            results_since_target = self.action_results[
                target_action_index : self.action_index
            ]
            # Undo all these results in reverse
            for result in results_since_target[::-1]:
                if result.undo is not None:
                    result.undo(data)
                self.action_index -= 1

        if target_action_index > self.action_index:
            actions_until_target = self.actions[self.action_index : target_action_index]

            # Redo these actions
            for action in actions_until_target:
                action.perform(data)
                self.action_index += 1

    def undo(self, data: T):
        """Undo the actions until the last savepoint"""
        savepoint = self.previous_savepoint()
        if savepoint is None:
            return

        self._move_to_index(savepoint, data)

    def redo(self, data: T):
        """Redo the actions until the next savepoint"""
        savepoint = self.next_savepoint() or len(self.actions)
        if savepoint == self.action_index:
            return

        self._move_to_index(savepoint, data)

    def fast_forward(self, data: T):
        self._move_to_index(len(self.actions), data)
