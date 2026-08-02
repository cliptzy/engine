#!/usr/bin/env python3
"""
PoC #4: Flet Threading & Background Task Verification
=======================================================
Verifikasi bahwa background tasks (threading.Thread) dapat:
1. Berjalan tanpa memblokir UI
2. Memperbarui UI secara thread-safe via page.update()
3. Mendukung pembatalan (cancellation flag)
4. Berkomunikasi progres ke UI (pengganti pyqtSignal)

Ini mensimulasikan pola kerja ClipWorker/ScanWorker di Cliptzy.
"""

import threading
import time

import flet as ft


def main(page: ft.Page) -> None:
    page.title = "Cliptzy Flet PoC #4 — Threading"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 800
    page.window.height = 600
    page.padding = 20

    # --- State ---
    cancel_event = threading.Event()
    worker_thread: threading.Thread | None = None

    # --- UI Controls ---
    progress_bar = ft.ProgressBar(value=0, color="#6C5CE7", bgcolor="#313244")
    progress_label = ft.Text("Idle", size=14)
    log_view = ft.ListView(height=250, spacing=2, auto_scroll=True)
    start_btn = ft.ElevatedButton("Start Heavy Task", icon=ft.Icons.PLAY_ARROW)
    cancel_btn = ft.ElevatedButton(
        "Cancel", icon=ft.Icons.CANCEL, disabled=True, color="#FF7675"
    )

    def log(msg: str, color: str = "#CDD6F4") -> None:
        """Thread-safe log to ListView."""
        log_view.controls.append(
            ft.Text(f"[{time.strftime('%H:%M:%S')}] {msg}", size=12, color=color)
        )
        page.update()

    def heavy_task() -> None:
        """Simulate a heavy background task (like FFmpeg processing)."""
        total_steps = 20

        log("🚀 Worker started — simulating heavy I/O task", "#00B894")

        for i in range(total_steps):
            if cancel_event.is_set():
                log("🛑 Task cancelled by user!", "#FF7675")
                progress_label.value = "Cancelled"
                progress_bar.value = 0
                progress_bar.color = "#FF7675"
                page.update()
                return

            # Simulate work
            time.sleep(0.3)

            # Update progress (thread-safe in Flet!)
            progress = (i + 1) / total_steps
            progress_bar.value = progress
            progress_label.value = f"Processing... {int(progress * 100)}%"
            log(f"  Step {i + 1}/{total_steps} completed")
            page.update()

        # Finished
        log("✅ Task completed successfully!", "#00B894")
        progress_label.value = "Completed!"
        progress_bar.value = 1.0
        progress_bar.color = "#00B894"

        # Reset UI state
        start_btn.disabled = False
        cancel_btn.disabled = True
        page.update()

    def on_start(e) -> None:
        nonlocal worker_thread
        cancel_event.clear()
        progress_bar.value = 0
        progress_bar.color = "#6C5CE7"
        log_view.controls.clear()

        start_btn.disabled = True
        cancel_btn.disabled = False
        page.update()

        log("📝 Creating background worker thread...")
        worker_thread = threading.Thread(target=heavy_task, daemon=True)
        worker_thread.start()
        log(f"   Thread ID: {worker_thread.ident}, Name: {worker_thread.name}")

    def on_cancel(e) -> None:
        log("⚠️ Cancellation requested...", "#FF7675")
        cancel_event.set()
        start_btn.disabled = False
        cancel_btn.disabled = True
        page.update()

    start_btn.on_click = on_start
    cancel_btn.on_click = on_cancel

    # --- Concurrent test: multiple workers ---
    concurrent_results = ft.Text("", size=12, selectable=True)

    def run_concurrent_test(e) -> None:
        """Test multiple concurrent background threads."""
        results: list[str] = []
        lock = threading.Lock()
        completed = threading.Event()
        count = [0]

        def worker(worker_id: int) -> None:
            time.sleep(0.5 * worker_id)  # Stagger
            with lock:
                results.append(f"Worker-{worker_id} done at {time.strftime('%H:%M:%S')}")
                count[0] += 1
                if count[0] == 3:
                    concurrent_results.value = "\n".join(results)
                    log(f"🎉 All 3 concurrent workers finished!", "#00B894")
                    page.update()

        log("🔄 Starting 3 concurrent workers...")
        for i in range(3):
            t = threading.Thread(target=worker, args=(i + 1,), daemon=True)
            t.start()
            log(f"  Started Worker-{i + 1} (Thread: {t.ident})")

    concurrent_btn = ft.ElevatedButton(
        "Test Concurrent Workers",
        icon=ft.Icons.MULTIPLE_STOP,
        on_click=run_concurrent_test,
    )

    # --- Layout ---
    page.add(
        ft.Column(
            controls=[
                ft.Text(
                    "🧵 Threading PoC — Background Task Runner",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(),
                ft.Text("Single Worker (with Cancellation):"),
                ft.Row([start_btn, cancel_btn]),
                progress_label,
                progress_bar,
                ft.Divider(),
                ft.Text("Concurrent Workers:"),
                ft.Row([concurrent_btn]),
                concurrent_results,
                ft.Divider(),
                ft.Text("Log Output:", weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=log_view,
                    bgcolor="#11111B",
                    padding=12,
                    border_radius=8,
                    expand=True,
                ),
            ],
            expand=True,
            spacing=10,
        )
    )

    log("Ready. Click 'Start Heavy Task' to begin.")


if __name__ == "__main__":
    ft.app(target=main)
