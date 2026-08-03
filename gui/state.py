from dataclasses import dataclass, field
from typing import List, Optional

from core.models import VideoInfo, ClipSegment
from gui.event_bus import event_bus
from gui import events


@dataclass
class AppState:
    """Centralized observable state for the GUI."""
    
    current_page: str = "clipper"
    current_video: Optional[VideoInfo] = None
    scan_results: List[ClipSegment] = field(default_factory=list)
    
    is_processing: bool = False
    progress_label: str = ""
    progress_value: float = 0.0
    
    log_messages: List[str] = field(default_factory=list)

    def set_page(self, page_name: str) -> None:
        self.current_page = page_name
        event_bus.publish(events.STATE_CHANGED, state=self)

    def set_processing(self, is_proc: bool, label: str = "") -> None:
        self.is_processing = is_proc
        self.progress_label = label
        if not is_proc:
            self.progress_value = 0.0
        event_bus.publish(events.STATE_CHANGED, state=self)

    def update_progress(self, label: str, current: int, total: int) -> None:
        self.progress_label = label
        self.progress_value = (current / total) if total > 0 else 0.0
        event_bus.publish(events.STATE_CHANGED, state=self)

    def append_log(self, message: str) -> None:
        self.log_messages.append(message)
        # We also publish a specific log event for real-time console viewers
        event_bus.publish(events.LOG_MESSAGE, message=message)

# Global application state instance
app_state = AppState()
