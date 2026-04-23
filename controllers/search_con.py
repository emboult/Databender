#search and goto functionality

import re
from typing import List, Optional, Generator
from model.state import AppState



class SearchController:
    def __init__(self, state: AppState, view, selection_ctrl):
        self.state = state
        self.view = view
        self.selection_ctrl = selection_ctrl
        self._matches: List[int] = []
        self._current_idx: int = -1
        self._match_len: int = 1
        self._last_query: str = ""
        self._pattern: bytes = b""
        self._generator: Optional[Generator[int, None, None]] = None
        self._cache_size = 100
        self._last_goto_pos: Optional[int] = None

        self.view.set_search_handlers(
            on_search=self.perform_search,
            on_next=self.find_next,
            on_prev=self.find_prev,
            on_close=self._on_close,
        )

    def _on_close(self):
        #Handle search bar close - clear highlights
        self._clear_cache()
        self._last_query = ""
        self.view.apply_search_matches([], -1, self._match_len)

    def _generate_matches(self, data: bytes, pattern: bytes) -> Generator[int, None, None]:
        pos = 0
        while True:
            pos = data.find(pattern, pos)
            if pos == -1:
                break
            yield pos
            pos += 1

    def _fetch_more_matches(self, direction: str = "forward") -> bool:
        if not self._generator:
            return False
        count = 0
        try:
            while count < self._cache_size:
                pos = next(self._generator)
                self._matches.append(pos)
                count += 1
        except StopIteration:
            self._generator = None
        return count > 0

    def _clear_cache(self):
        #Clear search matches and goto highlight
        self._matches = []
        self._current_idx = -1
        self._generator = None
        self._last_goto_pos = None  # ΝΕΟ
        if hasattr(self.view, 'clear_goto_highlight'):
            self.view.clear_goto_highlight()

    def set_view(self, new_view):
        # Switch the active view for search operations
        # Καθαρισμός goto highlight από παλιό view
        if hasattr(self.view, 'clear_goto_highlight'):
            self.view.clear_goto_highlight()

        self.view = new_view
        self.view.set_search_handlers(
            on_search=self.perform_search,
            on_next=self.find_next,
            on_prev=self.find_prev,
            on_close=self._on_close,
        )
        # Αν υπάρχουν αποθηκευμένα matches, τα εφαρμόζουμε στο νέο view
        if self._matches:
            self.view.apply_search_matches(self._matches, self._current_idx, self._match_len)
        # επαναφορά goto highlight αν υπάρχει
        if self._last_goto_pos is not None:
            self.view.apply_goto_highlight(self._last_goto_pos)

    def perform_search(self, query: str) -> None:
        # καθαρισμός προηγούμενων highlights (και goto και search)
        self._clear_cache()

        query = query.strip()
        if not query:
            self.view.apply_search_matches([], -1, self._match_len)
            return

        self._last_query = query
        data = self.state.get_current_bytes()

        # Offset (hex)
        if query.lower().startswith("0x"):
            try:
                off = int(query, 16)
                off = self.state.clamp_offset(off)
                self._go_to_offset(off)
            except ValueError:
                self.view.set_search_status("Invalid hex offset", "red")
            return

        # Offset (decimal)
        if query.startswith("@"):
            try:
                off = int(query[1:])
                off = self.state.clamp_offset(off)
                self._go_to_offset(off)
            except ValueError:
                self.view.set_search_status("Invalid decimal offset", "red")
            return

        # Hex pattern
        cleaned = query.replace(" ", "")
        if not re.fullmatch(r"[0-9A-Fa-f]+", cleaned) or len(cleaned) % 2 != 0:
            self.view.set_search_status("Invalid hex pattern", "red")
            return

        try:
            pattern = bytes.fromhex(cleaned)
        except Exception:
            self.view.set_search_status("Invalid hex", "red")
            return

        self._pattern = pattern
        self._match_len = len(pattern)

        self._generator = self._generate_matches(data, pattern)
        self._matches = []
        self._current_idx = -1

        if not self._fetch_more_matches():
            self.view.set_search_status("No matches", "red")
            self.view.apply_search_matches([], -1, self._match_len)
            return

        self._current_idx = 0
        self._jump_to_current()
        self.view.set_search_status(f"1/{self._total_matches_estimate()}", None)

    def _total_matches_estimate(self) -> str:
        if self._generator is None:
            return str(len(self._matches))
        else:
            return f"{len(self._matches)}+"

    def find_next(self) -> None:
        if not self._matches:
            return
        if self._current_idx == len(self._matches) - 1 and self._generator is not None:
            if not self._fetch_more_matches():
                self._current_idx = 0
            else:
                self._current_idx += 1
        else:
            self._current_idx = (self._current_idx + 1) % len(self._matches)
        self._jump_to_current()

    def find_prev(self) -> None:
        if not self._matches:
            return
        self._current_idx = (self._current_idx - 1) % len(self._matches)
        self._jump_to_current()

    def _jump_to_current(self) -> None:
        if self._current_idx < 0 or self._current_idx >= len(self._matches):
            return
        pos = self._matches[self._current_idx]
        self.view.scroll_to_byte(pos)
        self.view.apply_search_matches(self._matches, self._current_idx, self._match_len)
        self.selection_ctrl.set_selection(pos, pos + self._match_len - 1, context_byte=pos)
        self.view.set_search_status(
            f"{self._current_idx + 1}/{self._total_matches_estimate()}", None
        )

    def _go_to_offset(self, offset: int) -> None:
        #go to specific offset and highlight it
        self.view.scroll_to_byte(offset)
        self.view.apply_goto_highlight(offset)
        self._last_goto_pos = offset
        self.selection_ctrl.set_last_context_byte(offset)
        self._matches = []
        self._current_idx = -1
        self._generator = None
        self.view.apply_search_matches([], -1, 1)
        self.view.set_search_status(f"Go: 0x{offset:X}" if offset > 0 else f"Go: {offset}", None)