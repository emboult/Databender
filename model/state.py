from __future__ import annotations # gia na treksei to exe logw ths grammhs 24
from dataclasses import dataclass, field
from typing import Optional, Tuple
from .selection import Selection
from . import formats



@dataclass
class AppState:
    fname: Optional[str] = None
    original: Optional[bytes] = None
    current: bytearray = field(default_factory=bytearray)
    fmt: Optional[str] = None
    selection: Selection = field(default_factory=Selection)
    last_edit_pos: Optional[int] = None 

    def load(self, fname: Optional[str], data: Optional[bytes], fmt: Optional[str] = None):
        self.fname = fname
        self.original = data if data is None or isinstance(data, (bytes, bytearray)) else bytes(data)
        self.current = bytearray(self.original) if self.original is not None else bytearray()
        self.fmt = fmt
        self.reset_selection()
        self.last_edit_pos = None 

    def set_bytes(self, start: int, new_bytes: bytes, replace_len: int | None = None):
        if start is None:
            raise ValueError("start index required")
        if start < 0:
            raise ValueError("start must be >= 0")
        if new_bytes is None:
            raise ValueError("new_bytes required")

        if replace_len is None:
            replace_len = len(new_bytes)
        if replace_len < 0:
            raise ValueError("replace_len must be >= 0")

        cur = self.current
        end = min(start + replace_len, len(cur))

        if start > len(cur):
            cur.extend(b"\x00" * (start - len(cur)))

        cur[start:end] = new_bytes

        if 0 <= start < len(self.current):
            self.last_edit_pos = start

    def get_current_bytes(self) -> bytes:
        return bytes(self.current)

    def is_dirty(self) -> bool:
        if self.original is None or self.current is None:
            return False
        return bytes(self.current) != self.original

    # --- Clamping methods -------------------------------------------------
    def clamp_offset(self, offset: int) -> int:
        # Return a valid byte offset within [0, len(current)-1]
        if not self.current:
            return 0
        return max(0, min(offset, len(self.current) - 1))

    def clamp_range(self, start: int, end: int) -> Tuple[int, int]:
        # Return (start, end) with start ≤ end and inside current bounds.
        if not self.current:
            return (0, 0)
        length = len(self.current)
        start = max(0, min(start, length))
        end = max(0, min(end, length))
        if start > end:
            start, end = end, start
        return (start, end)
    
    # ---------------------------------------------------------------------

    def decode(self, mode: str = "raw"):
        if self.current is None:
            return None
        return formats.decode_bytes(bytes(self.current), fmt=self.fmt, mode=mode)

    def encode(self, target_format: Optional[str] = None, mode: str = "raw") -> bytes:
        tf = target_format or self.fmt
        if mode == "raw":
            return formats.encode_bytes(bytes(self.current), tf or "")
        return formats.encode_bytes(self.decode(mode=mode), tf or "")

    def select(self, a: Optional[int], b: Optional[int]):
        # Set selection, clamping indices to valid range.
        if a is not None:
            a = self.clamp_offset(a)
        if b is not None:
            b = self.clamp_offset(b)
        self.selection = Selection(a, b)

    def reset_selection(self):
        self.selection = Selection()

    def get_selection_range(self):
        # Return (start, end) if selection exists and is non‑empty, else None
        if not self.selection or self.selection.is_empty():
            return None
        start, end = self.selection.start, self.selection.end
        # start <= end
        return (min(start, end), max(start, end))