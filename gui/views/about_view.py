import asyncio
import platform
import subprocess
from typing import Dict

import flet as ft
import psutil

from core.utils import get_app_root


class AboutView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page_ref = page
        self.expand = True
        self.spacing = 20
        self.scroll = ft.ScrollMode.AUTO

        self.sys_info_column = ft.Column(spacing=10)

        # About Cliptzy Section
        about_section = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Cliptzy", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Cliptzy adalah aplikasi desktop standalone yang dirancang untuk mengubah video panjang "
                        "menjadi klip pendek secara otomatis untuk platform sosial media seperti Shorts, Reels, dan TikTok. "
                        "Aplikasi ini menggunakan kecerdasan buatan (AI) untuk menemukan highlight, memotong video, "
                        "dan menghasilkan subtitle dinamis secara otomatis tanpa memerlukan koneksi internet untuk pemrosesan inti."
                    ),
                    ft.Container(height=10),
                    ft.Text("Teknologi yang Digunakan:", weight=ft.FontWeight.BOLD),
                    ft.Column(
                        [
                            ft.Text(
                                "• Flet: Kerangka kerja UI berbasis Python (Native Desktop)"
                            ),
                            ft.Text(
                                "• yt-dlp: Pengunduh video dan audio performa tinggi"
                            ),
                            ft.Text("• FFmpeg: Pemroses media, crop, dan video efek"),
                            ft.Text(
                                "• Whisper / Faster-Whisper: Transkripsi AI lokal dan akurat"
                            ),
                            ft.Text(
                                "• Deepface & MTCNN: Deteksi wajah dan tracking emosi"
                            ),
                            ft.Text(
                                "• Edge-TTS: Sintesis suara teks-ke-ucapan (Text-to-Speech)"
                            ),
                            ft.Text("• uv: Manajemen dependensi Python super cepat"),
                        ],
                        spacing=5,
                    ),
                ]
            ),
            padding=20,
            border_radius=8,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

        # System Information Section
        sys_info_section = ft.Container(
            content=ft.Column(
                [
                    ft.Text("System Information", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Spesifikasi perangkat keras dan sistem operasi yang digunakan untuk menjalankan aplikasi:",
                        color=ft.Colors.WHITE_70,
                    ),
                    ft.Container(height=5),
                    self.sys_info_column,
                ]
            ),
            padding=20,
            border_radius=8,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

        self.controls = [about_section, sys_info_section]

    def did_mount(self):
        # Mulai ambil informasi sistem secara asinkron agar tidak memblokir UI thread (Peraturan 1.2 & 3.2)
        self.page_ref.run_task(self.load_system_info)

    async def load_system_info(self):
        self.sys_info_column.controls.clear()
        self.sys_info_column.controls.append(ft.ProgressRing(width=20, height=20))
        self.page_ref.update()

        try:
            info = await asyncio.to_thread(self._gather_sys_info)
            self.sys_info_column.controls.clear()
            for key, value in info.items():
                self.sys_info_column.controls.append(
                    ft.Row(
                        [
                            ft.Text(
                                f"{key}",
                                weight=ft.FontWeight.BOLD,
                                width=150,
                                color=ft.Colors.BLUE_200,
                            ),
                            ft.Text(value, selectable=True, expand=True),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                )
        except Exception as e:
            self.sys_info_column.controls.clear()
            self.sys_info_column.controls.append(
                ft.Text(f"Gagal memuat informasi sistem: {e}", color=ft.Colors.RED_400)
            )

        self.page_ref.update()

    def _gather_sys_info(self) -> Dict[str, str]:
        info = {}
        try:
            info["OS"] = (
                f"{platform.system()} {platform.release()} ({platform.version()})"
            )
            info["OS Architecture"] = platform.machine()
            info["Processor"] = platform.processor()
            info["CPU Cores"] = (
                f"{psutil.cpu_count(logical=False)} Physical / {psutil.cpu_count(logical=True)} Logical"
            )

            ram = psutil.virtual_memory()
            info["RAM Total"] = f"{ram.total / (1024**3):.2f} GB"
            info["RAM Available"] = f"{ram.available / (1024**3):.2f} GB"

            try:
                # Coba ambil informasi GPU di Windows via WMI command
                if platform.system() == "Windows":
                    # Disable creation of command window on Windows when frozen
                    startupinfo = None
                    if getattr(subprocess, "STARTUPINFO", None):
                        startupinfo = subprocess.STARTUPINFO()  # type: ignore
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore

                    cmd = ["wmic", "path", "win32_VideoController", "get", "name"]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        check=True,
                        startupinfo=startupinfo,
                    )
                    lines = result.stdout.strip().split("\n")[1:]
                    gpu_names = [line.strip() for line in lines if line.strip()]
                    info["GPU"] = (
                        ", ".join(gpu_names) if gpu_names else "Tidak terdeteksi"
                    )
                else:
                    info["GPU"] = "Informasi GPU hanya didukung di Windows saat ini"
            except Exception:
                info["GPU"] = "Gagal mengambil informasi GPU"

            app_root = get_app_root()
            disk = psutil.disk_usage(app_root)
            info["Disk Total"] = f"{disk.total / (1024**3):.2f} GB"
            info["Disk Free"] = f"{disk.free / (1024**3):.2f} GB"
            info["App Root Path"] = app_root

            info["Python Version"] = platform.python_version()

        except Exception as e:
            info["Error"] = str(e)

        return info
