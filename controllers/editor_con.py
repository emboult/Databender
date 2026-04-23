#main controller

from typing import Any
from model.state import AppState
from model.history import History
from controllers.file_con import FileController
from controllers.hex_con import HexController
from controllers.selection_con import SelectionController
from controllers.search_con import SearchController
from controllers.tool_con import ToolController
from controllers.latin_con import LatinController
from services import viewer_serv, clipboard_serv
from services import event_bus
from utils.debouncer import Debouncer



class EditorController:
    def __init__(self, state: AppState, history: History, view: Any):
        self.state = state
        self.history = history
        self.view = view

        # Subcontrollers
        self.file_ctrl = FileController(state, view, history)
        self.hex_ctrl = HexController(state, view.hex_view)
        self.selection_ctrl = SelectionController(state, view.hex_view)
        self.search_ctrl = SearchController(state, view.hex_view, self.selection_ctrl)
        self.tool_ctrl = ToolController(state, view, history)
        self.latin_ctrl = LatinController(state, view.latin_view, history, self.selection_ctrl)

        #Preview throttling
        self._preview_debouncer = Debouncer(view.master, delay_ms=50)

        # Connect view callbacks
        view.hex_view.set_status_callback(self._on_search_status)
        view.hex_view.set_edit_callback(self._on_hex_edit)

        # Connect to event bus
        event_bus.status_message_requested.connect(self._on_status_requested)
        event_bus.preview_update_requested.connect(self._on_preview_requested)
        event_bus.file_loaded.connect(self._on_file_loaded)
        event_bus.state_modified.connect(self._on_state_modified)
        event_bus.clear_highlights_requested.connect(self._on_clear_highlights_requested)

        #binding για αλλαγή tab
        view.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        #Initial render
        self.refresh_all()

    def _on_tab_changed(self, event=None):
        current_tab = self.view.nb.select()
        tab_text = self.view.nb.tab(current_tab, "text")

        if tab_text == "Hex":
            target_view = self.view.hex_view
        elif tab_text == "Latin1":
            target_view = self.view.latin_view
        else:
            return

        self.search_ctrl.set_view(target_view)

        # Jump to last edited position
        if self.state.last_edit_pos is not None:
            target_view.scroll_to_byte(self.state.last_edit_pos)
            self.selection_ctrl.set_selection(
                self.state.last_edit_pos,
                self.state.last_edit_pos
            )

    # --- Callbacks from views ---

    def _on_search_status(self, msg: str, color: str = None):
        self.set_status(msg)

    def _on_hex_edit(self, pos: int, new_byte: int):
        old_bytes = self.state.get_current_bytes()
        if pos >= len(old_bytes):
            return
        old_byte = old_bytes[pos]
        if old_byte == new_byte:
            return
        #apply change
        self.state.current[pos] = new_byte
        patch = (pos, bytes([old_byte]), bytes([new_byte]))
        self._push_history_patch(*patch)
        #emit event (no selection reset, update highlights)
        event_bus.state_modified.send(
            self,
            patch=patch,
            update_highlights=True,
            reset_selection=False,
            source='edit'
        )
        self.set_status(f"Edited byte at 0x{pos:X}")

    # --- Snapshot / render ---

    def build_snapshot(self) -> dict:
        return {
            'fname': self.state.fname,
            'fmt': self.state.fmt,
            'original': self.state.original,
            'current': self.state.get_current_bytes(),
            'selection': self.state.get_selection_range(),
            'is_dirty': self.state.is_dirty(),
        }

    def refresh_all(self, source: str = None) -> None:
        # Rebuild snapshot and call view.render(). Skip Latin render if source is 'latin'.
        if self.view is None:
            return
        snapshot = self.build_snapshot()
        try:
            self.view.render(snapshot)
        except Exception as e:
            self.set_status(f"Render error: {e}")
        # Update Latin view only if the change did not originate from it
        if source != 'latin':
            self.latin_ctrl.render(snapshot['current'])

    def set_status(self, msg: str) -> None:
        if hasattr(self.view, 'show_status'):
            self.view.show_status(msg)

    # --- History helper ----

    def _push_history_patch(self, start: int, before: bytes, after: bytes) -> None:
        if self.history:
            self.history.push((start, before, after))

    # --- Highlight management ---

    def _refresh_highlights(self):
        # Read edit highlights from history and forward to subcontrollers
        latest_range, older_ranges = self.history.get_edit_highlights()
        # Convert to sets for hex controller
        latest_set = set()
        if latest_range:
            start, end = latest_range
            latest_set = set(range(start, end + 1))
        old_set = set()
        for start, end in older_ranges:
            old_set.update(range(start, end + 1))
        self.hex_ctrl.set_edit_highlights(latest_set, old_set)
        self.latin_ctrl.set_edit_highlights(latest_set, old_set)

    def clear_changed_highlights(self):
        self.history.clear_edit_highlights()
        self._refresh_highlights()

    # --- Public API (called from view) ---

    def on_open(self) -> None:
        self.file_ctrl.on_open()

    def on_save(self) -> None:
        self.file_ctrl.on_save()

    def on_reload(self) -> None:
        self.file_ctrl.on_reload()

    def on_undo(self) -> None:
        if not self.history.can_undo():
            self.set_status("Nothing to undo")
            return
        patch = self.history.undo(self.state)
        if patch:
            start, before, _ = patch
            if before:
                self.selection_ctrl.set_selection(start, start + len(before) - 1)
            event_bus.state_modified.send(
                self,
                patch=patch,
                update_highlights=True,
                reset_selection=False,
                source='undo'
            )
            self.set_status("Undo applied")
        else:
            self.set_status("Nothing to undo")

    def on_redo(self) -> None:
        if not self.history.can_redo():
            self.set_status("Nothing to redo")
            return
        patch = self.history.redo(self.state)
        if patch:
            start, before, _ = patch
            if before:
                self.selection_ctrl.set_selection(start, start + len(before) - 1)
            event_bus.state_modified.send(
                self,
                patch=patch,
                update_highlights=True,
                reset_selection=False,
                source='redo'
            )
            self.set_status("Redo applied")
        else:
            self.set_status("Nothing to redo")

    def on_convert_format(self, target_format: str) -> None:
        if not self.state.current:
            self.set_status("No image data to convert")
            return

        old_bytes = self.state.get_current_bytes()
        try:
            new_bytes = self.state.encode(target_format, mode='image')
        except Exception as e:
            self.set_status(f"Conversion error: {e}")
            return

        patch = (0, old_bytes, new_bytes)
        self._push_history_patch(*patch)
        self.state.current = bytearray(new_bytes)
        self.state.original = new_bytes
        self.state.fmt = target_format

        #clear any leftover changed highlights
        self.history.clear_edit_highlights()
        self._refresh_highlights()

        #reset selection
        self.selection_ctrl.clear_selection()

        # clear search highlights from both views
        if hasattr(self, 'search_ctrl'):
            # Αποθήκευση του query αν υπάρχει
            last_query = getattr(self.search_ctrl, '_last_query', '')
            self.search_ctrl._clear_cache()
            
            # Αν υπήρχε ενεργό search, το επαναφέρουμε ΑΜΕΣΩΣ μετά το state_modified
            if last_query and last_query.strip():
                # Το state_modified θα κάνει render, οπότε μετά από αυτό κάνουμε search
                event_bus.state_modified.send(
                    self,
                    patch=patch,
                    update_highlights=False,
                    reset_selection=True,
                    source='convert'
                )
                self.search_ctrl.perform_search(last_query)
            else:
                # Αν δεν υπήρχε search, καθαρίζουμε κανονικά
                if hasattr(self.view, 'hex_view'):
                    self.view.hex_view.apply_search_matches([], -1, 1)
                if hasattr(self.view, 'latin_view'):
                    self.view.latin_view.apply_search_matches([], -1, 1)
                event_bus.state_modified.send(
                    self,
                    patch=patch,
                    update_highlights=False,
                    reset_selection=True,
                    source='convert'
                )

    def on_open_viewer(self) -> None:
        if not self.state.current:
            self.set_status("No image data to view")
            return
        try:
            viewer_serv.open_in_viewer(
                self.state.get_current_bytes(),
                self.state.fmt
            )
        except Exception as e:
            self.set_status(f"Viewer error: {e}")

    def on_tool_selected(self, tool_name: str) -> None:
        self.tool_ctrl.apply_tool(tool_name)

    def on_search(self, query: str) -> None:
        self.search_ctrl.perform_search(query)

    def on_search_next(self) -> None:
        self.search_ctrl.find_next()

    def on_search_prev(self) -> None:
        self.search_ctrl.find_prev()

    def on_search_close(self) -> None:
        self.search_ctrl._on_close()

    def on_paste(self, source: str = 'hex') -> None:
        if source == 'latin':
            self.paste_latin()
        else:
            self.paste_hex()

    def on_open_help(self) -> None:
        import tkinter as tk
        from viewers.help import HelpTab
        win = tk.Toplevel(self.view.master)
        win.title("Help")
        win.geometry("700x560")
        HelpTab(win).pack(fill="both", expand=True)

    # --- Copy / Paste ----

    def copy_hex(self) -> None:
        sel = self.state.get_selection_range()
        if not sel:
            self.set_status("No selection")
            return
        start, end = sel
        data = self.state.get_current_bytes()[start:end+1]
        hex_str = data.hex()
        try:
            clipboard_serv.copy_to_clipboard(hex_str)
            self.set_status("Copied as hex")
        except RuntimeError as e:
            self.set_status(str(e))

    def _read_hex_from_clipboard(self):
        # Διαβάζει και parse-άρει hex από clipboard
        try:
            txt = clipboard_serv.paste_from_clipboard()
        except RuntimeError as e:
            self.set_status(str(e))
            return None
        if not txt:
            self.set_status("Clipboard empty or invalid")
            return None
        try:
            return clipboard_serv.parse_hex(txt)
        except ValueError:
            self.set_status("Invalid hex in clipboard")
            return None

    def _paste_bytes_at(self, pos: int, new_bytes: bytes, label: str = "Pasted hex") -> None:
        # Εφαρμόζει paste σε θέση pos, ενημερώνει model/history/event bus.
        old_bytes = self.state.get_current_bytes()
        self.state.set_bytes(pos, new_bytes, replace_len=len(new_bytes))
        patch = (pos, old_bytes[pos:pos+len(new_bytes)], new_bytes)
        self._push_history_patch(*patch)
        event_bus.state_modified.send(
            self,
            patch=patch,
            update_highlights=True,
            reset_selection=True,
            source='edit'
        )
        self.set_status(label)

    def paste_hex(self) -> None:
        new_bytes = self._read_hex_from_clipboard()
        if new_bytes is None:
            return
        sel = self.state.get_selection_range()
        pos = sel[0] if sel else (self.selection_ctrl.get_last_context_byte() or 0)
        self._paste_bytes_at(pos, new_bytes, "Pasted hex")

    def paste_latin(self) -> None:
        new_bytes = self._read_hex_from_clipboard()
        if new_bytes is None:
            return
        # Προτεραιότητα: θέση cursor του latin view
        pos = None
        if hasattr(self.view, 'latin_view') and hasattr(self.view.latin_view, 'get_cursor_byte_offset'):
            pos = self.view.latin_view.get_cursor_byte_offset()
        if pos is None:
            sel = self.state.get_selection_range()
            pos = sel[0] if sel else (self.selection_ctrl.get_last_context_byte() or 0)
        self._paste_bytes_at(pos, new_bytes, "Pasted (latin)")

    # --- Preview live (throttled) ---

    def update_preview_live(self, data: bytes) -> None:
        self._preview_debouncer.debounce(lambda: self._do_live_preview(data))

    def _do_live_preview(self, data: bytes) -> None:
        if hasattr(self.view, 'update_preview'):
            self.view.update_preview(data)

    def update_preview(self, data: bytes) -> None:
        if hasattr(self.view, 'update_preview'):
            self.view.update_preview(data)

    # --- Event bus handlers ----
    def _on_status_requested(self, sender, message):
        self.set_status(message)

    def _on_preview_requested(self, sender, data):
        self.update_preview(data)

    def _on_file_loaded(self, sender):
        self.hex_ctrl.load_file()
        self.update_preview(self.state.get_current_bytes())
        self.refresh_all()
        self.history.clear_edit_highlights()
        self._refresh_highlights()
        self.selection_ctrl.clear_selection()

    def _on_state_modified(self, sender, patch, update_highlights, reset_selection, source):
        if reset_selection:
            self.selection_ctrl.clear_selection()
        self.hex_ctrl.refresh_after_model_change()
        self.update_preview(self.state.get_current_bytes())
        self.refresh_all(source=source)
        if update_highlights:
            self._refresh_highlights()
        if hasattr(self, 'tool_ctrl'):
            self.tool_ctrl.clear_preview()

    def _on_clear_highlights_requested(self, sender):
        self.clear_changed_highlights()