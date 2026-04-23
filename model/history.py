from typing import List, Tuple, Optional

Patch = Tuple[int, bytes, bytes]


class History:
    def __init__(self):
        self._undo: List[Patch] = []
        self._redo: List[Patch] = []
        self._highlight_clear_idx: int = 0

    def push(self, patch: Patch):
        self._undo.append(patch)
        self._redo.clear()

    def can_undo(self) -> bool:
        return len(self._undo) > 0

    def can_redo(self) -> bool:
        return len(self._redo) > 0

    def clear(self):
        self._undo.clear()
        self._redo.clear()

    def undo(self, state) -> Optional[Patch]:
        if not self.can_undo():
            return None
        start, before, after = self._undo.pop()
        state.set_bytes(start, before, replace_len=len(after))
        self._redo.append((start, before, after))
        return (start, before, after)

    def redo(self, state) -> Optional[Patch]:
        if not self.can_redo():
            return None
        start, before, after = self._redo.pop()
        state.set_bytes(start, after, replace_len=len(before))
        self._undo.append((start, before, after))
        return (start, before, after)

    def get_edit_highlights(self):
            # Παίρνουμε μόνο τα patches που έγιναν ΜΕΤΑ το clear
            visible_undo = self._undo[self._highlight_clear_idx:]
            
            if not visible_undo:
                return None, []

            ranges = []
            for i, patch in enumerate(visible_undo):
                start, before, after = patch
                
                # Το εύρος της αλλαγής τη στιγμή που έγινε
                rng_start = start
                rng_end = start + len(after) - 1
                
                # Υπολογισμός μετατόπισης (shift) από τα ΜΕΤΑΓΕΝΕΣΤΕΡΑ patches
                for next_patch in visible_undo[i+1:]:
                    n_start, n_before, n_after = next_patch
                    delta = len(n_after) - len(n_before)
                    
                    if delta == 0:
                        continue
                        
                    # Αν το νεότερο patch έγινε ΠΡΙΝ από το τρέχον highlight, το "σπρώχνει"
                    if n_start <= rng_start:
                        rng_start += delta
                        rng_end += delta
                    # Αν το νεότερο patch έγινε ΜΕΣΑ στο τρέχον highlight, το μεγαλώνει/μικραίνει
                    elif n_start <= rng_end:
                        rng_end += delta
                
                # Αποτροπή αρνητικών τιμών σε περίπτωση μαζικών διαγραφών
                rng_start = max(0, rng_start)
                rng_end = max(rng_start - 1, rng_end)
                
                ranges.append((rng_start, rng_end))

            # Το τελευταίο patch από τα ορατά (μετά τους υπολογισμούς)
            latest_range = ranges[-1] if ranges else None
            older_ranges = ranges[:-1] if len(ranges) > 1 else []
                
            return latest_range, older_ranges

    def clear_edit_highlights(self):
        self._highlight_clear_idx = len(self._undo)