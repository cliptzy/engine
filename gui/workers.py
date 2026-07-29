"""
QThread Worker classes for non-blocking asynchronous tasks in Cliptzy GUI.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import Dict, Any, Optional
from core import controller, log

class PreviewWorker(QThread):
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            preview = controller.get_preview(self.url)
            self.finished_signal.emit(preview)
        except Exception as e:
            self.error_signal.emit(str(e))


class ScanWorker(QThread):
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            result = controller.scan_segments(self.url)
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class ClipWorker(QThread):
    log_signal = pyqtSignal(str)
    stage_signal = pyqtSignal(str, dict)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, payload: Dict[str, Any]):
        super().__init__()
        self.payload = payload
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        def event_hook(kind: str, data: Any):
            if kind == "log":
                self.log_signal.emit(str(data))
            elif kind == "stage" and isinstance(data, dict):
                stage_name = data.get("stage", "")
                self.stage_signal.emit(stage_name, data)
            elif kind == "total_targets":
                self.stage_signal.emit("total_targets", {"total": data})

        def is_cancelled_check() -> bool:
            return self._is_cancelled

        try:
            result = controller.execute_clipping(
                payload=self.payload,
                event_hook=event_hook,
                is_cancelled=is_cancelled_check
            )
            self.finished_signal.emit(result)
        except Exception as e:
            log.exception(f"ClipWorker failed: {e}")
            self.error_signal.emit(str(e))


class SubtitlePreviewWorker(QThread):
    log_signal = pyqtSignal(str)
    stage_signal = pyqtSignal(str, dict)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, payload: Dict[str, Any]):
        super().__init__()
        self.payload = payload

    def run(self):
        def event_hook(kind: str, data: Any):
            if kind == "log":
                self.log_signal.emit(str(data))
            elif kind == "stage" and isinstance(data, dict):
                stage_name = data.get("stage", "")
                self.stage_signal.emit(stage_name, data)

        try:
            sample_path = controller.generate_subtitle_preview_sample(
                payload=self.payload,
                event_hook=event_hook
            )
            self.finished_signal.emit(sample_path)
        except Exception as e:
            log.exception(f"SubtitlePreviewWorker failed: {e}")
            self.error_signal.emit(str(e))


class AIScanWorker(QThread):
    log_signal = pyqtSignal(str)
    stage_signal = pyqtSignal(str, dict)
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, url: str, ai_config: Dict[str, Any]):
        super().__init__()
        self.url = url
        self.ai_config = ai_config

    def run(self):
        def event_hook(kind: str, data: Any):
            if kind == "log":
                self.log_signal.emit(str(data))
            elif kind == "log_inline":
                from gui.globals import signals
                signals.log_message_inline.emit(str(data))
            elif kind == "stage" and isinstance(data, dict):
                stage_name = data.get("stage", "")
                self.stage_signal.emit(stage_name, data)

        try:
            result = controller.scan_ai_highlights(
                url=self.url,
                ai_config=self.ai_config,
                event_hook=event_hook
            )
            self.finished_signal.emit(result)
        except Exception as e:
            log.exception(f"AIScanWorker failed: {e}")
            self.error_signal.emit(str(e))


