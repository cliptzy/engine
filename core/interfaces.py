from typing import Protocol, Any, Dict, List, Optional
from pathlib import Path


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


