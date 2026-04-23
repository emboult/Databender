#Tool controller: tool dialogs and model operations

from typing import Callable
import random
import hashlib
from model import ops
from viewers import tool_v as dialogs
from model.state import AppState
from services import event_bus


class ToolController:
    def __init__(self, state, view, history):
        self.state = state
        self.view = view
        self.history = history
        self._preview_active = False
        self._preview_seeds = {}

    def _get_preview_rng(self, tool_name: str, extra: int = 0) -> random.Random:
        if tool_name not in self._preview_seeds:
            self._preview_seeds[tool_name] = random.getrandbits(64)
        return random.Random(self._preview_seeds[tool_name] + extra)

    def _clear_preview_seed(self, tool_name: str):
        if tool_name in self._preview_seeds:
            del self._preview_seeds[tool_name]

    def _make_params_stable(self, params) -> str:
        if not params:
            return ""
        items = []
        for k, v in sorted(params.items()):
            if isinstance(v, bytes):
                v = v.hex()
            items.append(f"{k}:{v}")
        return ",".join(items)

    def _stable_hash(self, params) -> int:
        stable_str = self._make_params_stable(params)
        return int.from_bytes(hashlib.md5(stable_str.encode()).digest()[:8], 'little')

    def apply_tool(self, tool_name: str):
        method_map = {
            "glitch_randomize": self.tool_randomize,
            "glitch_invert": self.tool_invert,
            "glitch_zero": self.tool_zero,
            "whitespace_inject": self.tool_whitespace_inject,
            "repeat_chunks": self.tool_repeat_chunks,
            "pattern_inject": self.tool_pattern_inject,
            "shuffle_blocks": self.tool_shuffle_blocks,
            "hex_pattern_replace": self.tool_hex_pattern_replace,
            "reverse_blocks": self.tool_reverse_blocks,
        }
        method = method_map.get(tool_name)
        if method:
            method()
        else:
            event_bus.status_message_requested.send(self, message=f"Unknown tool: {tool_name}")

    def _apply_simple_tool(self, operation_func, success_message):
        sel = self.state.get_selection_range()
        if not sel:
            event_bus.status_message_requested.send(self, message="No selection")
            return
        start, end = sel
        old_bytes = bytes(self.state.current[start:end+1])
        operation_func(self.state, self.history)
        new_bytes = bytes(self.state.current[start:end+1])
        patch = (start, old_bytes, new_bytes)
        event_bus.state_modified.send(
            self,
            patch=patch,
            update_highlights=True,
            reset_selection=True,
            source='tool'
        )
        event_bus.status_message_requested.send(self, message=success_message)

    def tool_randomize(self):
        self._apply_simple_tool(ops.glitch_randomize, "Randomized selection")

    def tool_invert(self):
        self._apply_simple_tool(ops.glitch_invert, "Inverted selection")

    def tool_zero(self):
        self._apply_simple_tool(ops.glitch_zero, "Zeroed selection")

    def tool_whitespace_inject(self) -> None:
        def apply(state, history=None, count=None, **kwargs):
            return ops.whitespace_inject(state, history, count=count, rng=kwargs.get('rng'))

        self._run_dialog_tool(
            dialogs.ask_whitespace_params,
            apply,
            tool_name="whitespace_inject",
        )

    def tool_repeat_chunks(self) -> None:
        def apply(state, history=None, size=None, repeats=None, **kwargs):
            return ops.repeat_chunks(state, history, size=size, repeats=repeats, rng=kwargs.get('rng'))

        self._run_dialog_tool(
            dialogs.ask_repeat_chunks_params,
            apply,
            tool_name="repeat_chunks"
        )

    def tool_pattern_inject(self) -> None:
        def apply(state, history=None, pattern=None, count=None, **kwargs):
            return ops.pattern_inject(state, history, pattern=pattern, count=count, rng=kwargs.get('rng'))

        self._run_dialog_tool(
            dialogs.ask_pattern_inject_params,
            apply,
            tool_name="pattern_inject"
        )

    def tool_shuffle_blocks(self) -> None:
        def apply(state, history=None, block_size=None, **kwargs):
            return ops.shuffle_blocks(state, history, block_size=block_size, rng=kwargs.get('rng'))

        self._run_dialog_tool(
            dialogs.ask_shuffle_blocks_params,
            apply,
            tool_name="shuffle_blocks"
        )

    def tool_hex_pattern_replace(self) -> None:
        def apply(state, history=None, pattern=None, replace=None, **kwargs):
            return ops.hex_pattern_replace(state, history, pattern=pattern, replace=replace)

        self._run_dialog_tool(
            dialogs.ask_hex_pattern_replace_params,
            apply,
            tool_name="hex_pattern_replace"
        )

    def tool_reverse_blocks(self) -> None:
        def apply(state, history=None, block_size=None, **kwargs):
            return ops.reverse_blocks(state, history, block_size=block_size)

        self._run_dialog_tool(
            dialogs.ask_reverse_blocks_params,
            apply,
            tool_name="reverse_blocks"
        )

    def _run_dialog_tool(
        self,
        dialog_func: Callable,
        apply_func: Callable,
        tool_name: str,
        **kwargs
    ) -> None:
        file_size = len(self.state.get_current_bytes())
        sel_range = self.state.get_selection_range()
        edit_pos = sel_range[0] if sel_range else 0

        def preview_callback(params, enabled=True):
            if not enabled or not params:
                self._restore_preview()
                return
            try:
                temp_state = AppState()
                temp_state.current = bytearray(self.state.get_current_bytes())
                sel_range = self.state.get_selection_range()
                if sel_range:
                    temp_state.select(sel_range[0], sel_range[1])
                else:
                    temp_state.reset_selection()

                rng = self._get_preview_rng(tool_name, extra=self._stable_hash(params))
                apply_func(temp_state, history=None, **params, rng=rng)
                preview_data = bytes(temp_state.current)
                self._show_preview(preview_data)
            except Exception as e:
                event_bus.status_message_requested.send(self, message=f"Preview error: {e}")
                import traceback
                traceback.print_exc()

        # Call the dialog function with the required parameters. The dialog function expects tool_name as a named argument.
        params = dialog_func(
            self.view,
            tool_name=tool_name,
            preview_callback=preview_callback,
            file_size=file_size
        )

        self._restore_preview()

        if params is None:
            return

        event_bus.clear_highlights_requested.send(self)

        rng = self._get_preview_rng(tool_name, extra=self._stable_hash(params))
        apply_func(self.state, history=self.history, **params, rng=rng)
        self._clear_preview_seed(tool_name)

        event_bus.state_modified.send(
            self,
            patch=None,
            update_highlights=False,
            reset_selection=True,
            source=None
        )
        event_bus.status_message_requested.send(self, message="Tool applied")

    def _show_preview(self, data: bytes):
        self._preview_active = True
        event_bus.preview_update_requested.send(self, data=data)

    def _restore_preview(self):
        if self._preview_active:
            self._preview_active = False
            event_bus.preview_update_requested.send(self, data=self.state.get_current_bytes())

    def clear_preview(self):
        self._restore_preview()