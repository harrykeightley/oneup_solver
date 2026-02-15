from collections import defaultdict
from enum import Enum
from pathlib import Path
import tkinter as tk
from tkinter.simpledialog import askinteger
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter import font as tk_font
from typing import Any, Callable, Literal, Optional

from grid.grid import Grid
from grid.position import Alignment, Direction, Position
from oneup.game import OneUp, OneUpSerializer, Wall
from oneup.solver import (
    AddHint,
    OneUpSolver,
    RemoveHint,
    SetPosition,
    SolverState,
)


class OneUpApp:
    SHIFT_BINDINGS = "!@#$%^&*("

    class PlacementMode(Enum):
        WALLS = "wall"
        NUMBERS = "number"

    def __init__(self, root: tk.Tk, game: OneUp) -> None:
        root.title("OneUp")
        self.root = root
        self.game = game
        self.solver = OneUpSolver(self.game)

        self.placement_mode = OneUpApp.PlacementMode.NUMBERS
        self.show_solver_hints = False

        self.grid = GridCanvas(
            root,
            dimensions=(8, 8),
            size=(600, 600),
            on_select_position=self.on_click_position,
            on_right_click_position=self.on_right_click_position,
            on_select_wall=self.on_select_wall,
        )
        self.grid.pack(fill=tk.BOTH, expand=True)
        self.selected_position: Optional[Position] = None

        self.commands = CommandsPane(
            root,
            on_step=self.step,
            on_undo=self.undo,
            on_reset=self.reset,
            on_solve=self.attempt_solve,
            toggle_creation=self.update(self.toggle_creation_mode),
            toggle_solver_hints=self.update(self.toggle_solver_hints),
        )
        self.commands.pack()

        self.root.bind("<Key>", self.on_keypress)

        menu = tk.Menu(root)
        filemenu = tk.Menu(menu)
        filemenu.add_command(label="New", command=self.new)
        filemenu.add_command(label="Save", command=self.save)
        filemenu.add_command(label="Load", command=self.load)

        menu.add_cascade(label="File", menu=filemenu)
        root.config(menu=menu)

        self.redraw()

    def step(self):
        self.solver.step_solver()
        self.redraw()

    def undo(self):
        self.solver.undo()
        self.redraw()

    def save(self):
        path = asksaveasfilename(title="Save Level")
        OneUpSerializer.save(self.game, Path(path))

    def load(self):
        path = askopenfilename(title="Load Level")
        self.game = OneUpSerializer.load(Path(path))
        self.reset()

    def new(self):
        size = askinteger(
            title="New Level",
            prompt="Enter the size of the level",
            minvalue=4,
            maxvalue=10,
        )
        if size is None:
            return

        self.game = OneUp(grid=Grid.from_empty(size), walls=set())
        self.reset()

    def remake_game(self):
        """Rebuilds the game to refresh the vision stuff. Kind of ridiculous."""
        data = OneUpSerializer.data_dict(self.game)
        grid = Grid.from_list(data["size"], data["values"])
        old_fixed = self.game.fixed_positions
        self.game = OneUp(
            grid=grid,
            walls=self.game.walls,
            blocked_positions=self.game.blocked_positions,
        )
        self.game.fixed_positions = old_fixed
        self.reset()

    def reset(self):
        for position in self.game.free_positions():
            if position in self.game.fixed_positions:
                continue
            self.game.grid.set_position(position, 0)

        self.solver = OneUpSolver(self.game)
        self.grid.dimensions = (self.game.size, self.game.size)
        self.redraw()

    def attempt_solve(self):
        self.solver.state = SolverState.SOLVING
        while self.solver.state == SolverState.SOLVING:
            self.solver.step_solver()

        self.redraw()

    def detect_errors(self) -> set[Position]:
        result = set[Position]()
        for group in self.game.all_vision_groups():
            for start in group:
                if len(self.solver.possible_values[start]) == 0:
                    result.add(start)

                for other in group:
                    if start == other:
                        continue
                    value = self.game.grid.get_position(start)
                    other_value = self.game.grid.get_position(other)

                    if value == 0:
                        continue

                    if value == other_value:
                        result.add(start)
                        result.add(other)

        return result

    def update(self, fn: Callable[[], Any]) -> Callable[[], Any]:
        def callback():
            fn()
            self.redraw()

        return callback

    def toggle_creation_mode(self):
        if self.placement_mode == self.PlacementMode.NUMBERS:
            self.placement_mode = self.PlacementMode.WALLS
        else:
            self.placement_mode = self.PlacementMode.NUMBERS

    def toggle_solver_hints(self):
        self.show_solver_hints = not self.show_solver_hints

    def redraw(self):
        self.grid.redraw(
            self.game,
            selected_position=self.selected_position,
            errors=self.detect_errors(),
            hints=self.solver.hints,
            solver_hints=self.solver.possible_values,
            show_solver_hints=self.show_solver_hints,
        )

    def on_right_click_position(self, position: Position):
        if self.placement_mode != self.PlacementMode.WALLS:
            return

        self.selected_position = None
        if position in self.game.blocked_positions:
            self.game.blocked_positions.remove(position)
        else:
            self.game.blocked_positions.add(position)

        self.remake_game()

    def on_click_position(self, position: Position):
        if self.placement_mode == self.PlacementMode.NUMBERS:
            if position == self.selected_position:
                self.selected_position = None
            else:
                self.selected_position = position

        self.redraw()

    def on_select_wall(self, wall: Wall):
        if self.placement_mode != self.PlacementMode.WALLS:
            return

        if wall in self.game.walls:
            self.game.walls.remove(wall)
        else:
            self.game.walls.add(wall)

        self.remake_game()

    def on_keypress(self, event: tk.Event):
        # Value Bindings
        for i in range(1, 10):
            if event.char == str(i):
                self.set_position(i)

        # Hint bindings
        for i, letter in enumerate(self.SHIFT_BINDINGS, 1):
            if event.char == letter:
                self.hint_position(i)

        if event.keysym == "BackSpace":
            self.set_position(0)

    def set_position(self, value: int):
        if (
            self.selected_position is None
            or self.selected_position in self.game.fixed_positions
        ):
            return

        if self.game.grid.get_position(self.selected_position) == value:
            value = 0
        self.solver.perform_action(SetPosition(self.selected_position, value))
        self.redraw()

    def hint_position(self, value: int):
        if (
            self.selected_position is None
            or self.selected_position in self.game.fixed_positions
        ):
            return

        already_hinted = value in self.solver.hints[self.selected_position]
        if already_hinted:
            self.solver.perform_action(RemoveHint(self.selected_position, value))
        else:
            self.solver.perform_action(AddHint(self.selected_position, value))

        self.redraw()


class CellPosition(Enum):
    TOP_LEFT = (0, 0)
    TOP = (0, 1)
    TOP_RIGHT = (0, 2)
    LEFT = (1, 0)
    CENTER = (1, 1)
    RIGHT = (1, 2)
    BOTTOM_LEFT = (2, 0)
    BOTTOM = (2, 1)
    BOTTOM_RIGHT = (2, 2)


class GridCanvas(tk.Canvas):
    class AnnotationType(Enum):
        TEXT = "text"
        HINT = "hint"
        ERROR = "error"

    def __init__(
        self,
        master: tk.Misc,
        dimensions: tuple[int, int],
        size: tuple[int, int],
        on_select_position: Callable[[Position], None],
        on_right_click_position: Callable[[Position], None],
        on_select_wall: Callable[[Wall], None],
        *args,
        **kwargs,
    ) -> None:
        self.dimensions = dimensions
        self.size = size
        width, height = self.size
        super().__init__(master, width=width, height=height, *args, **kwargs)
        self.on_select_position = on_select_position
        self.on_right_click_position = on_right_click_position
        self.on_select_wall = on_select_wall
        self.bind("<Button-1>", self.on_click)
        self.bind("<Button-3>", self.on_right_click)

    def on_click(self, event: tk.Event):
        position = self.pixels_to_position((event.x, event.y))
        self.on_select_position(position)

        wall = self.nearest_wall((event.x, event.y))
        self.on_select_wall(wall)

    def on_right_click(self, event: tk.Event):
        position = self.pixels_to_position((event.x, event.y))
        self.on_right_click_position(position)

    def pixels_to_position(self, pixels: tuple[float, float]) -> Position:
        x, y = pixels
        cell_width, cell_height = self.cell_size()
        return Position(int(y / cell_height), int(x / cell_width))

    def cell_size(self) -> tuple[float, float]:
        rows, cols = self.dimensions
        width, height = self.size
        return width / cols, height / rows

    def position_bbox(self, position: Position) -> tuple[float, float, float, float]:
        cell_width, cell_height = self.cell_size()

        x = cell_width * position.col
        y = cell_height * position.row

        x1 = cell_width * (position.col + 1)
        y1 = cell_height * (position.row + 1)

        return x, y, x1, y1

    def cell_position(
        self, position: Position, offset: CellPosition = CellPosition.CENTER
    ) -> tuple[float, float]:
        x, y, x1, y1 = self.position_bbox(position)

        cell_offset_width = (x1 - x) / 3
        cell_offset_height = (y1 - y) / 3

        offset_row, offset_col = offset.value
        offset_width = offset_col * cell_offset_width
        offset_height = offset_row * cell_offset_height

        cell_width, cell_height = self.cell_size()

        x = cell_width * position.col + (cell_offset_width / 2) + offset_width
        y = cell_height * position.row + (cell_offset_height / 2) + offset_height

        return x, y

    def position_fill(
        self,
        position: Position,
        game: OneUp,
        errors: set[Position],
        selected_position: Optional[Position],
    ):
        if position in game.blocked_positions:
            return "black"

        if position == selected_position and position in errors:
            return "orange"

        if position == selected_position:
            return "yellow"

        if position in errors:
            return "orange"

        return "white"

    def redraw(
        self,
        game: OneUp,
        hints: dict[Position, set[int]],
        solver_hints: dict[Position, set[int]],
        errors: set[Position],
        selected_position: Optional[Position] = None,
        show_solver_hints=False,
    ):
        self.delete(tk.ALL)
        # Draw gridlines

        for row in range(game.size):
            for col in range(game.size):
                position = Position(row, col)
                fill = self.position_fill(position, game, errors, selected_position)
                self.create_rectangle(
                    self.position_bbox(position), fill=fill, outline="black"
                )

                if position in game.blocked_positions:
                    continue

                # Check number
                value = game.grid.get_position(position)
                if value > 0:
                    fill = "red" if position in game.fixed_positions else "black"

                    self.annotate_position(
                        position, str(value), kind=self.AnnotationType.TEXT, fill=fill
                    )
                    continue

                # Otherwise, draw all hints
                for hint in hints.get(position, set()):
                    offset_cell = (hint - 1) // 3, (hint - 1) % 3
                    for offset in CellPosition:
                        if offset.value == offset_cell:
                            self.annotate_position(
                                position,
                                str(hint),
                                offset,
                                kind=self.AnnotationType.HINT,
                            )

                # Solver hints
                if not show_solver_hints:
                    continue

                # Extra hints
                for hint in solver_hints.get(position, set()) - hints[position]:
                    offset_cell = (hint - 1) // 3, (hint - 1) % 3
                    for offset in CellPosition:
                        if offset.value == offset_cell:
                            self.annotate_position(
                                position,
                                str(hint),
                                offset,
                                kind=self.AnnotationType.HINT,
                                fill="blue",
                            )

                # Wrong hints
                for hint in hints[position] - solver_hints.get(position, set()):
                    offset_cell = (hint - 1) // 3, (hint - 1) % 3
                    for offset in CellPosition:
                        if offset.value == offset_cell:
                            self.annotate_position(
                                position,
                                str(hint),
                                offset,
                                kind=self.AnnotationType.HINT,
                                fill="red",
                            )

        for wall in game.walls:
            self.draw_wall(wall)

    def nearest_wall(self, pixels: tuple[float, float]) -> Wall:
        position = self.pixels_to_position(pixels)
        x0, y0, x1, y1 = self.position_bbox(position)

        x, y = pixels
        distances: dict[Direction, float] = {
            Direction.UP: abs(y - y0),
            Direction.DOWN: abs(y - y1),
            Direction.LEFT: abs(x - x0),
            Direction.RIGHT: abs(x - x1),
        }
        min_direction = min(distances.keys(), key=lambda d: distances[d])
        return Wall.from_positions(position, position.neighbour(min_direction))

    def annotate_position(
        self,
        position: Position,
        text: str,
        offset: CellPosition = CellPosition.CENTER,
        kind: AnnotationType = AnnotationType.TEXT,
        fill="black",
    ):
        match kind:
            case self.AnnotationType.HINT:
                font = tk_font.Font(size=10, weight="normal")
            case _:
                font = tk_font.Font(size=18, weight="bold")

        self.create_text(
            self.cell_position(position, offset), text=text, font=font, fill=fill
        )

    def draw_wall(self, wall: Wall) -> None:
        x, y, x1, y1 = self.position_bbox(wall.bounds[1])

        match wall.alignment():
            case Alignment.HORIZONTAL:
                line = (x, y), (x, y1)
            case Alignment.VERTICAL:
                line = (x, y), (x1, y)
            case _:
                return

        self.create_line(line, width=4, fill="black")


class CommandsPane(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        on_step: Callable[[], None],
        on_undo: Callable[[], None],
        on_reset: Callable[[], None],
        on_solve: Callable[[], None],
        toggle_creation: Callable[[], None],
        toggle_solver_hints: Callable[[], None],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(master, *args, **kwargs)

        reset_btn = tk.Button(self, text="Reset", command=on_reset)
        reset_btn.pack(side=tk.LEFT)

        step_btn = tk.Button(self, text="Step", command=on_step)
        step_btn.pack(side=tk.LEFT)

        undo_btn = tk.Button(self, text="Undo", command=on_undo)
        undo_btn.pack(side=tk.LEFT)

        tk.Button(self, text="Solve", command=on_solve).pack(side=tk.LEFT)

        self.create_btn = tk.Checkbutton(
            self, text="Wall Placement", command=lambda: toggle_creation()
        )
        self.create_btn.pack()

        tk.Checkbutton(
            self, text="Show Solver Hints", command=lambda: toggle_solver_hints()
        ).pack()


def start_app(game: OneUp):
    root = tk.Tk()
    app = OneUpApp(root, game)
    root.mainloop()
