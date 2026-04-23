# toolbar με κουμπια και dropdowns για εργαλεια και μετατροπή φορματ.

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ToolbarView(ttk.Frame):

    def __init__(
        self,
        master,
        on_open: Callable[[], None],
        on_save: Callable[[], None],
        on_reload: Callable[[], None],
        on_undo: Callable[[], None],
        on_redo: Callable[[], None],
        on_tool_selected: Callable[[str], None],
        on_convert: Callable[[str], None],
        on_viewer: Callable[[], None],
        on_help: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, **kwargs)

        # Store callbacks
        self._on_open = on_open
        self._on_save = on_save
        self._on_reload = on_reload
        self._on_undo = on_undo
        self._on_redo = on_redo
        self._on_tool_selected_cb = on_tool_selected
        self._on_convert = on_convert
        self._on_viewer = on_viewer
        self._on_help = on_help

        # Build UI
        self._create_widgets()

    def _create_widgets(self):
        # File buttons
        ttk.Button(self, text="Open", command=self._on_open).grid(row=0, column=0, padx=2)
        ttk.Button(self, text="Save", command=self._on_save).grid(row=0, column=1, padx=2)
        ttk.Button(self, text="Reload", command=self._on_reload).grid(row=0, column=2, padx=2)

        # Edit buttons
        ttk.Button(self, text="Undo", command=self._on_undo).grid(row=0, column=3, padx=2)
        ttk.Button(self, text="Redo", command=self._on_redo).grid(row=0, column=4, padx=2)

        # Tools dropdown - changed to Combobox like Convert
        ttk.Label(self, text="Tools:").grid(row=0, column=5, padx=(10, 2))
        self.tools_var = tk.StringVar()
        self.tools_combo = ttk.Combobox(
            self,
            textvariable=self.tools_var,
            values=[
                "Hex Pattern Replace",
                "Pattern Inject",
                "Whitespace Inject",
                "Repeat Chunks",
                "Shuffle Blocks",
                "Reverse Blocks"
            ],
            state="readonly",
            width=16
        )
        self.tools_combo.grid(row=0, column=6, padx=2)
        self.tools_combo.bind("<<ComboboxSelected>>", self._on_tool_selected)

        # Format conversion
        ttk.Label(self, text="Convert:").grid(row=0, column=7, padx=(10, 2))
        self.convert_var = tk.StringVar(value="PNG")
        self.convert_combo = ttk.Combobox(
            self,
            textvariable=self.convert_var,
            values=["JPEG", "PNG", "BMP", "GIF", "WEBP", "TIFF", "PPM", "TGA"],
            state="readonly",
            width=8
        )
        self.convert_combo.grid(row=0, column=8, padx=2)
        self.convert_combo.bind("<<ComboboxSelected>>", self._on_convert_combo)

        # External viewer and help
        ttk.Button(self, text="View", command=self._on_viewer).grid(row=0, column=9, padx=2)
        ttk.Button(self, text="Help", command=self._on_help).grid(row=0, column=10, padx=2)

    def _on_tool_selected(self, event=None):
        #Called when a tool is selected from the combobox
        selected = self.tools_var.get()
        if selected and self._on_tool_selected_cb:
            # Map display name back to command name
            tool_map = {
                "Hex Pattern Replace": "hex_pattern_replace",
                "Pattern Inject": "pattern_inject",
                "Whitespace Inject": "whitespace_inject",
                "Repeat Chunks": "repeat_chunks",
                "Shuffle Blocks": "shuffle_blocks",
                "Reverse Blocks": "reverse_blocks",
            }
            cmd = tool_map.get(selected)
            if cmd:
                self._on_tool_selected_cb(cmd)
            # Reset selection after use
            self.tools_var.set("")

    def _on_convert_combo(self, event=None):
        #called when a format is selected from the combobox
        self._on_convert(self.convert_var.get())

    def set_format(self, fmt: str):
        #update the combobox to reflect the current image format
        if fmt and fmt in self.convert_combo["values"]:
            self.convert_var.set(fmt)