import flet as ft
from gui.event_bus import event_bus
from gui import events
from typing import Any
import logging

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
        
        self._levels = [
            ("DEBUG", logging.DEBUG, "#A6ADC8"),
            ("INFO", logging.INFO, "#CDD6F4"),
            ("WARNING", logging.WARNING, "#F9E2AF"),
            ("ERROR", logging.ERROR, "#F38BA8")
        ]
        self._level_idx = 1 # Default to INFO
        self._current_min_level = self._levels[self._level_idx][1]
        
        self.level_button = ft.Button(
            content=ft.Text(self._levels[self._level_idx][0], size=11, color=self._levels[self._level_idx][2], weight=ft.FontWeight.BOLD),
            style=ft.ButtonStyle(
                padding=ft.Padding(8, 2, 8, 2),
                bgcolor=ft.Colors.TRANSPARENT,
            ),
            on_click=self._on_level_cycle
        )
        
        self.header = ft.Container(
            content=ft.Row([
                ft.Text("Logs", weight=ft.FontWeight.BOLD, size=13),
                ft.Container(expand=True),
                self.level_button
            ]),
            padding=ft.Padding(8, 2, 8, 2)
        )
        
        self.content = ft.Column([
            self.header,
            ft.Divider(height=1, thickness=1),
            ft.Container(self.log_list, expand=True)
        ], spacing=0)
        self._mounted = False
        
    def _on_level_cycle(self, e: Any) -> None:
        self._level_idx = (self._level_idx + 1) % len(self._levels)
        label, level, color = self._levels[self._level_idx]
        self._current_min_level = level
        
        if isinstance(self.level_button.content, ft.Text):
            self.level_button.content.value = label
            self.level_button.content.color = color
            
        if hasattr(self, "_log_handler"):
            self._log_handler.setLevel(self._current_min_level)
            
        # Perbarui visibility berdasarkan level log saat ini
        for control in self.log_list.controls:
            if isinstance(control, ft.Text):
                lvl = self._get_level_from_msg(str(control.value))
                control.visible = lvl >= self._current_min_level
                
        try:
            self.update()
        except Exception:
            pass
            
    def _get_level_from_msg(self, msg: str) -> int:
        if "| DEBUG" in msg: return logging.DEBUG
        if "| WARNING" in msg: return logging.WARNING
        if "| ERROR" in msg: return logging.ERROR
        if "| CRITICAL" in msg: return logging.CRITICAL
        # Teks plain dari UI atau app_state.append_log() (tanpa prefix)
        if msg.startswith("Error:") or msg.startswith("[UPLOAD] ❌ Gagal"): 
            return logging.ERROR
        if msg.startswith("Peringatan:"):
            return logging.WARNING
        return logging.INFO
        
    def did_mount(self) -> None:
        self._mounted = True
        event_bus.subscribe(events.LOG_MESSAGE, self._on_log_message)
        
        from core.logger import log as core_log
        
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
        self._log_handler.setLevel(self._current_min_level)
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
            
        level = self._get_level_from_msg(message)
        
        color = "#CDD6F4"
        if level == logging.ERROR or level == logging.CRITICAL:
            color = "#F38BA8"
        elif level == logging.WARNING:
            color = "#F9E2AF"
        elif level == logging.DEBUG:
            color = "#A6ADC8"
            
        text = ft.Text(
            value=message,
            size=13,
            font_family="monospace",
            color=color,
            selectable=True,
            visible=level >= self._current_min_level
        )
        self.log_list.controls.append(text)
        
        overflow = len(self.log_list.controls) - MAX_LOG_LINES
        if overflow > 0:
            del self.log_list.controls[:overflow]
        
        try:
            if self._mounted and self.page:
                self.log_list.update()
        except Exception:
            pass