#Selection management: mouse drag, anchor, and view highlighting

from typing import Optional
from model.state import AppState
from services.event_bus import selection_changed


class SelectionController:
    def __init__(self, state: AppState, view):
        self.state = state
        self.view = view
        self._sel_anchor: Optional[int] = None
        self._last_context_byte: Optional[int] = None

        self.view.set_handlers(
            on_selection_start=self.on_selection_start,
            on_selection_drag=self.on_selection_drag,
            on_selection_end=self.on_selection_end,
        )

        selection_changed.connect(self.on_external_selection)

    def on_external_selection(self, sender, start=None, end=None):
        # Ignore signals from ourselves to avoid loops
        if sender is self:
            return
        self._sel_anchor = None

    def on_selection_start(self, byte_idx: Optional[int]) -> None:
        if byte_idx is None:
            self.clear_selection()
            return
        self._sel_anchor = byte_idx
        self.state.select(byte_idx, byte_idx)
        self._emit_selection()

    def on_selection_drag(self, byte_idx: Optional[int]) -> None:
        if self._sel_anchor is None or byte_idx is None:
            return
        self.state.select(self._sel_anchor, byte_idx)
        self._emit_selection()

    def on_selection_end(self, byte_idx: Optional[int]) -> None:
        if self._sel_anchor is None:
            return
        if byte_idx is None:
            byte_idx = self._sel_anchor
        self.state.select(self._sel_anchor, byte_idx)
        self._last_context_byte = byte_idx
        self._sel_anchor = None
        self._emit_selection()

    def clear_selection(self) -> None:
        self.state.reset_selection()
        self._sel_anchor = None
        self._emit_selection()

    def _emit_selection(self):
        #send selection_changed signal with current range
        sel = self.state.get_selection_range()
        if sel:
            start, end = sel
            selection_changed.send(self, start=start, end=end)
        else:
            selection_changed.send(self, start=None, end=None)

    def set_selection(self, start: int, end: int, context_byte: Optional[int] = None) -> None:
        #Programmatically set selection and update view
        self.state.select(start, end)
        if context_byte is not None:
            self._last_context_byte = context_byte
        self._emit_selection()

    def set_last_context_byte(self, byte_idx: Optional[int]) -> None:
        self._last_context_byte = byte_idx

    def get_last_context_byte(self) -> Optional[int]:
        return self._last_context_byte