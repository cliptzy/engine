#!/usr/bin/env python3
"""
PoC #3: Flet Video Player Verification
========================================
Verifikasi bahwa ft.Video dapat memutar file .mp4 lokal
dengan kontrol: seek, play/pause, dan volume.

Usage:
  python scripts/poc_flet_video.py [path_to_mp4]

Jika tidak ada argumen, akan mencari file .mp4 di folder clips/.
"""

import os
import sys
from pathlib import Path
from typing import cast

import flet as ft
from flet_video import MaterialVideoControls, Video, VideoMedia


def find_sample_video() -> str | None:
    """Cari file .mp4 pertama di direktori clips/."""
    project_root = Path(__file__).parent.parent
    clips_dir = project_root / "clips"

    if clips_dir.exists():
        for mp4 in clips_dir.rglob("*.mp4"):
            return str(mp4.absolute())

    return None


def main(page: ft.Page) -> None:
    page.title = "Cliptzy Flet PoC #3 — Video Player"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 900
    page.window.height = 650
    page.padding = 20

    # Determine video path
    video_path = sys.argv[1] if len(sys.argv) > 1 else find_sample_video()

    status_text = ft.Text(
        value="",
        size=13,
        color="#CDD6F4",
        selectable=True,
    )

    def log(msg: str) -> None:
        status_text.value = f"{status_text.value}\n{msg}".strip()
        page.update()

    if not video_path or not os.path.isfile(video_path):
        page.add(
            ft.Column(
                controls=[
                    ft.Icon(ft.Icons.WARNING, size=64, color="#FF7675"),
                    ft.Text(
                        "No .mp4 file found!",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        "Usage: python scripts/poc_flet_video.py <path_to_mp4>\n"
                        "Or place a .mp4 file in the clips/ directory.",
                        size=14,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        )
        return

    log(f"📹 Loading video: {video_path}")
    log(f"   File size: {os.path.getsize(video_path) / (1024 * 1024):.1f} MB")

    # Create video player
    video = Video(
        playlist=[VideoMedia(video_path)],
        controls=MaterialVideoControls(),
        autoplay=False,
        fit=ft.BoxFit.CONTAIN,
        aspect_ratio=16 / 9,
        volume=80,
        expand=True,
        on_load=lambda _: log("✅ Video loaded successfully!"),
        on_error=lambda e: log(f"❌ Video error: {e.data}"),
    )

    log("✅ flet_video.Video control created")

    # Custom controls
    async def play_pause(e) -> None:
        await video.play_or_pause()
        log("⏯️ Play/Pause toggled")

    async def seek_forward(e) -> None:
        await video.seek(10000)  # Seek to 10s
        log("⏩ Seeked to 10s")

    def volume_change(e) -> None:
        video.volume = int(e.control.value)  # type: ignore
        log(f"🔊 Volume: {int(e.control.value)}%")  # type: ignore
        page.update()

    video_controls: list[ft.Control] = cast(
        list[ft.Control],
        [
            ft.IconButton(
                ft.Icons.PLAY_ARROW,
                icon_size=32,
                on_click=play_pause,
                tooltip="Play/Pause",
            ),
            ft.IconButton(
                ft.Icons.FORWARD_10,
                icon_size=32,
                on_click=seek_forward,
                tooltip="Seek to 10s",
            ),
            ft.Text("Volume:"),
            ft.Slider(
                min=0,
                max=100,
                value=80,
                divisions=20,
                label="{value}%",
                on_change=volume_change,
                expand=True,
            ),
        ],
    )

    controls_row = ft.Row(
        controls=video_controls,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    page.add(
        ft.Column(
            controls=[
                ft.Text(
                    "🎬 Flet Video Player PoC",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Container(
                    content=video,
                    height=400,
                    border_radius=12,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    bgcolor="#000000",
                ),
                controls_row,
                ft.Divider(),
                ft.Text("Status Log:", weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=status_text,
                    bgcolor="#11111B",
                    padding=12,
                    border_radius=8,
                    height=120,
                ),
            ],
            expand=True,
            spacing=12,
        )
    )

    log("🎉 Video player PoC ready — press Play to test")


if __name__ == "__main__":
    ft.run(main)
