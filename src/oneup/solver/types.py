from enum import StrEnum


class SolverState(StrEnum):
    SOLVING = "solving"
    COMPLETE = "complete"
    HALTED = "halted"
