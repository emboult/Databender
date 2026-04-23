#Shared context menu for hex and latin views

import tkinter as ttk


class ContextMenu:
    def __init__(self, parent: ttk.Misc, callbacks: dict):
        self.menu = ttk.Menu(parent, tearoff=False)
        self.menu.add_command(label="Randomize", command=callbacks.get('randomize', lambda: None))
        self.menu.add_command(label="Invert Bits", command=callbacks.get('invert', lambda: None))
        self.menu.add_command(label="Set to Zero", command=callbacks.get('zero', lambda: None))
        self.menu.add_separator()
        self.menu.add_command(label="Copy Hex", command=callbacks.get('copy_hex', lambda: None))
        self.menu.add_command(label="Paste Hex", command=callbacks.get('paste_hex', lambda: None))
        self.menu.add_separator()
        self.menu.add_command(label="Clear Highlights", command=callbacks.get('clear_highlights', lambda: None))

    def show(self, event) -> None:
        self.menu.post(event.x_root, event.y_root)
        return "break"