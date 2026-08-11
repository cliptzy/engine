"""
Centralized yt-dlp Logger Adapter.

Provides a single, reusable logger class that bridges yt-dlp's custom logger
interface with Python's standard logging (core.logger). Since the GUI LogViewer
already attaches an EventBusLogHandler to core.logger, all messages logged here
automatically appear in the desktop GUI log viewer.

Design Principles (SOLID):
- Single Responsibility: This module only handles yt-dlp ↔ logging bridge.
- Open/Closed: New log destinations are added via logging handlers, not by
  modifying this class.
- Dependency Inversion: Depends on the standard `logging.Logger` abstraction,
  not on specific GUI or event-bus details.
"""

from typing import Any, Callable, Optional

from core.logger import log


class YtDlpLoggerAdapter:
    """
    Adapter that satisfies yt-dlp's expected logger interface (debug/info/warning/error)
    and routes all messages through Python's standard logging framework.

    Usage:
        logger = YtDlpLoggerAdapter(prefix="[yt-dlp]")
        ydl_opts = {'logger': logger, ...}
    """

    def __init__(self, prefix: str = "[yt-dlp]") -> None:
        self._prefix = prefix

    def debug(self, msg: str) -> None:
        # yt-dlp sends download progress lines as debug messages prefixed with
        # "[download]".  These are extremely high-frequency and redundant when a
        # progress_hook is also attached — suppress them to avoid flooding the
        # log file and GUI.
        if msg.startswith("[download]"):
            return
        log.debug(f"{self._prefix} {msg}")

    def info(self, msg: str) -> None:
        log.info(f"{self._prefix} {msg}")

    def warning(self, msg: str) -> None:
        log.warning(f"{self._prefix} {msg}")

    def error(self, msg: str) -> None:
        log.error(f"{self._prefix} {msg}")


def create_yt_dlp_logger(prefix: str = "[yt-dlp]") -> YtDlpLoggerAdapter:
    """Factory function to create a configured YtDlpLoggerAdapter."""
    return YtDlpLoggerAdapter(prefix=prefix)


def create_yt_dlp_progress_hook(
    event_hook: Optional[Callable[[str, Any], None]] = None,
    prefix: str = "[yt-dlp]",
) -> Callable[[dict], None]:
    """
    Factory function that creates a yt-dlp progress_hook callback.

    The progress_hook logs download progress both to the centralized logger
    and (optionally) to an event_hook callback for real-time GUI updates.

    Args:
        event_hook: Optional callback ``(event: str, data: Any) -> None`` that
                    will receive ``("log", message)`` events.
        prefix: Log line prefix for identification.
    """

    def hook(d: dict) -> None:
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "").strip()
            speed = d.get("_speed_str", "").strip()
            eta = d.get("_eta_str", "").strip()
            total = d.get("_total_bytes_estimate_str", d.get("_total_bytes_str", ""))
            msg = f"{prefix} [download] {percent} of {total} at {speed} ETA {eta}"
            log.info(msg)
        elif d["status"] == "finished":
            filename = d.get("filename", "")
            msg = f"{prefix} Download selesai: {filename}"
            log.info(msg)

    return hook
