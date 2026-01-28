from pathlib import Path
from oneup.app import start_app
from oneup.game import OneUpSerializer
from oneup.games import practice_10, practice_2, puzzle_15_4, round_of_16
from oneup.solver import OneUpSolver, SolverState
from pprint import pprint

ROOT_DIR = Path(__file__).parent.parent.parent / "levels"


def main() -> None:
    game = puzzle_15_4()
    # solver = OneUpSolver(game)
    # while solver.state == SolverState.SOLVING:
    #     print(game)
    #     solver.step_solver()
    #
    # print(solver.state)
    # if solver.state == SolverState.HALTED:
    #     pprint({p: e for (p, e) in solver.possible_values.items() if len(e) > 1})

    # OneUpSerializer.save(game, ROOT_DIR / 'level1.txt')
    start_app(game)
