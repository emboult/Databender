import tkinter as tk
from tkinter import ttk
import json
import os


class CollapsibleSection(ttk.Frame):
    def __init__(self, parent, title, content):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)

        self.header = ttk.Frame(self)
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        self.is_expanded = tk.BooleanVar(value=False)
        self.arrow_label = ttk.Label(self.header, text="▶", width=2, cursor="hand2")
        self.arrow_label.grid(row=0, column=0, sticky="w")

        self.title_label = ttk.Label(self.header, text=title, cursor="hand2", font=("Segoe UI", 10, "bold"))
        self.title_label.grid(row=0, column=1, sticky="w", padx=(2, 0))

        self.content_frame = ttk.Frame(self)
        self._build_content(self.content_frame, content)

        self.arrow_label.bind("<Button-1>", lambda e: self.toggle())
        self.title_label.bind("<Button-1>", lambda e: self.toggle())

    def _build_content(self, parent, text):
        lbl = ttk.Label(parent, text=text, justify="left", wraplength=550)
        lbl.pack(anchor="w", padx=(20, 10), pady=(0, 5))

    def toggle(self):
        if self.is_expanded.get():
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self.is_expanded.set(True)
        self.arrow_label.config(text="▼")
        self.content_frame.grid(row=1, column=0, sticky="ew")

    def collapse(self):
        self.is_expanded.set(False)
        self.arrow_label.config(text="▶")
        self.content_frame.grid_forget()


class HelpTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Φόρτωσε το JSON
        json_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'help.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sections = data.get('sections', [])
        except Exception as e:
            sections = [{"title": "Error", "content": f"Could not load help content: {e}"}]

        canvas = tk.Canvas(self, highlightthickness=0)
        yscroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=yscroll.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        # Δημιούργησε sections από το JSON
        for section in sections:
            section_widget = CollapsibleSection(
                scrollable_frame,
                section.get('title', 'Untitled'),
                section.get('content', 'No content')
            )
            section_widget.pack(fill="x", padx=10, pady=2)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(-1 * (event.delta // 120), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))