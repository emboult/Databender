#Hex view: offset / hex / latin columns με virtual scrolling

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from model import formats
from viewers.widgets.tooltip import FloatingTooltip
from typing import Set, List, Tuple
from services import event_bus


class HexView(ttk.Frame):
    def __init__(self, parent, bytes_per_line=16, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.bytes_per_line = bytes_per_line
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.text_font = tkfont.Font(family="Consolas", size=10)

        kw = dict(font=self.text_font, bd=0, highlightthickness=0, relief="flat",
                  height=1, wrap="none", exportselection=0)
        self.offsets = tk.Text(self, width=10, state="disabled", bg="#f0f0f0", **kw)
        self.hexbox  = tk.Text(self, width=49, undo=False, bg="white",
                               insertbackground="red", selectbackground="white",
                               inactiveselectbackground="white", **kw)
        self.latin   = tk.Text(self, width=bytes_per_line, bg="#f8f8f8", **kw)

        self.vscroll = ttk.Scrollbar(self, orient="vertical",   command=self._on_vscroll)
        self.hscroll = ttk.Scrollbar(self, orient="horizontal", command=self._on_hscroll)
        self.hexbox.config(yscrollcommand=self._sync_scrolls, xscrollcommand=self.hscroll.set)
        self.latin.config(xscrollcommand=self.hscroll.set)

        self.offsets.grid(row=0, column=0, sticky="nsew")
        self.hexbox .grid(row=0, column=1, sticky="nsew")
        self.latin  .grid(row=0, column=2, sticky="nsew")
        self.vscroll.grid(row=0, column=3, sticky="ns")
        self.hscroll.grid(row=1, column=0, columnspan=3, sticky="ew")

        #state
        self._current_offset = 0
        self._current_chunk  = b""
        self._scroll_callback = None
        self._select_start = self._select_end = None
        self._visible_lines = 80  #fallback μεγάλο για την πρώτη φόρτωση

        #scroll SSoT
        self._total_bytes = self._total_lines = self._top_line = 0
        self._latest_indices: set = set()
        self._old_indices:    set = set()

        #search
        self._search_matches   = []
        self._search_active    = -1
        self._search_match_len = 1

        #edit
        self._edit_pos = self._partial_nibble_pos = None
        self._edit_buffer   = ""
        self._edit_callback = None

        #tags
        for w in (self.hexbox, self.latin):
            w.tag_config("selection",    background="#1E90FF")
            w.tag_config("search_match", background="#FFF59D")
            w.tag_config("search_active",background="#FFB74D")
            w.tag_config("preview",      background="#e6f3ff", foreground="#0066cc")
            w.tag_config("edit_latest",  background="#99e699")
            w.tag_config("edit_old",     background="#ddfedd")
            w.tag_config("goto",         background="#ADD8E6")
        self.hexbox.tag_config("partial", background="#e0e0e0", foreground="#888888")
        self.offsets.tag_config("offset", foreground="#858585")
        self.hexbox.tag_raise("edit_latest", "edit_old")
        self.latin .tag_raise("edit_latest", "edit_old")
        self.hexbox.tag_raise("selection")
        self.latin .tag_raise("selection")

        self._tooltip = FloatingTooltip(self)
        self._on_selection_start = self._on_selection_drag = self._on_selection_end = None
        self._on_search = self._on_next = self._on_prev = self._on_close = None
        self._on_status_message = self._context_menu_cb = None

        self._bind_events()
        self.bind("<Configure>", self._on_resize)
        event_bus.selection_changed.connect(self._on_selection_changed)


    # --- Public API ---

    def bind_scroll(self, callback):                   self._scroll_callback = callback
    def set_edit_callback(self, cb):                   self._edit_callback = cb
    def set_status_callback(self, cb):                 self._on_status_message = cb
    def set_context_menu_callback(self, cb):           self._context_menu_cb = cb
    def set_scroll_params(self, start, end):           self._scroll_start = start; self._scroll_end = end
    def set_search_status(self, msg, color=None):
        if self._on_status_message: self._on_status_message(msg, color)
    def set_scroll_thumb(self, first, last):
        try: self.vscroll.set(first, last)
        except Exception: pass
    def set_search_handlers(self, on_search, on_next, on_prev, on_close):
        self._on_search, self._on_next, self._on_prev, self._on_close = on_search, on_next, on_prev, on_close
    def set_handlers(self, on_selection_start=None, on_selection_drag=None, on_selection_end=None):
        self._on_selection_start = on_selection_start
        self._on_selection_drag  = on_selection_drag
        self._on_selection_end   = on_selection_end


    # --- Scroll / virtual render (SSoT) ---

    def _update_metrics(self, data: bytes):
        self._total_bytes = len(data)
        self._total_lines = (self._total_bytes + self.bytes_per_line - 1) // self.bytes_per_line
        try:
            vh = self.winfo_height()
            lh = self.text_font.metrics('linespace')
            if vh > 10 and lh > 0:
                self._visible_lines = max(1, vh // lh)
        except Exception:
            pass

    def _render_at_top_line(self, data, latest, old):
        offset = min(self._top_line * self.bytes_per_line,
                     max(0, self._total_bytes - self._visible_lines * self.bytes_per_line))
        self.render_chunk(data[offset:offset + self._visible_lines * self.bytes_per_line], offset)
        self.apply_edit_highlights(latest, old, offset)
        max_top = max(0, self._total_lines - self._visible_lines)
        if max_top == 0:
            self.set_scroll_thumb(0.0, 1.0)
        else:
            self.set_scroll_thumb(self._top_line / max_top,
                                  (self._top_line + self._visible_lines) / max(1, self._total_lines))

    def load(self, get_data_fn, latest, old):
        self._latest_indices, self._old_indices = latest, old
        data = get_data_fn()
        self._update_metrics(data)
        self.set_scroll_params(0, self._total_bytes)
        self._top_line = 0
        self._render_at_top_line(data, latest, old)

    def refresh(self, get_data_fn, latest, old):
        self._latest_indices, self._old_indices = latest, old
        data = get_data_fn()
        self._update_metrics(data)
        self.set_scroll_params(0, self._total_bytes)
        self._top_line = min(self._top_line, max(0, self._total_lines - self._visible_lines))
        self._render_at_top_line(data, latest, old)

    def handle_scroll(self, args, get_data_fn, latest, old):
        self._latest_indices, self._old_indices = latest, old
        data = get_data_fn()
        self._update_metrics(data)
        max_top = max(0, self._total_lines - self._visible_lines)
        if not args: return
        cmd = args[0]
        if cmd == 'moveto':
            try:
                frac = max(0.0, min(1.0, float(args[1])))
                self._top_line = max(0, min(max_top, int(frac * self._total_bytes) // self.bytes_per_line))
            except Exception: pass
        elif cmd == 'scroll':
            try: n = int(args[1])
            except Exception: n = 0
            step = 1 if (len(args) > 2 and args[2] == 'units') else self._visible_lines
            self._top_line = max(0, min(max_top, self._top_line + n * step))
        else:
            return
        self._render_at_top_line(data, self._latest_indices, self._old_indices)

    def render_current(self, latest, old):
        self._latest_indices, self._old_indices = latest, old
        self.apply_edit_highlights(latest, old, self._current_offset)

    def scroll_to_byte(self, byte_idx):
        if self._total_bytes > 0:
            self._top_line = max(0, min(max(0, self._total_lines - self._visible_lines),
                                        byte_idx // self.bytes_per_line))
        if self._scroll_callback and self._total_bytes > 0:
            self._scroll_callback("moveto", byte_idx / self._total_bytes)


    # --- Render chunk ---

    def render_chunk(self, data: bytes, offset: int):
        self._current_offset = offset
        self._current_chunk  = data
        off_lines, hex_lines, lat_lines = [], [], []
        for i in range(0, len(data), self.bytes_per_line):
            row = data[i:i + self.bytes_per_line]
            off_lines.append(f"{offset + i:08X}")
            parts = []
            for j, b in enumerate(row):
                parts.append(f"{b:02X}")
                if j < len(row) - 1:
                    parts.append("  " if (j + 1) % 8 == 0 else " ")
            hex_lines.append("".join(parts))
            lat_lines.append(formats.printable_latin1_str(row))

        self.offsets.config(state="normal")
        self.offsets.delete("1.0", "end"); self.offsets.insert("1.0", "\n".join(off_lines))
        self.offsets.config(state="disabled")
        self.hexbox.delete("1.0", "end"); self.hexbox.insert("1.0", "\n".join(hex_lines))
        self.latin.config(state="normal")
        self.latin.delete("1.0", "end");  self.latin.insert("1.0", "\n".join(lat_lines))
        self.latin.config(state="disabled")
        for w in (self.offsets, self.hexbox, self.latin): w.yview_moveto(0.0)
        self._apply_selection_tags()
        self._apply_search_tags()


    # --- Highlights ---

    def apply_edit_highlights(self, latest: Set[int], old: Set[int], base: int):
        self._clear_tags("edit_latest", "edit_old")
        chunk_end = base + self._visible_lines * self.bytes_per_line - 1
        for tag, indices in (("edit_latest", latest), ("edit_old", old)):
            for s, e in self._indices_to_ranges(sorted(i for i in indices if base <= i <= chunk_end)):
                self._tag_byte_range(s, e, tag)

    def _indices_to_ranges(self, indices: List[int]) -> List[Tuple[int, int]]:
        if not indices: return []
        ranges, start, prev = [], indices[0], indices[0]
        for idx in indices[1:]:
            if idx == prev + 1: prev = idx
            else: ranges.append((start, prev)); start = prev = idx
        ranges.append((start, prev))
        return ranges

    def apply_goto_highlight(self, pos):
        self.hexbox.tag_remove("goto", "1.0", "end")
        self.latin .tag_remove("goto", "1.0", "end")
        if pos is not None:
            self._tag_byte_range(pos, pos, "goto")
            self.hexbox.tag_raise("goto"); self.latin.tag_raise("goto")

    def clear_goto_highlight(self):
        self.hexbox.tag_remove("goto", "1.0", "end")
        self.latin .tag_remove("goto", "1.0", "end")

    def apply_search_matches(self, matches, active_idx, match_len):
        self._search_matches, self._search_active, self._search_match_len = matches, active_idx, match_len
        self._apply_search_tags()


    # --- Internal helpers ---

    def _clear_tags(self, *tags):
        for w in (self.hexbox, self.latin):
            for t in tags: w.tag_remove(t, "1.0", "end")

    def _tag_byte_range(self, start_abs, end_abs, tag):
        if start_abs > end_abs: return
        sr, er = start_abs - self._current_offset, end_abs - self._current_offset
        if er < 0 or sr >= self.bytes_per_line * self._visible_lines: return
        def hc(c): return c * 3 + (c // 8)
        r1, r2 = max(0, sr // self.bytes_per_line) + 1, max(0, er // self.bytes_per_line) + 1
        c1, c2 = sr % self.bytes_per_line, er % self.bytes_per_line
        if r1 == r2:
            self.hexbox.tag_add(tag, f"{r1}.{hc(c1)}", f"{r1}.{hc(c2)+2}")
            self.latin .tag_add(tag, f"{r1}.{c1}",     f"{r1}.{c2+1}")
        else:
            self.hexbox.tag_add(tag, f"{r1}.{hc(c1)}", f"{r1}.end")
            self.latin .tag_add(tag, f"{r1}.{c1}",     f"{r1}.end")
            for row in range(r1 + 1, r2):
                self.hexbox.tag_add(tag, f"{row}.0", f"{row}.end")
                self.latin .tag_add(tag, f"{row}.0", f"{row}.end")
            self.hexbox.tag_add(tag, f"{r2}.0", f"{r2}.{hc(c2)+2}")
            self.latin .tag_add(tag, f"{r2}.0", f"{r2}.{c2+1}")

    def _apply_selection_tags(self):
        self._clear_tags("selection")
        for w in (self.hexbox, self.latin): w.tag_remove("sel", "1.0", "end")
        if self._select_start is None or self._select_end is None: return
        s, e = min(self._select_start, self._select_end), max(self._select_start, self._select_end)
        self._tag_byte_range(s, e, "selection")
        self.hexbox.tag_raise("selection"); self.latin.tag_raise("selection")

    def _apply_search_tags(self):
        self._clear_tags("search_match", "search_active")
        if not self._search_matches: return
        s0 = self._current_offset
        s1 = s0 + self._visible_lines * self.bytes_per_line
        for i, pos in enumerate(self._search_matches):
            if s0 <= pos < s1:
                self._tag_byte_range(pos, pos + self._search_match_len - 1,
                                     "search_active" if i == self._search_active else "search_match")
        self.hexbox.tag_raise("selection"); self.hexbox.tag_raise("goto")
        self.latin .tag_raise("selection"); self.latin .tag_raise("goto")

    def _sync_scrolls(self, first, last):
        self.offsets.yview_moveto(first)
        self.latin  .yview_moveto(first)

    def _on_resize(self, event=None):
        try:
            vh = self.winfo_height()
            if vh <= 10: return
            lh = self.text_font.metrics('linespace')
            if lh > 0: self._visible_lines = max(1, vh // lh)
        except Exception: pass

    def _on_selection_changed(self, sender, start=None, end=None):
        self._select_start, self._select_end = start, end
        self._apply_selection_tags()


    # --- Mouse / keyboard ---

    def _get_byte_at_mouse(self, event):
        w = event.widget
        if w is self.offsets: return None
        try: ln, col = map(int, w.index(f"@{event.x},{event.y}").split('.'))
        except tk.TclError: return None
        if w is self.hexbox:
            for b in range(self.bytes_per_line):
                sc = b * 3 + (b // 8)
                if sc <= col < sc + 2:
                    return self._current_offset + (ln - 1) * self.bytes_per_line + b
            return None
        if w is self.latin:
            ab = self._current_offset + (ln - 1) * self.bytes_per_line + col
            return ab if self._current_offset <= ab < self._current_offset + len(self._current_chunk) else None
        return None

    def _get_byte_value_at_mouse(self, event):
        bi = self._get_byte_at_mouse(event)
        if bi is None: return None
        rel = bi - self._current_offset
        return self._current_chunk[rel] if 0 <= rel < len(self._current_chunk) else None

    def _show_tooltip(self, event):
        bv = self._get_byte_value_at_mouse(event)
        if bv is None: self._tooltip.hide(); return
        bi = self._get_byte_at_mouse(event)
        if bi is None: self._tooltip.hide(); return
        char = ""
        if 32 <= bv <= 126: char = f" '{chr(bv)}'"
        elif bv >= 0xA0:
            try: char = f" '{bv.to_bytes(1,'big').decode('latin-1')}'"
            except Exception: pass
        self._tooltip.show(
            f"Offset: 0x{bi:08X} (@{bi})   Byte: {bv} (0x{bv:02X} / {bv:08b}b){char}",
            event.x_root, event.y_root)

    def _on_vscroll(self, *args):
        for w in (self.offsets, self.hexbox, self.latin): w.yview(*args)
        if self._scroll_callback: self._scroll_callback(*args)

    def _on_hscroll(self, *args):
        self.hexbox.xview(*args); self.latin.xview(*args)

    def _on_mousewheel(self, event):
        d = -1 if (getattr(event, 'num', 0) == 4 or getattr(event, 'delta', 0) > 0) else 1
        self._on_vscroll("scroll", d, "units")
        return "break"

    def _on_mouse_button(self, event):
        if self._on_selection_start: self._on_selection_start(self._get_byte_at_mouse(event))
        self.hexbox.focus_set()
        return "break"

    def _on_mouse_drag(self, event):
        if self._on_selection_drag: self._on_selection_drag(self._get_byte_at_mouse(event))
        return "break"

    def _on_mouse_release(self, event):
        if self._on_selection_end: self._on_selection_end(self._get_byte_at_mouse(event))
        return "break"

    def _on_context_menu(self, event):
        bi = self._get_byte_at_mouse(event)
        if bi is not None:
            s, e = self._select_start, self._select_end
            if not (s is not None and e is not None and min(s,e) <= bi <= max(s,e)):
                if self._on_selection_start: self._on_selection_start(bi)
                if self._on_selection_end:   self._on_selection_end(bi)
        else:
            if self._on_selection_start: self._on_selection_start(None)
        if self._context_menu_cb: self._context_menu_cb(event)
        return "break"

    def _on_hex_key(self, event):
        if not self._edit_callback: return "break"
        if self._select_start is None or self._select_start != self._select_end: return "break"
        pos, char, sym = self._select_start, event.char.upper(), event.keysym
        if sym == "BackSpace":
            self._edit_buffer = ""; self._clear_partial_highlight(); return "break"
        if char in "0123456789ABCDEF":
            self._clear_partial_highlight()
            self._edit_buffer += char
            if len(self._edit_buffer) == 2:
                try: self._edit_callback(pos, int(self._edit_buffer, 16))
                except ValueError: pass
                self._edit_buffer = ""
            else:
                self._show_partial_highlight(pos, char)
            return "break"
        if sym in ("Escape", "Return"):
            self._edit_buffer = ""; self._clear_partial_highlight()
        return "break"

    def _show_partial_highlight(self, pos, _char):
        self.hexbox.tag_remove("partial", "1.0", "end")
        rel = pos - self._current_offset
        if not (0 <= rel < len(self._current_chunk)): return
        ln  = rel // self.bytes_per_line + 1
        col = rel %  self.bytes_per_line
        sc  = col * 3 + (col // 8)
        self.hexbox.tag_add("partial", f"{ln}.{sc}", f"{ln}.{sc+1}")
        self._partial_nibble_pos = pos

    def _clear_partial_highlight(self):
        self.hexbox.tag_remove("partial", "1.0", "end")
        self._partial_nibble_pos = None

    def _bind_events(self):
        for w in (self.offsets, self.hexbox, self.latin):
            w.bind("<MouseWheel>", self._on_mousewheel)
            w.bind("<Button-4>", self._on_mousewheel)
            w.bind("<Button-5>", self._on_mousewheel)
            w.bind("<Button-1>", self._on_mouse_button)
            w.bind("<B1-Motion>", self._on_mouse_drag)
            w.bind("<ButtonRelease-1>", self._on_mouse_release)
            w.bind("<Button-3>", self._on_context_menu)
            w.bind("<Motion>", self._show_tooltip)
            w.bind("<Leave>", lambda e: self._tooltip.hide())
            w.bind("<<Selection>>", lambda e: "break")
            w.bind("<B1-Leave>", lambda e: "break")
            w.bind("<B1-Enter>", lambda e: "break")
        self.hexbox.bind("<Key>", self._on_hex_key)