from typing import Any, Optional

import flet as ft

from gui.components.clipper import (
    ClipConfig,
    Preview,
    ProcessControl,
    VideoInput,
)
from gui.event_bus import event_bus
from gui.workers import BackgroundWorker


class ClipperView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.spacing = 20

        self.worker: Optional[BackgroundWorker] = None

        self.video_input = VideoInput(self.page_ref)
        self.preview = Preview(on_ai_scan_requested=self.on_ai_scan_requested)
        self.clip_config = ClipConfig(self.page_ref)
        self.process_control = ProcessControl(self.page_ref)
        self.controls = [
            self.video_input,
            self.preview,
            self.clip_config,
            self.process_control,
        ]
        self.scroll = ft.ScrollMode.AUTO
        self.expand = True

        self.clip_config.load_from_config()
        self.clip_config.detect_hw_accel()
        self.clip_config.detect_libass()

    def did_mount(self):
        event_bus.subscribe("fetch_requested", self.on_fetch_requested)
        event_bus.subscribe("start_process_requested", self.on_start_process_requested)
        event_bus.subscribe(
            "cancel_process_requested", self.on_cancel_process_requested
        )

    def will_unmount(self):
        event_bus.unsubscribe("fetch_requested", self.on_fetch_requested)
        event_bus.unsubscribe(
            "start_process_requested", self.on_start_process_requested
        )
        event_bus.unsubscribe(
            "cancel_process_requested", self.on_cancel_process_requested
        )

    def on_cancel_process_requested(self, *args, **kwargs):
        self._cancel_flag = True
        from core.logger import log
        from core.utils import kill_active_subprocesses

        log.info("Membatalkan proses klip...")
        kill_active_subprocesses()

    def on_start_process_requested(self, *args, **kwargs):
        from core.controller import controller
        from core.logger import log
        from gui.state import app_state

        url = self.video_input.url_input.value
        if not url:
            app_state.append_log(
                "Error: URL kosong, silakan Load Video terlebih dahulu."
            )
            return

        mode = self.preview.get_selected_mode()
        segments = []
        payload = {}

        if mode == "custom":
            start_val, end_val = self.preview.get_custom_range()
            payload["start"] = start_val
            payload["end"] = end_val
        else:
            segments = self.preview.get_selected_segments()
            if not segments:
                app_state.append_log(
                    f"Error: Tidak ada segmen yang dipilih untuk mode {mode}"
                )
                return
            payload["segments"] = segments

        payload.update(
            {
                "url": url,
                "mode": mode,
                "clip_method": self.preview.clip_method_dropdown.value,
                "crop": self.clip_config.crop_combo.value,
                "ratio": self.clip_config.ratio_combo.value,
                "subtitle": True,  # Subtitle is always enabled (mandatory)
                "use_highlight": bool(self.clip_config.highlight_check.value),
                "merge_clips": bool(self.clip_config.merge_clips_check.value),
                "whisper_model": self.clip_config.whisper_combo.value,
                "subtitle_font": self.clip_config.font_combo.value,
                "subtitle_location": self.clip_config.location_combo.value,
                "subtitle_delay": float(self.clip_config.delay_spin.value or 0),
                "subtitle_font_size": int(self.clip_config.font_size_spin.value or 60),
                "subtitle_color": self.clip_config.color_combo.value,
                "subtitle_border_style": int(self.clip_config.bg_combo.value or 3),
                "subtitle_animation": self.clip_config.anim_combo.value,
                "subtitle_style": self.clip_config.style_combo.value,
                "subtitle_max_words": int(self.clip_config.max_words_spin.value or 3),
                "padding": int(self.clip_config.padding_spin.value or 0),
                "min_duration": int(self.clip_config.min_duration_spin.value or 0),
                "custom_prompt": self.preview.custom_prompt_input.value or "",
                "phase1_only": False,
            }
        )

        self.set_processing(True)
        self._cancel_flag = False

        class FletProgressReporter:
            def __init__(self, view):
                self.view = view

            def on_progress(self, label: str, current: int, total: int) -> None:
                if label == "total_targets":
                    self.view.set_total_targets(current)
                else:
                    self.view.update_stage(
                        label, {"clip_index": current, "total": total}
                    )

            def on_log(self, message: str) -> None:
                app_state.append_log(message)

            def on_error(self, error: str) -> None:
                app_state.append_log(f"Error: {error}")

            def on_finished(self, result: Any) -> None:
                pass

        controller.reporter = FletProgressReporter(self)
        controller.clip_uc.reporter = controller.reporter

        async def clip_worker():
            import asyncio

            try:

                def check_cancelled():
                    return self._cancel_flag

                log.info(f"Memulai proses clipping untuk URL: {url} (Mode: {mode})")
                res = await asyncio.to_thread(
                    controller.execute_clipping, payload, check_cancelled
                )

                if self._cancel_flag:
                    log.warning("Proses clipping dibatalkan oleh pengguna.")
                    app_state.append_log("Proses dibatalkan.")
                else:
                    success = res.get("success", 0)
                    log.info(
                        f"Proses clipping selesai! Berhasil memproses {success} klip."
                    )
                    app_state.append_log(f"Selesai: {success} klip diproses.")

                    if success > 0:
                        # Tell user to go to Upload page manually
                        app_state.append_log("Klip selesai di-render. Buka tab Upload untuk mempublikasikan.")
            except Exception as e:
                import traceback

                log.error(f"Error proses klip: {e}\n{traceback.format_exc()}")
                app_state.append_log(f"Error: {e}")
            finally:
                self.set_processing(False)
                self.process_control.update_stage("Idle", {})

        if self.page:
            self.page.run_task(clip_worker)

    def on_fetch_requested(self, url: str):
        import threading

        from core.controller import controller
        from gui.state import app_state

        self.video_input.set_loading(True)
        app_state.set_processing(True, "Menganalisa URL Video...")

        async def worker():
            import asyncio

            from core.logger import log

            # We must use asyncio.to_thread for blocking calls
            try:
                # 1. Fetch metadata
                log.info(f"Mengambil metadata dari URL: {url}")
                preview_data = await asyncio.to_thread(controller.get_preview, url)
                self.preview.set_preview_data(preview_data)
                log.info(f"Metadata berhasil didapatkan: {preview_data.get('title')}")

                # 2. Fetch segments/heatmap
                app_state.set_processing(True, "Menganalisa Heatmap Video...")
                log.info(f"Memindai Heatmap (Most Replayed) dari YouTube...")
                scan_data = await asyncio.to_thread(controller.scan_segments, url)
                self.preview.set_scan_data(scan_data)
                log.info(
                    f"Heatmap selesai: {len(scan_data.get('segments', []))} klip ditemukan."
                )

                # Check for cached AI segments
                ai_cache = await asyncio.to_thread(
                    controller.get_cached_ai_highlights, url
                )
                if ai_cache:
                    self.preview.set_ai_scan_data(ai_cache)

            except Exception as e:
                from core.logger import log

                log.error(f"Gagal memuat video: {e}")
                app_state.append_log(f"Error: {str(e)}")
            finally:
                self.video_input.set_loading(False)
                app_state.set_processing(False)
                try:
                    if self.page:
                        self.page.update()
                    else:
                        self.update()
                except Exception:
                    pass

        if self.page:
            self.page.run_task(worker)

    def on_ai_scan_requested(self, ai_config: dict):
        url = self.video_input.url_input.value
        if not url:
            from gui.state import app_state

            app_state.append_log(
                "Error: URL kosong, silakan Load Video terlebih dahulu."
            )
            return

        from core.controller import controller
        from core.logger import log
        from gui.state import app_state

        self.preview.set_ai_scanning(True)
        app_state.set_processing(
            True, "Menganalisa Highlights dengan AI (Transkripsi Whisper + LLM)..."
        )
        log.info(f"Memulai AI Scan untuk URL: {url}")

        async def ai_scan_worker():
            import asyncio

            try:
                # Gunakan to_thread agar I/O berat tidak memblokir UI thread Flet
                ai_data = await asyncio.to_thread(
                    controller.scan_ai_highlights, url, ai_config
                )
                if ai_data and ai_data.get("segments"):
                    self.preview.set_ai_scan_data(ai_data)
                    log.info(
                        f"AI Scan selesai: {len(ai_data['segments'])} klip ditemukan."
                    )
                else:
                    log.warning(
                        "AI Scan selesai tapi tidak menemukan klip yang relevan."
                    )
                    app_state.append_log(
                        "Peringatan: AI tidak menemukan segmen highlight."
                    )
            except Exception as e:
                import traceback

                log.error(f"Error proses AI Scan: {e}\n{traceback.format_exc()}")
                app_state.append_log(f"Error AI Scan: {e}")
            finally:
                self.preview.set_ai_scanning(False)
                app_state.set_processing(False)
                try:
                    if self.page:
                        self.page.update()
                    else:
                        self.update()
                except Exception:
                    pass

        if self.page:
            self.page.run_task(ai_scan_worker)

    def set_loading(self, loading: bool) -> None:
        self.video_input.set_loading(loading)

    def set_processing(self, processing: bool) -> None:
        self.process_control.set_processing(processing)

    def set_total_targets(self, total: int) -> None:
        self.process_control.set_total_targets(total)

    def update_stage(self, stage_name: str, data: dict) -> None:
        self.process_control.update_stage(stage_name, data)

    def on_test_subtitle(self, e) -> None:
        event_bus.publish("test_subtitle_requested")

    def load_video_url(self, url: str) -> None:
        self.video_input.url_input.value = url
        try:
            self.video_input.url_input.update()
        except Exception:
            pass
        event_bus.publish("fetch_requested", url=url)
