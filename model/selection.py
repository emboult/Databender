from dataclasses import dataclass
from typing import Optional


@dataclass
class Selection:
    start: Optional[int] = None
    end: Optional[int] = None

    def is_empty(self) -> bool:
        return self.start is None or self.end is None