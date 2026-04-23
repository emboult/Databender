#Search bar with entry, prev/next buttons, close 

from tkinter import ttk


class SearchBar(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.label = ttk.Label(self, text="Find/Go:")
        self.label.pack(side="left", padx=4)

        self.entry = ttk.Entry(self, width=30)
        self.entry.pack(side="left", padx=4)
        self.entry.bind("<Return>", lambda e: self._on_search())

        self.prev_btn = ttk.Button(self, text="Prev", command=self._on_prev)
        self.prev_btn.pack(side="left", padx=2)

        self.next_btn = ttk.Button(self, text="Next", command=self._on_next)
        self.next_btn.pack(side="left", padx=2)

        self.close_btn = ttk.Button(self, text="Close", command=self._on_close)
        self.close_btn.pack(side="left", padx=6)

        self.status = ttk.Label(self, text="")
        self.status.pack(side="left", padx=6)

        self._on_search_cb = None
        self._on_next_cb = None
        self._on_prev_cb = None
        self._on_close_cb = None

    def set_handlers(self, on_search=None, on_next=None, on_prev=None, on_close=None):
        self._on_search_cb = on_search
        self._on_next_cb = on_next
        self._on_prev_cb = on_prev
        self._on_close_cb = on_close

    def show(self):
        self.grid()
        self.entry.focus_set()
        self.entry.select_range(0, "end")

    def hide(self):
        self.entry.delete(0, 'end')
        self.grid_remove()

    def get_query(self) -> str:
        return self.entry.get()

    def set_status(self, msg: str, color: str = None):
        self.status.config(text=msg)
        if color:
            self.status.config(foreground=color)
        else:
            self.status.config(foreground="black")

    def _on_search(self):
        if self._on_search_cb:
            self._on_search_cb(self.entry.get())

    def _on_next(self):
        if self._on_next_cb:
            self._on_next_cb()

    def _on_prev(self):
        if self._on_prev_cb:
            self._on_prev_cb()

    def _on_close(self):
        if self._on_close_cb:
            self._on_close_cb()
        self.hide()