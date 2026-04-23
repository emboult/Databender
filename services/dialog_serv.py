"""Dialog service – handles file dialogs, message boxes, and confirmations."""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
from typing import Optional, List, Tuple

# Persistent state for save dialog
_last_save_dir: Optional[str] = None


def ask_open_filename(
    parent: tk.Misc,
    title: str = "Open",
    filetypes: Optional[List[Tuple[str, str]]] = None
) -> str:
    """Show an open file dialog. Returns selected path or empty string."""
    if filetypes is None:
        filetypes = [("All files", "*.*")]
    return filedialog.askopenfilename(
        parent=parent,
        title=title,
        filetypes=filetypes
    )


def ask_save_filename(
    parent: tk.Misc,
    title: str = "Save As",
    initialfile: str = "",
    filetypes: Optional[List[Tuple[str, str]]] = None,
    defaultextension: str = ".png",
    initialdir: Optional[str] = None
) -> str:
    global _last_save_dir, _last_save_filter
    filename = filedialog.asksaveasfilename(
        parent=parent,
        title=title,
        initialdir=initialdir or _last_save_dir,
        initialfile=initialfile,
        filetypes=filetypes or [("PNG files", "*.png"), ("All files", "*.*")],
        defaultextension=defaultextension
    )
    if filename:
        _last_save_dir = os.path.dirname(filename)
    return filename


def show_error(parent: tk.Misc, message: str, title: str = "Error") -> None:
    """Display an error message box."""
    messagebox.showerror(title, message, parent=parent)


def show_info(parent: tk.Misc, message: str, title: str = "Information") -> None:
    """Display an information message box."""
    messagebox.showinfo(title, message, parent=parent)


def ask_yesno(parent: tk.Misc, message: str, title: str = "Confirm") -> bool:
    """Display a yes/no confirmation dialog. Returns True for Yes, False for No."""
    return messagebox.askyesno(title, message, parent=parent)