# Latin-1 editor controller: handles edits, diff, and updates model/history.

from utils.debouncer import Debouncer
from utils.diffing import find_changed_region
from services import event_bus


class LatinController:
    def __init__(self, state, view, history, selection_ctrl):
        self.state = state
        self.view = view
        self.history = history
        self.selection_ctrl = selection_ctrl
        self._debouncer = Debouncer(view.master, delay_ms=600)

        self.view.set_edit_callback(self._on_edit)
        self.view.bind_scroll(self._on_scroll)

        self.view.set_selection_handlers(
            on_start=selection_ctrl.on_selection_start,
            on_drag=selection_ctrl.on_selection_drag,
            on_end=selection_ctrl.on_selection_end
        )

        self._latest_indices: set = set()
        self._old_indices: set = set()

    # --- Scroll: απλά forward στο View ---

    def _on_scroll(self, *args):
        self.view.handle_scroll(args, self.state.get_current_bytes)

    # --- Δημόσιες μέθοδοι ---

    def render(self, data: bytes):
        self.view.load(data, self._latest_indices, self._old_indices)

    def set_edit_highlights(self, latest_set: set, old_set: set):
        self._latest_indices = latest_set or set()
        self._old_indices = old_set or set()
        # Ενημέρωση και στο view ώστε το scroll να χρησιμοποιεί τα νέα highlights
        self.view._latest_indices = self._latest_indices
        self.view._old_indices    = self._old_indices
        self.view.apply_edit_highlights(self._latest_indices, self._old_indices, self.view.current_offset)

    def clear(self):
        self.view.clear()

    # --- Επεξεργασία αλλαγών (τοπικό diffing) ---

    def _on_edit(self):
        self._debouncer.debounce(self._apply_changes)

    def _apply_changes(self):
        new_text = self.view.get_content()

        if isinstance(new_text, bytes):
            new_text = new_text.decode('latin-1', errors='replace')
        clean_new_text = new_text.replace('\n', '')

        old_chunk_bytes = self.view.last_rendered_chunk
        old_text = "".join(
            chr(b) if 32 <= b <= 126 or b >= 0xA0 else '.'
            for b in old_chunk_bytes
        )

        if old_text == clean_new_text:
            return

        start, old_end, new_end = find_changed_region(old_text, clean_new_text)

        before_segment = old_chunk_bytes[start:old_end]
        after_segment = clean_new_text[start:new_end].encode('latin-1', errors='replace')

        absolute_start = self.view.current_offset + start
        patch = (absolute_start, before_segment, after_segment)

        if self.history:
            self.history.push(patch)

        self.state.set_bytes(absolute_start, after_segment, replace_len=len(before_segment))

        event_bus.state_modified.send(
            self,
            patch=patch,
            update_highlights=True,
            reset_selection=True,
            source='latin'
        )
        event_bus.status_message_requested.send(self, message="Latin edit")

        # αναγκάζω το view να ξανασχεδιαστεί άμεσα
        self.view.load(self.state.get_current_bytes(), self._latest_indices, self._old_indices)