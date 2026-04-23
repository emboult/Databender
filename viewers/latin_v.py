#Latin1 view: text area με virtual scrolling και Latin-1 encoding

import tkinter as tk
from tkinter import ttk
from model import formats
from viewers.widgets.tooltip import FloatingTooltip
from typing import Optional, List
from services import event_bus


class LatinView(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.text = tk.Text(self, wrap="none", font=("Consolas", 10), undo=False,
                            bg="white", fg="black", insertbackground="red",
                            exportselection=False, width=1, height=1)
        self.text.grid(row=0, column=0, sticky="nsew")

        self._bytes_per_line = 120
        self._scroll_callback = None

        #scroll SSoT
        self._total_bytes  = self._total_lines = self._top_line = 0
        self._visible_lines = 50
        self._safety_lines  = 3
        self.current_offset = 0
        self.last_rendered_chunk = bytearray() 

        self.v_scroll = ttk.Scrollbar(self, orient="vertical",   command=self._on_vscroll)
        h_scroll      = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll     .grid(row=1, column=0, sticky="ew")
        self.text.configure(xscrollcommand=h_scroll.set)

        #callbacks
        self._edit_callback = self._context_menu_callback = None
        self._selection_start_callback = self._selection_drag_callback = self._selection_end_callback = None
        self._status_callback = None
        self._on_search = self._on_next = self._on_prev = self._on_close = None

        #state
        self._rendering   = False
        self._select_start = self._select_end = None
        self._offset       = 0
        self._latest_indices: set = set()
        self._old_indices:    set = set()
        self._click_pos    = None
        self._drag_started = False
        self._pending_paste_pos = None

        #search
        self._search_matches   = []
        self._search_active    = -1
        self._search_match_len = 1

        self._tooltip = FloatingTooltip(self)

        #tags
        self.text.tag_config("edit_latest",   background="#99e699")
        self.text.tag_config("edit_old",      background="#ddfedd")
        self.text.tag_raise("edit_latest", "edit_old")
        self.text.tag_config("sel",           background="#1E90FF")
        self.text.tag_config("search_match",  background="#FFF59D")
        self.text.tag_config("search_active", background="#FFB74D")
        self.text.tag_config("goto",          background="#ADD8E6")

        #bindings
        self.text.bind("<MouseWheel>", self._on_mousewheel)
        self.text.bind("<Button-4>", self._on_mousewheel)
        self.text.bind("<Button-5>", self._on_mousewheel)
        self.text.bind("<KeyRelease>", self._on_key_release)
        self.text.bind("<Motion>", self._on_motion)
        self.text.bind("<Leave>", lambda e: self._tooltip.hide())
        self.text.bind("<Button-1>", self._on_mouse_button)
        self.text.bind("<B1-Motion>", self._on_mouse_drag)
        self.text.bind("<ButtonRelease-1>", self._on_mouse_release)
        self.text.bind("<B1-Leave>", lambda e: "break")
        self.text.bind("<B1-Enter>", lambda e: "break")
        self.text.bind("<Button-3>", self._on_context_menu)
        self.text.bind("<Control-v>", self._on_paste)
        self.text.bind("<Double-1>", self._on_double_click)

        event_bus.selection_changed.connect(self._on_selection_changed)


    # --- Public API ---

    def bind_scroll(self, callback): self._scroll_callback = callback
    def set_edit_callback(self, cb): self._edit_callback = cb
    def set_context_menu_callback(self, cb): self._context_menu_callback = cb
    def set_status_callback(self, cb): self._status_callback = cb
    def set_selection_handlers(self, on_start, on_drag, on_end):
        self._selection_start_callback = on_start
        self._selection_drag_callback = on_drag
        self._selection_end_callback = on_end
    def set_search_handlers(self, on_search, on_next, on_prev, on_close):
        self._on_search, self._on_next, self._on_prev, self._on_close = on_search, on_next, on_prev, on_close
    def set_search_status(self, msg, color=None):
        if self._status_callback: self._status_callback(msg, color)
    def set_scroll_thumb(self, first, last):
        self.v_scroll.set(first, last)
    def get_content(self) -> bytes:
        return self.text.get("1.0", "end-1c").encode("latin-1", errors="replace")
    def clear(self):
        self._rendering = True
        self.text.delete("1.0", "end")
        self._rendering = False
    def focus(self):
        self.text.focus_set()

    # --- Scroll / virtual render (SSoT) ---

    def _update_metrics(self, data: bytes):
        self._total_bytes = len(data) if data else 0
        self._total_lines = (self._total_bytes + self._bytes_per_line - 1) // self._bytes_per_line

    def load(self, data: bytes, latest: set, old: set):
        #φόρτωση νέων δεδομένων — κρατάει τη θέση scroll
        self._latest_indices, self._old_indices = latest, old
        self._update_metrics(data)
        self._top_line = min(self._top_line, max(0, self._total_lines - self._visible_lines))
        self._render_at_top_line(data, latest, old)

    def handle_scroll(self, args, get_data_fn):
        data = get_data_fn()
        self._update_metrics(data)
        if not self._total_lines: return
        max_top = max(0, self._total_lines - self._visible_lines)
        cmd = args[0] if args else None
        if cmd == 'moveto':
            try: self._top_line = int(float(args[1]) * max_top)
            except Exception: pass
        elif cmd == 'scroll':
            try: n = int(args[1])
            except Exception: n = 0
            step = 1 if (len(args) > 2 and args[2] == 'units') else self._visible_lines
            self._top_line = max(0, min(max_top, self._top_line + n * step))
        else:
            return
        self._render_at_top_line(data, self._latest_indices, self._old_indices)

    def _render_at_top_line(self, data: bytes, latest: set, old: set):
        chunk_lines = self._visible_lines + self._safety_lines * 2
        start_line  = max(0, self._top_line - self._safety_lines)
        offset = min(start_line * self._bytes_per_line, 
                     max(0, self._total_bytes - chunk_lines * self._bytes_per_line))
        self.current_offset = self._offset = offset

        chunk = data[offset:offset + chunk_lines * self._bytes_per_line]
        self.last_rendered_chunk = bytearray(chunk)

        text_data = formats.printable_latin1_str(bytes(chunk))
        lines = [text_data[i:i + self._bytes_per_line]
                 for i in range(0, len(text_data), self._bytes_per_line)]
        self.render_chunk("\n".join(lines), offset)

        if latest or old:
            self.apply_edit_highlights(latest, old, offset)

        max_top = max(0, self._total_lines - self._visible_lines)
        if max_top > 0:
            self.set_scroll_thumb(self._top_line / max_top,
                                  min(1.0, (self._top_line + self._visible_lines) / max_top))
        else:
            self.set_scroll_thumb(0.0, 1.0)

    def render_chunk(self, text_data: str, offset: int = 0):
        self._offset = self.current_offset = offset
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text_data)
        self.text.yview_moveto(0.0)

    def scroll_to_byte(self, byte_idx: int):
        if byte_idx is None: return
        max_top = max(0, self._total_lines - self._visible_lines)
        self._top_line = max(0, min(max_top, byte_idx // self._bytes_per_line - self._safety_lines))
        try:
            pos = self._byte_to_index(byte_idx)
            self.text.see(pos); self.text.mark_set("insert", pos)
        except Exception: pass

    def _on_vscroll(self, *args):
        if self._scroll_callback: self._scroll_callback(*args)

    def _on_mousewheel(self, event):
        if not self._scroll_callback: return "break"
        d = "-1" if (event.num == 4 or getattr(event, 'delta', 0) > 0) else "1"
        self._scroll_callback("scroll", d, "units")
        return "break"


    # --- Selection ---

    def _on_selection_changed(self, sender, start=None, end=None):
        self._select_start, self._select_end = start, end
        self.apply_selection(start, end)

    def apply_selection(self, start: Optional[int], end: Optional[int]):
        self.text.tag_remove("sel", "1.0", "end")
        if start is not None and end is not None and start <= end:
            chunk_end = self._offset + len(self.get_content())
            sp = self._byte_to_index(start)
            ep = self._byte_to_index(end + 1) if (end + 1) < chunk_end else "end"
            try:
                self.text.tag_add("sel", sp, ep)
                self.text.tag_raise("sel")
            except tk.TclError: pass

    def _byte_to_index(self, byte_idx: int) -> str:
        rel = byte_idx - getattr(self, '_offset', 0)
        if rel < 0: return "1.0"
        return f"{rel // self._bytes_per_line + 1}.{rel % self._bytes_per_line}"


    # --- Edit highlights ---

    def apply_edit_highlights(self, latest: set, old: set, offset: int):
        self.text.tag_remove("edit_latest", "1.0", "end")
        self.text.tag_remove("edit_old", "1.0", "end")
        for tag, indices, exclude in (("edit_latest", latest, set()), ("edit_old",    old,    latest)):
            for pos in indices:
                if pos in exclude: continue
                rel = pos - offset
                if rel < 0: continue
                ln  = rel // self._bytes_per_line + 1
                col = rel %  self._bytes_per_line
                try: self.text.tag_add(tag, f"{ln}.{col}", f"{ln}.{col+1}")
                except tk.TclError: pass
        self.text.tag_raise("edit_latest", "edit_old")


    # --- Search & Goto ---

    def apply_search_matches(self, matches: List[int], active_idx: int, match_len: int):
        self._search_matches, self._search_active, self._search_match_len = matches, active_idx, match_len
        self._apply_search_tags()

    def _apply_search_tags(self):
        self.text.tag_remove("search_match",  "1.0", "end")
        self.text.tag_remove("search_active", "1.0", "end")
        if not self._search_matches: return
        cs, ce = self._offset, self._offset + len(self.get_content())
        for i, pos in enumerate(self._search_matches):
            if not (cs <= pos < ce): continue
            end = self._byte_to_index(pos + self._search_match_len) if (pos + self._search_match_len) < ce else "end"
            tag = "search_active" if i == self._search_active else "search_match"
            try:
                self.text.tag_add(tag, self._byte_to_index(pos), end)
                self.text.tag_raise("sel"); self.text.tag_raise("goto")
            except tk.TclError: pass

    def apply_goto_highlight(self, pos: int):
        self.text.tag_remove("goto", "1.0", "end")
        cs, ce = self._offset, self._offset + len(self.get_content())
        if pos is None or not (cs <= pos < ce): return
        end = self._byte_to_index(pos + 1) if (pos + 1) < ce else "end"
        try: self.text.tag_add("goto", self._byte_to_index(pos), end); self.text.tag_raise("goto")
        except tk.TclError: pass

    def clear_goto_highlight(self):
        self.text.tag_remove("goto", "1.0", "end")


    # --- Mouse / keyboard ---

    def _get_byte_at_event(self, event) -> Optional[int]:
        try:
            line, col = map(int, self.text.index(f"@{event.x},{event.y}").split('.'))
            rel = (line - 1) * self._bytes_per_line + col
            ab  = rel + self._offset
            total = len(self.get_content()) + self._offset
            return ab if self._offset <= ab < total else None
        except Exception: return None

    def _on_motion(self, event):
        idx = self.text.index(f"@{event.x},{event.y}")
        try: total_chars = self.text.count("1.0", idx)[0]
        except Exception: self._tooltip.hide(); return
        rel  = total_chars - (int(idx.split('.')[0]) - 1)
        data = self.get_content()
        if not (0 <= rel < len(data)): self._tooltip.hide(); return
        bv = data[rel]
        ab = rel + self._offset
        char = ""
        try:
            c = data[rel:rel+1].decode('latin-1')
            if c.isprintable() or c in '\t\n\r': char = f" '{c}'"
        except Exception: pass
        self._tooltip.show(
            f"Offset: 0x{ab:08X} (@{ab})   Byte: {bv} (0x{bv:02X} / {bv:08b}b){char}",
            event.x_root, event.y_root)

    def _on_key_release(self, event):
        if not self._rendering and self._edit_callback:
            self._edit_callback()

    def _on_mouse_button(self, event):
        self.text.focus_set()
        self.text.mark_set("insert", self.text.index(f"@{event.x},{event.y}"))
        self._click_pos    = self._get_byte_at_event(event)
        self._drag_started = False
        if self._selection_start_callback: self._selection_start_callback(None)
        return "break"

    def _on_double_click(self, event):
        bi = self._get_byte_at_event(event)
        if bi is not None and self._selection_start_callback and self._selection_end_callback:
            self._selection_start_callback(bi); self._selection_end_callback(bi)
        return "break"

    def _on_mouse_drag(self, event):
        if self._click_pos is None: return "break"
        bi = self._get_byte_at_event(event)
        if bi is None: return "break"
        if not self._drag_started:
            if self._selection_start_callback: self._selection_start_callback(self._click_pos)
            self._drag_started = True
        if self._selection_drag_callback: self._selection_drag_callback(bi)
        return "break"

    def _on_mouse_release(self, event):
        if self._drag_started:
            if self._selection_end_callback: self._selection_end_callback(self._get_byte_at_event(event))
        self._click_pos = None; self._drag_started = False
        return "break"

    def _on_context_menu(self, event):
        bi = self._get_byte_at_event(event)
        if bi is not None:
            s, e = self._select_start, self._select_end
            if not (s is not None and e is not None and min(s,e) <= bi <= max(s,e)):
                if self._selection_start_callback: self._selection_start_callback(bi)
                if self._selection_end_callback: self._selection_end_callback(bi)
        else:
            if self._selection_start_callback: self._selection_start_callback(None)
        if self._context_menu_callback: return self._context_menu_callback(event)
        return "break"

    def _on_paste(self, event):
        #καταγράφουμε τη θέση cursor ΠΡΙΝ το default tkinter paste αλλάξει το insert mark
        try:
            line, col = map(int, self.text.index("insert").split('.'))
            rel = (line - 1) * self._bytes_per_line + col
            chunk_len = len(self.get_content())
            self._pending_paste_pos = (rel + self._offset) if 0 <= rel < chunk_len else None
        except Exception:
            self._pending_paste_pos = None
        #forward στον controller traversing το widget tree
        w = self.text
        while w is not None:
            ctrl = getattr(w, '_controller', None)
            if ctrl is not None: ctrl.on_paste('latin'); break
            w = getattr(w, 'master', None)
        return "break"

    def get_cursor_byte_offset(self) -> Optional[int]:
        #προτεραιότητα στο _pending_paste_pos που καταγράφηκε πριν το default action
        pos, self._pending_paste_pos = self._pending_paste_pos, None
        if pos is not None: return pos
        try:
            line, col = map(int, self.text.index("insert").split('.'))
            rel = (line - 1) * self._bytes_per_line + col
            return (rel + self._offset) if 0 <= rel < len(self.get_content()) else None
        except Exception: return None