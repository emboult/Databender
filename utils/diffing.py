
from typing import Tuple


def find_changed_region(old: bytes, new: bytes) -> Tuple[int, int, int]:
    # Find first differing byte
    min_len = min(len(old), len(new))
    start = 0
    while start < min_len and old[start] == new[start]:
        start += 1

    # Find last differing byte (scan from the end)
    old_end = len(old)
    new_end = len(new)
    max_match = min(len(old) - start, len(new) - start)
    i = 1
    while i <= max_match and old[-i] == new[-i]:
        old_end -= 1
        new_end -= 1
        i += 1

    return start, old_end, new_end