from typing import Set


class HexController:
    def __init__(self, model, view, bytes_per_line: int = 16, chunk_lines: int = 30):
        self.model = model
        self.view = view

        self.view.bind_scroll(self.on_scroll)
        self.view.set_edit_callback(self._on_edit)

        self._latest_indices: Set[int] = set()
        self._old_indices: Set[int] = set()

    def _on_edit(self, pos: int, new_byte: int):
        # Το scroll state διαχειρίζεται το View· forward γίνεται μέσω state_modified
        pass

    def set_edit_highlights(self, latest_set: Set[int], old_set: Set[int]):
        self._latest_indices = latest_set
        self._old_indices = old_set
        self.view.render_current(self._latest_indices, self._old_indices)

    def load_file(self) -> None:
        self.view.load(self.model.get_current_bytes,
                       self._latest_indices, self._old_indices)

    def refresh_after_model_change(self) -> None:
        self.view.refresh(self.model.get_current_bytes,
                          self._latest_indices, self._old_indices)

    def on_scroll(self, *args) -> None:
        self.view.handle_scroll(args, self.model.get_current_bytes,
                                self._latest_indices, self._old_indices)