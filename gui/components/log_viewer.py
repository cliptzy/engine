import flet as ft
from gui.event_bus import event_bus
from gui import events
from typing import Any

MAX_LOG_LINES = 200

class LogViewer(ft.Container):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.border_radius = 8
        self.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        
        self.log_list = ft.ListView(
            padding=4,
            expand=True,
            spacing=4,
            auto_scroll=True,
        )
        self.content = self.log_list
        self._mounted = False
        
    def did_mount(self) -> None:
        self._mounted = True
        event_bus.subscribe(events.LOG_MESSAGE, self._on_log_message)
        
        # Attach logging handler to capture all core logs
        import logging
        from core.logger import log as core_log
        
        handler_ref = self  # capture reference untuk inner class
        
        class EventBusLogHandler(logging.Handler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    event_bus.publish(events.LOG_MESSAGE, message=msg)
                except Exception:
                    pass

        self._log_handler = EventBusLogHandler()
        formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")
        self._log_handler.setFormatter(formatter)
        self._log_handler.setLevel(logging.INFO)
        core_log.addHandler(self._log_handler)
        
    def will_unmount(self) -> None:
        self._mounted = False
        event_bus.unsubscribe(events.LOG_MESSAGE, self._on_log_message)
        from core.logger import log as core_log
        if hasattr(self, '_log_handler'):
            core_log.removeHandler(self._log_handler)
        
    def _on_log_message(self, message: str) -> None:
        if not self._mounted:
            return
            
        text = ft.Text(
            value=message,
            size=13,
            font_family="monospace",
            color="#CDD6F4",
            selectable=True,
        )
        self.log_list.controls.append(text)
        
        # Batasi jumlah log agar tidak membebani memori dan UI
        overflow = len(self.log_list.controls) - MAX_LOG_LINES
        if overflow > 0:
            del self.log_list.controls[:overflow]
        
        try:
            if self._mounted and self.page:
                self.log_list.update()
        except Exception:
            pass