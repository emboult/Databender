#Preview panel widget – displays image thumbnail or status messages

import tkinter as tk
from tkinter import ttk
from services import preview_serv

try:
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class PreviewView(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)   # το label της εικόνας παίρνει όλο το χώρο
        self.rowconfigure(1, weight=0)   # το info label έχει σταθερό ύψος

        # Label που θα δείχνει την εικόνα ή το μήνυμα (καταλαμβάνει όλο το χώρο)
        self.label = tk.Label(
            self,
            anchor="center",
            background="#111",
            fg="#eee",
            text="Preview",
            font=("TkDefaultFont", 10),
            justify="center",
            wraplength=500
        )
        self.label.grid(row=0, column=0, sticky="nsew")

        # Info label – πάντα στο κάτω μέρος, πάνω από το label
        self.info = tk.Label(
            self,
            text="Preview is limited. Open in 'View' for full image. This is especially true for PNG and GIF",
            foreground="#bebebe",
            background="#111",
            font=("TkDefaultFont", 8),
            anchor="w",
            padx=4,
            pady=2
        )
        self.info.grid(row=1, column=0, sticky="ew")

        # Store the current PhotoImage to prevent garbage collection
        self._current_image = None

    def update_preview(self, data: bytes):
        # update with new image data.
        if not PIL_AVAILABLE:
            self.label.config(image="", text="Preview (Pillow missing)", fg="#e66")
            self._current_image = None
            return

        try:
            img, error = preview_serv.generate_image_preview(data)
            if img is None:
                hint = "\n\nTry opening in 'View' (external viewer)"
                self.label.config(
                    image="",
                    text=f"Preview not available\n{error}{hint}",
                    fg="#e66"
                )
                self._current_image = None
            else:
                self.label.config(image=img, text="")
                self._current_image = img
        except Exception as e:
            hint = "\n\nTry opening in 'View' (external viewer)"
            self.label.config(
                image="",
                text=f"Unexpected preview error:\n{e}{hint}",
                fg="#e66"
            )
            self._current_image = None

    def clear(self):
        #clear the preview, showing default text
        self.label.config(image="", text="Preview")
        self._current_image = None