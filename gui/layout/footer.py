import os
import shutil
import threading
import time
from typing import Any, cast

import flet as ft
import psutil

from core.config import config


class StatusBar(ft.Container):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.height = 24
        # self.bgcolor = ft.Colors.SURFACE_VARIANT
        # self.padding = ft.padding.symmetric(horizontal=10, vertical=0) # type: ignore

        # Left Side (Status)
        self.cookies_status = ft.Text(
            "🍪 Cookies: Loading...", size=11, color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.ffmpeg_status = ft.Text(
            "🎥 FFmpeg: Loading...", size=11, color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.deno_status = ft.Text(
            "🦕 Deno: Loading...", size=11, color=ft.Colors.ON_SURFACE_VARIANT
        )

        self.left_row = ft.Row(
            spacing=15,
            controls=cast(
                list[ft.Control],
                [self.cookies_status, self.ffmpeg_status, self.deno_status],
            ),
        )

        # Right Side (Stats + Progress)
        self.cpu_ram_status = ft.Text(
            "💻 CPU: 0% | RAM: 0%", size=11, color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.network_status = ft.Text(
            "🌐 0 KB/s", size=11, color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.clock_status = ft.Text(
            "🕒 00:00:00",
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
            weight=ft.FontWeight.BOLD,
        )

        self.progress_bar = ft.ProgressBar(
            width=100, color=ft.Colors.PRIMARY, bgcolor=ft.Colors.SURFACE, value=0.0
        )
        self.progress_bar.visible = False

        self.progress_label = ft.Text(
            size=11, color=ft.Colors.ON_SURFACE_VARIANT, visible=False
        )

        self.right_row = ft.Row(
            spacing=15,
            controls=cast(
                list[ft.Control],
                [
                    self.progress_label,
                    self.progress_bar,
                    self.cpu_ram_status,
                    self.network_status,
                    self.clock_status,
                ],
            ),
        )

        self.content = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=cast(list[ft.Control], [self.left_row, self.right_row]),
        )

        self._running = True

    def did_mount(self):
        from gui import events
        from gui.event_bus import event_bus

        event_bus.subscribe(events.STATE_CHANGED, self._on_state_changed)
        self._check_dependencies()
        if self.page:
            self.page.run_task(self._stats_worker_async)

    def will_unmount(self):
        from gui import events
        from gui.event_bus import event_bus

        event_bus.unsubscribe(events.STATE_CHANGED, self._on_state_changed)
        self._running = False

    def _check_dependencies(self):
        import os
        import shutil

        has_cookies = os.path.exists("cred/yt_cookies.txt")
        has_ffmpeg = shutil.which("ffmpeg") is not None
        has_deno = shutil.which("deno") is not None

        self.cookies_status.value = (
            "Cookies: OK" if has_cookies else "Cookies: Not Found"
        )
        self.cookies_status.color = (
            ft.Colors.GREEN_400 if has_cookies else ft.Colors.ERROR
        )

        self.ffmpeg_status.value = "FFmpeg: OK" if has_ffmpeg else "FFmpeg: Not Found"
        self.ffmpeg_status.color = (
            ft.Colors.GREEN_400 if has_ffmpeg else ft.Colors.ERROR
        )

        self.deno_status.value = "Deno: OK" if has_deno else "Deno: Not Found"
        self.deno_status.color = ft.Colors.GREEN_400 if has_deno else ft.Colors.ERROR

        if self.page:
            self.page.update()
        else:
            self.update()

    async def _stats_worker_async(self):
        import asyncio
        import time

        import psutil

        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                ram = mem.percent

                net_io = psutil.net_io_counters()
                if not hasattr(self, "_last_net_io"):
                    self._last_net_io = net_io
                    self._last_net_time = time.time()
                    speed_str = "0 KB/s"
                else:
                    now = time.time()
                    dt = now - self._last_net_time
                    if dt > 0:
                        bytes_recv = net_io.bytes_recv - self._last_net_io.bytes_recv
                        bytes_sent = net_io.bytes_sent - self._last_net_io.bytes_sent
                        total_bytes = bytes_recv + bytes_sent

                        speed_kbs = (total_bytes / 1024) / dt
                        if speed_kbs > 1024:
                            speed_str = f"{speed_kbs / 1024:.1f} MB/s"
                        else:
                            speed_str = f"{speed_kbs:.0f} KB/s"
                    else:
                        speed_str = "0 KB/s"

                    self._last_net_io = net_io
                    self._last_net_time = now

                self.cpu_ram_status.value = f"💻 CPU: {cpu:.1f}% | RAM: {ram:.1f}%"
                self.network_status.value = f"🌐 {speed_str}"

                # Update Clock
                self.clock_status.value = f"🕒 {time.strftime('%H:%M:%S')}"

                try:
                    if self.page:
                        self.page.update()
                    else:
                        self.update()
                except Exception as e:
                    print("Error updating footer UI:", e)
            except Exception as e:
                print("Error in stats worker:", e)
            await asyncio.sleep(1)

    def _on_state_changed(self, state: Any):
        if state.is_processing:
            self.progress_bar.visible = True
            self.progress_bar.value = state.progress_value
            self.progress_label.value = state.progress_label
            self.progress_label.visible = True
        else:
            self.progress_bar.visible = False
            self.progress_label.visible = False

        try:
            if self.page:
                self.page.update()
            else:
                self.update()
        except Exception:
            pass
