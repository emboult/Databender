#status bar with autoclear after timeout

from tkinter import ttk


class StatusBar(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.label = ttk.Label(self, relief="sunken", anchor="w")
        self.label.pack(fill="both", expand=True)
        self._after_id = None

    def set(self, text: str, timeout: int = 5000):
        #Set status message, clear after timeout (ms)
        self.label.config(text=text)
        if self._after_id:
            self.after_cancel(self._after_id)
        if timeout > 0:
            self._after_id = self.after(timeout, lambda: self.label.config(text=""))