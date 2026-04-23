#Main application window with notebook, toolbar, preview, and status

import tkinter as tk
from tkinter import ttk
from model import formats
from viewers.hex_v import HexView
from viewers.latin_v import LatinView
from viewers.widgets.toolbar_v import ToolbarView
from viewers.preview_v import PreviewView
from viewers.widgets.context_menu import ContextMenu
from viewers.widgets.search import SearchBar
from viewers.widgets.status import StatusBar


class EditorView(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self._controller = None

        # Layout: left preview, right notebook
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left: preview area
        self.preview = PreviewView(self)
        self.preview.grid(row=0, column=0, sticky="nsew", padx=(2, 2))

        # Right: notebook with editors
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.nb = ttk.Notebook(right)
        self.nb.grid(row=0, column=0, sticky="nsew")

        # Latin1 editor
        self.latin_view = LatinView(self.nb)
        self.nb.add(self.latin_view, text="Latin1")

        # Hex view
        self.hex_view = HexView(self.nb)
        self.nb.add(self.hex_view, text="Hex")

        # Shared context menu
        self.context_menu = ContextMenu(
            self,
            {
                'randomize': self._on_randomize,
                'invert': self._on_invert,
                'zero': self._on_zero,
                'clear_highlights': self._on_clear_highlights,
                'copy_hex': self._on_copy_hex,
                'paste_hex': self._on_paste_hex,
            }
        )

        # Set context menu callbacks for both views
        self.hex_view.set_context_menu_callback(self.context_menu.show)
        self.latin_view.set_context_menu_callback(self.context_menu.show)

        # Toolbar
        self.toolbar = ToolbarView(
            self,
            on_open=self._on_open_click,
            on_save=self._on_save_click,
            on_reload=self._on_reload_click,
            on_undo=self._on_undo_click,
            on_redo=self._on_redo_click,
            on_tool_selected=self._on_tool_selected,
            on_convert=self._on_convert,
            on_viewer=self._on_viewer_click,
            on_help=self._open_help,
        )
        self.toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=2)

        # Status bar
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

        # Search bar
        self.search_bar = SearchBar(self)
        self.search_bar.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.search_bar.hide()
        self.search_bar.set_handlers(
            on_search=self._on_search,
            on_next=self._on_search_next,
            on_prev=self._on_search_prev,
            on_close=self._on_search_close
        )


        #Για hex: κάνω bind καθώς μόνο για master δεν πιάνει σε hex view, πιθανώς λόγω focus.
        # Search Key bindings
        self.master.bind_all("<Control-f>", self._toggle_search)
        self.hex_view.hexbox.bind("<Control-f>", self._toggle_search)
        self.search_bar.entry.bind("<Control-f>", self._toggle_search)

        # Copy/Paste bindings
        self.master.bind_all("<Control-c>", self._on_copy_hex_event)
        self.master.bind_all("<Control-v>", self._on_paste_hex_event)
        self.hex_view.hexbox.bind("<Control-c>", self._on_copy_hex_event)
        self.hex_view.hexbox.bind("<Control-v>", self._on_paste_hex_event)
        


        # Undo bindings (Ctrl+Z)
        self.master.bind_all("<Control-z>", self._on_undo_event)
        self.hex_view.hexbox.bind("<Control-z>", self._on_undo_event)
        self.master.bind_all("<Control-Z>", self._on_undo_event)
        self.hex_view.hexbox.bind("<Control-Z>", self._on_undo_event)


        # Redo bindings
        self.master.bind_all("<Control-y>", self._on_redo_event)
        self.master.bind_all("<Control-Shift-Z>", self._on_redo_event)
        self.hex_view.hexbox.bind("<Control-y>", self._on_redo_event)
        self.hex_view.hexbox.bind("<Control-Shift-Z>", self._on_redo_event)

        #Εδώ αμα κάνω bind στο hex θα το κάνει 2 φορες; Ε οπότε καλύτερα μόνο στο hex.
        # Open / Save / Reload bindings.
        self.master.bind_all("<Control-o>", lambda e: self._on_open_click())
        self.master.bind_all("<Control-O>", lambda e: self._on_open_click()) 
        self.master.bind_all("<Control-s>", lambda e: self._on_save_click())
        self.master.bind_all("<Control-r>", lambda e: self._on_reload_click())
        self.master.bind_all("<Control-S>", lambda e: self._on_save_click())
        self.master.bind_all("<Control-R>", lambda e: self._on_reload_click())



# --- Public API called by controller ---
    def render(self, snapshot: dict):
        #Update all editors from snapshot
        current = snapshot.get("current", b"")
        fmt = snapshot.get("fmt", "")
        self.toolbar.set_format(fmt)

        fname = snapshot.get("fname", "")
        dirty = snapshot.get("is_dirty", False)
        status = f"{fname or 'Untitled'} ({len(current)} bytes as {fmt})"
        if dirty:
            status += " [modified]"
        self.status_bar.set(status)

    def show_status(self, msg: str):
        #Display a temporary status message
        self.status_bar.set(msg)

    def update_preview(self, data: bytes):
        #Delegate preview update to the preview widget
        self.preview.update_preview(data)

    def get_active_editor_content(self) -> bytes:
        #Return bytes from the active editor (only Latin1)
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "Latin1":
                if self.nb.index(self.nb.select()) == i:
                    return self.latin_view.get_content()
                break
        return None

    def bind_controller(self, controller):
        #Store controller reference for callbacks
        self._controller = controller


# --- Internal event handlers (forward to controller) ---


    def _on_open_click(self):
        if self._controller:
            self._controller.on_open()

    def _on_save_click(self):
        if self._controller:
            self._controller.on_save()

    def _on_reload_click(self):
        if self._controller:
            self._controller.on_reload()

    def _on_undo_click(self):
        if self._controller:
            self._controller.on_undo()

    def _on_redo_click(self):
        if self._controller:
            self._controller.on_redo()

    def _on_tool_selected(self, tool_name):
        if self._controller:
            self._controller.on_tool_selected(tool_name)

    def _on_convert(self, fmt):
        if self._controller and fmt:
            self._controller.on_convert_format(fmt)

    def _on_viewer_click(self):
        if self._controller:
            self._controller.on_open_viewer()

    def _open_help(self):
        if self._controller:
            self._controller.on_open_help()

    # Search bar handlers
    def _on_search(self, query):
        if self._controller:
            self._controller.on_search(query)

    def _on_search_next(self):
        if self._controller:
            self._controller.on_search_next()

    def _on_search_prev(self):
        if self._controller:
            self._controller.on_search_prev()

    def _on_search_close(self):
        self.search_bar.hide()
        if self._controller:
            self._controller.on_search_close()

    def _toggle_search(self, event=None):
        if self.search_bar.winfo_ismapped():
            self.search_bar.hide()
            if self._controller:
                self._controller.on_search_close()
        else:
            self.search_bar.show()
        return "break"

    # Copy/Paste
    def _on_copy_hex(self):
        if self._controller:
            self._controller.copy_hex()

    def _on_paste_hex(self):
        if self._controller:
            self._controller.paste_hex()

    def _is_latin_focused(self):
        try:
            focused = self.focus_get()
            return focused is self.latin_view.text
        except Exception:
            return False

    def _on_copy_hex_event(self, event=None):
        # Παίρνουμε το widget που έχει αυτή τη στιγμή το focus
        focused = self.focus_get()
        
        # Λίστα με τα widgets του editor που επιτρέπεται να κάνουν hex copy
        editor_widgets = [self.hex_view.hexbox, self.latin_view.text]
        
        if focused in editor_widgets:
            self._on_copy_hex()
            return "break" # Σταματάει τη διάδοση του event
        
        return None

    def _on_paste_hex_event(self, event=None):
        focused = self.focus_get()
        editor_widgets = [self.hex_view.hexbox, self.latin_view.text]
        
        if focused in editor_widgets:
            if self._controller:
                source = 'latin' if focused is self.latin_view.text else 'hex'
                self._controller.on_paste(source)
            return "break"
        
        return None
        

    # Context menu actions
    def _on_randomize(self):
        if self._controller:
            self._controller.on_tool_selected("glitch_randomize")

    def _on_invert(self):
        if self._controller:
            self._controller.on_tool_selected("glitch_invert")

    def _on_zero(self):
        if self._controller:
            self._controller.on_tool_selected("glitch_zero")

    def _on_clear_highlights(self):
        if self._controller:
            self._controller.clear_changed_highlights()

    def _on_redo_event(self, event=None):
        self._on_redo_click()
        return "break"
    
    def _on_undo_event(self, event=None):
        self._on_undo_click()
        return "break"