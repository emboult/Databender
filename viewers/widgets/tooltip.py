#Floating tooltip widget

import tkinter as ttk
from typing import Optional


class FloatingTooltip:
    def __init__(self, parent: ttk.Misc):
        self.parent = parent
        self._window: Optional[ttk.Toplevel] = None
        self._label: Optional[ttk.Label] = None

    def show(self, text: str, x_root: int, y_root: int):
        if self._window is None:
            # Create the window once
            self._window = ttk.Toplevel(self.parent)
            self._window.overrideredirect(True)
            self._window.attributes('-topmost', True)
            self._label = ttk.Label(
                self._window,
                text=text,
                bg="#ffffe0",
                relief="solid",
                borderwidth=1,
                font=("TkDefaultFont", 9)
            )
            self._label.pack()
        else:
            self._label.config(text=text)

        # Update window to calculate size
        self._window.update_idletasks()
        width = self._window.winfo_width()
        height = self._window.winfo_height()

        # Position to the left of the mouse
        x = x_root - width - 5
        y = y_root + 10

        # ensure not off-screen left
        if x < 0:
            x = 0

        self._window.geometry(f"+{x}+{y}")
        self._window.deiconify()

    def hide(self):
        if self._window:
            self._window.withdraw()

    def destroy(self):
        if self._window:
            self._window.destroy()
            self._window = None
            self._label = None