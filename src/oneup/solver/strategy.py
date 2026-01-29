from collections import Counter, defaultdict
import operator
from functools import reduce
from heapq import heapify
from typing import TYPE_CHECKING, Callable, Generator, Iterable, Optional

from grid.position import Alignment, Position

from .actions import RemovePossibleValue, SetPosition, SolverAction

if TYPE_CHECKING:
    from .solver import OneUpSolver

from .types import SolverState

type SolverStrategy = Callable[["OneUpSolver"], list[SolverAction]]


def default_solver_strategy(solver: "OneUpSolver") -> list[SolverAction]:
    collapse_action = find_easy_collapse(solver)
    if collapse_action is not None:
        return [collapse_action]

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

    # Identify chains
    chains = detect_chains(
        vision=solver.game.vision, possibilities=solver.possible_values
    )
    if len(chains) > 0:
        result = []
        print("Chains")
        for chain in chains:
            completed_chain = complete_chain(chain, solver.possible_values)
            if completed_chain is not None:
                print(sorted(list(completed_chain)))
                result.extend(create_chain_actions(completed_chain, solver))
            else:
                print("Couldn't complete chain:", chain)

        if len(result) > 0:
            return result

    return []


def find_easy_collapse(solver: "OneUpSolver") -> Optional[SolverAction]:
    entropic_positions = [
        (solver.entropy(position), i, position)
        for i, position in enumerate(solver._non_fixed_positions())
    ]
    heapify(entropic_positions)

    if len(entropic_positions) == 0:
        return None

    (entropy, _, position) = entropic_positions.pop(0)
    # If invalid state
    if entropy < 0:
        solver.state = SolverState.HALTED
        return None

    # Check for easy collapses
    if entropy == 0:
        value = list(solver.possible_values[position])[0]
        return SetPosition(position, value)


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
    if _is_group(values):
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


def _is_group(values: list[set[int]]) -> bool:
    combined_values: set[int] = reduce(operator.or_, values, set())
    return 0 < len(combined_values) == len(values)


def detect_chains(
    vision: dict[Position, set[Position]], possibilities: dict[Position, set[int]]
) -> list[set[Position]]:
    """Finds the largest sets of positions where if any position is known in the set, all positions are known."""
    candidates: list[set[Position]] = []

    nodes = {p for (p, values) in possibilities.items() if len(values) == 2}

    def neighbours(node: Position):
        """Returns all neighbours that would share a possibility"""
        return {
            p
            for p in vision[node].intersection(nodes)
            if p != node and len(possibilities[node].intersection(possibilities[p])) > 0
        }

    lowest: dict[Position, int] = {}
    inserted: dict[Position, int] = {}

    # Start a search from each node to find all the possible chains
    timer = inf_inc(0)
    for start in nodes:
        dfs(start, None, neighbours, [], inserted, lowest, timer)

    # Initialise components
    component_count = max(lowest.values())
    for _ in range(component_count + 1):
        candidates.append(set())

    # Add all positions to their component-groups
    for position, low in lowest.items():
        candidates[low].add(position)

    return [
        candidate
        for candidate in candidates
        if _is_chain(candidate, vision, possibilities)
    ]


def inf_inc(start: int = 0):
    count = start
    while True:
        yield count
        count += 1


def dfs(
    node: Position,
    parent: Optional[Position],
    neighbours: Callable[[Position], set[Position]],
    stack: list[Position],
    ids: dict[Position, int],
    lowest: dict[Position, int],
    timer: Generator[int],
):
    if node in ids:
        return

    stack.append(node)
    time = next(timer)
    ids[node] = time
    lowest[node] = time

    for neighbour in neighbours(node):
        if neighbour == parent:
            continue

        if neighbour not in ids:
            dfs(neighbour, node, neighbours, stack, ids, lowest, timer)

        if neighbour in stack:
            lowest[node] = min(lowest[node], lowest[neighbour])

    if ids[node] != lowest[node]:
        return

    while len(stack) > 0:
        popped = stack.pop()
        lowest[popped] = ids[node]
        if popped == node:
            break


def _chain_values(values: list[set[int]]) -> Counter[int]:
    counter = Counter[int]()
    for s in values:
        counter.update(s)
    return counter


def complete_chain(
    chain: set[Position], possibilities: dict[Position, set[int]]
) -> Optional[set[Position]]:
    values = [possibilities[position] for position in chain]

    mismatched_values = {
        value for (value, count) in _chain_values(values).items() if count % 2 == 1
    }
    # BUG: WRONG
    # There should be a single position in this chain which makes it bad
    for position in chain:
        if possibilities[position] == mismatched_values:
            result = chain.copy()
            result.remove(position)
            return result

    return None


def _is_chain(
    chain: set[Position],
    vision: dict[Position, set[Position]],
    possibilities: dict[Position, set[int]],
) -> bool:
    if len(chain) < 2:
        return False

    # Check that each position in the chain can see at least one other
    for position in chain:
        other_positions = chain.difference([position])
        if len(vision[position].intersection(other_positions)) == 0:
            return False

    return True


def create_chain_actions(
    chain: set[Position], solver: "OneUpSolver"
) -> list[SolverAction]:
    result = []
    for position in chain:
        for partner in chain:
            alignment = position.alignment(partner)
            if position == partner:
                continue

            if alignment == Alignment.NONE:
                # There are only two candidate squares that can be seen by both.
                # TODO:
                continue

            if (
                alignment != Alignment.NONE
                and partner not in solver.game.vision[position]
            ):
                continue

            if alignment == Alignment.HORIZONTAL:
                vision_group = solver.game.horizontal_vision[position]
            else:
                vision_group = solver.game.vertical_vision[position]

            included_group = set([position, partner])
            excluded_group = vision_group - included_group

            included_shared_values = solver.possible_values[position].intersection(
                solver.possible_values[partner]
            )
            for value in included_shared_values:
                for excluded_position in excluded_group:
                    if value in solver.possible_values[excluded_position]:
                        result.append(RemovePossibleValue(excluded_position, value))

    return result
