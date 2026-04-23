#Provides a reusable Debouncer class that schedules function calls with a delay, cancelling previous pending calls.

import tkinter as tk
from typing import Callable, Optional


class Debouncer:
    def __init__(self, master: tk.Misc, delay_ms: int = 300):
        self.master = master
        self.delay = delay_ms
        self._job_id: Optional[str] = None

    def debounce(self, func: Callable[[], None]) -> None:
        #Schedule func to be called after the delay, cancelling any pending call
        if self._job_id:
            self.master.after_cancel(self._job_id)
        self._job_id = self.master.after(self.delay, lambda: self._execute(func))

    def _execute(self, func: Callable[[], None]) -> None:
        self._job_id = None
        func()

    def cancel(self) -> None:
        #Cancel any pending debounced call
        if self._job_id:
            self.master.after_cancel(self._job_id)
            self._job_id = None