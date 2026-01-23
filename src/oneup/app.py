import tkinter as tk
from typing import Callable


class OneUpApp:
    def __init__(self, root: tk.Tk) -> None:
        root.title("OneUp")
        self.root = root

        self.grid = Grid(root, (8, 8))
        self.grid.configure(width=300, height=300)
        self.grid.pack()

        noop = lambda: None

        self.commands = CommandsPane(root, noop, noop, noop)
        self.commands.pack()


class CommandsPane(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        on_step: Callable,
        on_undo: Callable,
        on_reset: Callable,
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


class Grid(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        dimensions: tuple[int, int],
        *args,
        **kwargs,
    ) -> None:
        self.dimensions = dimensions
        super().__init__(master, *args, **kwargs)


def start_app():
    root = tk.Tk()
    app = OneUpApp(root)
    root.mainloop()
