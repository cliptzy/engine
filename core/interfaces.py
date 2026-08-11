from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


class ProgressReporter(Protocol):
    """
    Protocol for reporting progress from background tasks.
    Any GUI layer (PyQt6, Flet, CLI) must implement this interface
    to receive updates from the core engine.
    """

    def on_progress(self, label: str, current: int, total: int) -> None:
        """Called when progress is updated."""
        ...

    def on_log(self, message: str) -> None:
        """Called to log a message to the console/UI."""
        ...

    def on_error(self, error: str) -> None:
        """Called when a fatal error occurs."""
        ...

    def on_finished(self, result: Any) -> None:
        """Called when the task completes successfully."""
        ...


class AIProvider(Protocol):
    """
    Protocol for AI highlighting providers (Ollama, Gemini, OpenAI).
    """

    def detect_highlights(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Detects highlight segments in a video transcript.
        Returns a list of segments: [{"start_time": float, "end_time": float, "label": str, "score": float}, ...]
        """
        ...


from typing import Callable


def create_reporter_hook(
    reporter: Optional[ProgressReporter],
) -> Callable[[str, Any], None]:
    """
    Factory modular untuk menghasilkan fungsi event_hook standar.
    Mencegah redundansi pembuatan fungsi hook secara manual di setiap UseCase.
    """

    def hook(event: str, data: Any = None):
        if not reporter:
            return
        if event == "log":
            reporter.on_log(str(data))
        elif event == "stage":
            if isinstance(data, dict):
                stage = data.get("stage", "")
                idx = data.get("clip_index", 0)
                tot = data.get("total", 0)
                reporter.on_progress(stage, idx, tot)
        elif event == "total_targets":
            reporter.on_progress("total_targets", int(data), int(data))

    return hook
