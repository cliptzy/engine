import threading
from typing import Any, Callable, Optional

import flet as ft


class BackgroundWorker:
    """Generic background task runner with cancellation support for Flet."""

    def __init__(
        self,
        page: ft.Page,
        target: Callable[..., Any],
        *,
        on_progress: Optional[Callable[..., Any]] = None,
        on_finished: Optional[Callable[..., Any]] = None,
        on_error: Optional[Callable[..., Any]] = None,
    ):
        self._page = page
        self._target = target
        self._on_progress = on_progress
        self._on_finished = on_finished
        self._on_error = on_error

        self._is_cancelled = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self, *args: Any, **kwargs: Any) -> None:
        """Starts the background task."""
        self._is_cancelled.clear()

        # We pass self as the first keyword argument if the target expects it,
        # but to keep it simple and generic, we just run the target in a thread.
        # Flet's page.run_thread is thread-safe for UI updates, but since we are doing heavy I/O,
        # we can just use a normal thread and use page.run_task / page.update for UI callbacks if needed.
        # However, Flet's run_thread handles session context nicely.

        def run_wrapper() -> None:
            try:
                # Add cancellation flag check to kwargs if the target supports it?
                # For now, we assume the target uses a global flag or we inject a checker.
                kwargs["is_cancelled_check"] = self.is_cancelled
                result = self._target(*args, **kwargs)
                if self._on_finished:
                    self._on_finished(result)
            except Exception as e:
                import traceback

                error_trace = traceback.format_exc()
                if self._on_error:
                    self._on_error(f"{str(e)}\\n{error_trace}")
                else:
                    print(f"BackgroundWorker Error: {e}\\n{error_trace}")
            finally:
                # Ensure UI refreshes
                self._page.update()

        self._thread = threading.Thread(target=run_wrapper, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """Requests cancellation of the task."""
        self._is_cancelled.set()

    def is_cancelled(self) -> bool:
        """Returns True if the task was cancelled."""
        return self._is_cancelled.is_set()
