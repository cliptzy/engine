# 🚀 TODO: Migrasi GUI Framework PyQt6 → Flet & Refactoring Arsitektur

Dokumen ini berisi **roadmap lengkap** untuk migrasi _GUI framework_ Cliptzy dari **PyQt6** ke **[Flet](https://flet.dev)**, sekaligus melakukan refactoring arsitektur kode Python agar memenuhi standar _best practice_ internasional: **scalable**, **modular**, **DRY**, dan siap menampung penambahan fitur masif di masa depan (template editing, crop video, generate outro, dll).

> **Catatan**: Seluruh proses harus tetap mematuhi aturan yang ditetapkan di [`AGENTS.md`](AGENTS.md) — terutama _Three-Tier Architecture_, _Non-Blocking UI Policy_, dan _Strict Prohibitions_.

---

## 📋 Daftar Isi

1. [Fase 0 — Persiapan & Riset](#-fase-0--persiapan--riset)
2. [Fase 1 — Refactoring Arsitektur Core (GUI-Agnostic)](#-fase-1--refactoring-arsitektur-core-gui-agnostic)
3. [Fase 2 — Scaffolding Flet & Infrastruktur Baru](#-fase-2--scaffolding-flet--infrastruktur-baru)
4. [Fase 3 — Migrasi Komponen UI](#-fase-3--migrasi-komponen-ui)
5. [Fase 4 — Migrasi Fitur Lanjutan](#-fase-4--migrasi-fitur-lanjutan)
6. [Fase 5 — Styling, Theming & Polish UX](#-fase-5--styling-theming--polish-ux)
7. [Fase 6 — Testing, Packaging & CI/CD](#-fase-6--testing-packaging--cicd)
8. [Fase 7 — Fitur Baru Pasca-Migrasi](#-fase-7--fitur-baru-pasca-migrasi)
9. [Appendix A — Mapping Widget PyQt6 → Flet](#-appendix-a--mapping-widget-pyqt6--flet)
10. [Appendix B — Risiko & Mitigasi](#-appendix-b--risiko--mitigasi)
11. [Appendix C — Prinsip Best Practice Python](#-appendix-c--prinsip-best-practice-python)

---

## 🔬 Fase 0 — Persiapan & Riset ✅ SELESAI

> Tujuan: Validasi kelayakan migrasi dan siapkan fondasi sebelum menulis kode.
> **Status**: ✅ Semua task selesai (2 Agustus 2026). Hasil lengkap: lihat `fase_0_report.md`.

- [x] **Audit Kompatibilitas Dependensi dengan `flet build`**
  - ✅ Semua 12 dependensi kritis + 5 opsional kompatibel di satu environment (Python 3.13 + Flet 0.86.5).
  - PoC script: `scripts/poc_flet_deps.py` — 21/21 checks PASS.
  - ⚠️ Verifikasi `flet build` aktual dengan C extensions berat (faster-whisper, opencv) ditunda ke Fase 6 (packaging). Fallback: `flet pack` (PyInstaller wrapper) tetap tersedia.
- [x] **Verifikasi `ft.Video` untuk Kebutuhan Media Player**
  - ✅ Video control tersedia di package terpisah `flet-video==0.86.5`.
  - ⚠️ **PENTING**: Import bukan `ft.Video`, melainkan `from flet_video import Video, VideoMedia`.
  - API lengkap: `play()`, `pause()`, `seek()`, `play_or_pause()`, subtitle support, screenshot, playlist management.
  - PoC script: `scripts/poc_flet_video.py` — siap dijalankan manual dengan file `.mp4`.
- [x] **Riset Pengganti Fitur yang Tidak Ada di Flet**
  - ✅ **System Tray**: `pystray==0.19.5` terinstal. Backend macOS: `pystray._darwin` (native Cocoa). Perlu daemon thread terpisah.
  - ✅ **Desktop Notifications**: `desktop-notifier==6.2.0` terinstal. Urgency: Critical/Normal/Low. API async (kompatibel Flet async). Fallback: `ft.SnackBar`.
  - ✅ **SpinBox**: PoC dibuat — `ft.Row` + `ft.IconButton(-)` + `ft.TextField` + `ft.IconButton(+)`. Lihat `scripts/poc_flet_basic.py`.
- [x] **Instal Flet di Virtual Environment**
  - ✅ `flet==0.86.5`, `flet-video==0.86.5`, `pystray==0.19.5`, `desktop-notifier==6.2.0` terdaftar di `requirements.in`.
  - ✅ `requirements.txt` di-compile ulang dan environment disinkronisasi via `manage_reqs.py`.
- [x] **Buat Branch Git Khusus Migrasi**
  - ✅ Branch `feat/flet-migration` dibuat dari `main` (commit `a6cc8e0`).
  - Kode PyQt6 lama dipertahankan hingga validasi Flet 100% selesai.

---

## 🏗️ Fase 1 — Refactoring Arsitektur Core (GUI-Agnostic)

> Tujuan: Memastikan _Engine Layer_ (`core/`) benar-benar bersih dari ketergantungan GUI apapun sehingga migrasi framework UI hanya berdampak di layer `gui/` saja.

### 1.1 — Definisi Interface & Protocol (Kontrak Antar Layer)

- [ ] **Buat `core/interfaces.py` — Abstract Base Classes & Protocols**
  - Definisikan `Protocol` class untuk semua callback yang digunakan controller:
    ```python
    # core/interfaces.py
    from typing import Protocol, Any

    class ProgressReporter(Protocol):
        def on_progress(self, label: str, current: int, total: int) -> None: ...
        def on_log(self, message: str) -> None: ...
        def on_error(self, error: str) -> None: ...
        def on_finished(self, result: Any) -> None: ...
    ```
  - Definisikan `Protocol` untuk setiap operasi utama (scan, clip, preview, AI detect).
  - Ini menegaskan kontrak yang harus dipenuhi oleh layer UI manapun (PyQt6, Flet, CLI).

- [ ] **Refactor `core/controller.py` — Gunakan Dependency Injection**
  - Hapus semua _implicit coupling_ ke PyQt6.
  - Controller harus menerima _reporter/callback_ melalui constructor injection, bukan global state.
  - Terapkan pola _Command_ atau _UseCase_ untuk setiap operasi:
    ```python
    # core/use_cases/clip_video.py
    class ClipVideoUseCase:
        def __init__(self, processor, config, reporter: ProgressReporter):
            self._processor = processor
            self._config = config
            self._reporter = reporter

        def execute(self, video_info, segments, **options) -> ClipResult:
            ...
    ```

### 1.2 — Modularisasi Engine Core

- [ ] **Pecah `core/processor.py` (27 KB!) menjadi modul-modul kecil:**
  - `core/processing/cropper.py` — Logika crop (default, split-left, split-right).
  - `core/processing/stacker.py` — Logika vstack split-screen.
  - `core/processing/merger.py` — Logika merge multiple clips.
  - `core/processing/intro_outro.py` — Penambahan intro/outro.
  - `core/processing/tts.py` — Text-to-speech generation.
  - `core/processing/__init__.py` — Re-export public API.
  - Setiap modul harus memiliki **satu tanggung jawab** (_Single Responsibility Principle_).

- [ ] **Pecah `core/controller.py` (28 KB!) menjadi Use Cases:**
  - `core/use_cases/__init__.py`
  - `core/use_cases/scan_video.py` — Orkestrasi scan heatmap.
  - `core/use_cases/clip_video.py` — Orkestrasi pemotongan klip.
  - `core/use_cases/preview_clip.py` — Orkestrasi preview.
  - `core/use_cases/detect_highlights.py` — Orkestrasi AI highlight detection.
  - `core/use_cases/upload_clip.py` — Orkestrasi upload ke platform.
  - Controller utama (`core/controller.py`) menjadi _Facade_ ringan yang mendelegasikan ke use case.

- [ ] **Pecah `core/ai_detector.py` (17 KB) — Strategy Pattern:**
  - `core/ai/base_provider.py` — Abstract base class `AIProvider`.
  - `core/ai/ollama_provider.py` — Implementasi Ollama.
  - `core/ai/gemini_provider.py` — Implementasi Google Gemini.
  - `core/ai/openai_provider.py` — Implementasi OpenAI.
  - `core/ai/factory.py` — Factory function `create_ai_provider(config) -> AIProvider`.

- [ ] **Pecah `core/uploader.py` (14 KB) — Strategy Pattern:**
  - `core/uploaders/base.py` — `BaseUploader` ABC.
  - `core/uploaders/youtube.py` — YouTube Shorts uploader.
  - `core/uploaders/tiktok.py` — TikTok uploader.
  - `core/uploaders/instagram.py` — Instagram Reels uploader.
  - `core/uploaders/factory.py` — Factory untuk memilih uploader.

### 1.3 — Standarisasi Type Hints & Data Classes

- [ ] **Buat `core/models.py` — Typed Data Models:**
  - Gunakan `dataclasses` atau `pydantic.BaseModel` untuk semua entitas:
    ```python
    @dataclass
    class VideoInfo:
        video_id: str
        title: str
        duration: float
        url: str
        thumbnail_url: str | None = None

    @dataclass
    class ClipSegment:
        start_time: float
        end_time: float
        label: str
        score: float = 0.0

    @dataclass
    class ClipResult:
        output_path: Path
        duration: float
        success: bool
        error: str | None = None
    ```
  - Eliminasi penggunaan `dict` generik yang tidak terstruktur sebagai data carrier.

- [ ] **Tambahkan Type Hints ke Seluruh Public API di `core/`**
  - Semua fungsi publik harus memiliki _return type_ dan _parameter types_ yang eksplisit.
  - Konfigurasi `mypy` atau `pyright` di `pyproject.toml` untuk _type checking_.

### 1.4 — Standarisasi Error Handling

- [ ] **Buat `core/exceptions.py` — Custom Exception Hierarchy:**
  ```python
  class CliptzyError(Exception): ...
  class VideoDownloadError(CliptzyError): ...
  class ProcessingError(CliptzyError): ...
  class TranscriptionError(CliptzyError): ...
  class UploadError(CliptzyError): ...
  class ConfigError(CliptzyError): ...
  class FFmpegError(ProcessingError): ...
  class CancellationError(CliptzyError): ...
  ```
  - Semua module di `core/` harus melempar _custom exceptions_, bukan `Exception` generik.

### 1.5 — Standarisasi Konfigurasi

- [ ] **Refactor `core/config.py` (12 KB) — Typed Configuration:**
  - Gunakan `dataclass` atau `pydantic.BaseModel` untuk validasi konfigurasi:
    ```python
    @dataclass
    class AIConfig:
        provider: Literal["ollama", "gemini", "openai"] = "ollama"
        host: str = "http://localhost:11434"
        model: str = "llama3"
        api_key: str = ""

    @dataclass
    class AppConfig:
        ai: AIConfig = field(default_factory=AIConfig)
        crop_mode: str = "default"
        aspect_ratio: str = "9:16"
        ...
    ```
  - Sediakan method `from_json()`, `to_json()`, dan validasi otomatis.

---

## 🧱 Fase 2 — Scaffolding Flet & Infrastruktur Baru

> Tujuan: Bangun kerangka aplikasi Flet dan infrastruktur pendukung (event bus, state management, theming).

### 2.1 — Struktur Direktori Baru

- [ ] **Buat Struktur `gui/` Baru untuk Flet:**
  ```
  gui/
  ├── __init__.py
  ├── app.py                    # Entry point ft.app(main)
  ├── theme.py                  # Material Design theming & color palette
  ├── router.py                 # Navigation/routing logic
  ├── state.py                  # Centralized state management (AppState)
  ├── event_bus.py              # Pub/Sub event system pengganti pyqtSignal
  ├── workers.py                # Background task runner (threading.Thread)
  ├── components/               # Reusable UI components (atomic)
  │   ├── __init__.py
  │   ├── spin_box.py           # Custom SpinBox (tidak ada di Flet)
  │   ├── log_viewer.py         # Log console component
  │   ├── progress_indicator.py # Unified progress bar/ring
  │   └── video_card.py         # Kartu video thumbnail
  ├── views/                    # Halaman (page-level views)
  │   ├── __init__.py
  │   ├── clipper_view.py       # YouTube Clipper dashboard
  │   ├── preview_view.py       # Preview & media player
  │   ├── creator_hub_view.py   # Creator Hub browser
  │   ├── upload_view.py        # Auto Upload & distribution
  │   ├── settings_view.py      # Settings & AI config
  │   └── login_view.py         # Login dialog/view
  └── layout/                   # Layout struktural
      ├── __init__.py
      ├── main_layout.py        # Shell layout (sidebar + content area)
      ├── sidebar.py            # NavigationRail sidebar
      └── header.py             # Top bar / status bar
  ```

### 2.2 — Event Bus (Pengganti `pyqtSignal`)

- [ ] **Implementasi `gui/event_bus.py` — Pub/Sub Thread-Safe:**
  ```python
  import threading
  from collections import defaultdict
  from typing import Callable, Any

  class EventBus:
      """Thread-safe publish/subscribe event system."""

      def __init__(self):
          self._subscribers: dict[str, list[Callable]] = defaultdict(list)
          self._lock = threading.Lock()

      def subscribe(self, event: str, callback: Callable) -> None:
          with self._lock:
              self._subscribers[event].append(callback)

      def unsubscribe(self, event: str, callback: Callable) -> None:
          with self._lock:
              self._subscribers[event].remove(callback)

      def publish(self, event: str, **kwargs: Any) -> None:
          with self._lock:
              listeners = list(self._subscribers.get(event, []))
          for callback in listeners:
              callback(**kwargs)
  ```
  - Event names sebagai konstanta di `gui/events.py`:
    ```python
    # gui/events.py
    SCAN_PROGRESS = "scan.progress"
    SCAN_FINISHED = "scan.finished"
    CLIP_PROGRESS = "clip.progress"
    CLIP_FINISHED = "clip.finished"
    # ... dll
    ```

### 2.3 — State Management

- [ ] **Implementasi `gui/state.py` — Centralized Observable State:**
  ```python
  @dataclass
  class AppState:
      current_page: str = "clipper"
      current_video: VideoInfo | None = None
      scan_results: list[ClipSegment] = field(default_factory=list)
      is_processing: bool = False
      progress_label: str = ""
      progress_value: float = 0.0
      log_messages: list[str] = field(default_factory=list)
  ```
  - State disimpan secara terpusat dan dimutasi melalui metode terkontrol.
  - Perubahan state memicu `page.update()` pada UI.

### 2.4 — Background Worker Abstraction

- [ ] **Implementasi `gui/workers.py` — Generic Worker Menggunakan `threading.Thread`:**
  ```python
  class BackgroundWorker:
      """Generic background task runner with cancellation support."""

      def __init__(self, page: ft.Page, target: Callable, *,
                   on_progress=None, on_finished=None, on_error=None):
          self._page = page
          self._target = target
          self._on_progress = on_progress
          self._on_finished = on_finished
          self._on_error = on_error
          self._is_cancelled = threading.Event()
          self._thread: threading.Thread | None = None

      def start(self, *args, **kwargs) -> None: ...
      def cancel(self) -> None: ...

      @property
      def is_cancelled(self) -> bool: ...
  ```
  - Callback dari worker harus memanggil `page.update()` setelah memutasi state.
  - **Flet Threading API**: Manfaatkan `page.run_thread(target)` untuk background tasks (thread-safe UI update bawaan) dan `page.run_task(coroutine)` untuk operasi async.
  - `core/controller.py` sudah 100% GUI-agnostic (menggunakan `event_hook` callback), jadi worker cukup menjembatani callback → state mutation → `page.update()`.

### 2.5 — Entry Point

- [ ] **Buat `gui/app.py` Baru (Flet Entry Point):**
  ```python
  import flet as ft
  from gui.router import Router
  from gui.theme import build_theme
  from gui.state import AppState

  def main(page: ft.Page):
      page.title = "Cliptzy"
      page.theme = build_theme()
      page.theme_mode = ft.ThemeMode.DARK
      page.window.width = 1280
      page.window.height = 800

      state = AppState()
      router = Router(page, state)
      router.initialize()

      page.update()

  if __name__ == "__main__":
      ft.app(target=main)
  ```

- [ ] **Update `run.py` — Deteksi Mode GUI (Flet):**
  - Pertahankan mode `--cli` yang sudah ada.
  - Mode GUI default menjalankan `ft.app(target=main)` alih-alih `QApplication.exec()`.

---

## 🔄 Fase 3 — Migrasi Komponen UI

> Tujuan: Migrasi setiap widget PyQt6 ke komponen Flet secara bertahap. Urutkan berdasarkan dependensi — mulai dari yang tidak tergantung komponen lain.

### 3.1 — Layout Struktural

- [ ] **`gui/layout/sidebar.py`** — Ganti `SidebarWidget` (PyQt6) → `ft.NavigationRail`
  - Gunakan `NavigationRailDestination` untuk setiap halaman: Clipper, Preview, Creator Hub, Upload, Settings.
  - Tautkan `on_change` event ke `router.navigate()`.
- [ ] **`gui/layout/header.py`** — Ganti `HeaderWidget` → `ft.AppBar` atau `ft.Row` custom
  - Tampilkan judul halaman aktif, info video yang sedang diproses, dan tombol aksi cepat.
- [ ] **`gui/layout/main_layout.py`** — Ganti `QHBoxLayout` + `QStackedWidget`
  - Gunakan `ft.Row` dengan `NavigationRail` + `ft.Container(expand=True)` sebagai area konten.
  - Content area akan di-swap berdasarkan routing state.

### 3.2 — Halaman Utama (Views)

- [ ] **`gui/views/clipper_view.py`** — Migrasi dashboard clipper utama
  - Gabungkan: `VideoInputWidget`, `ClipConfigWidget`, `ProcessControlWidget`.
  - Ganti `QLineEdit` → `ft.TextField`, `QComboBox` → `ft.Dropdown`.
  - Ganti `QCheckBox` → `ft.Checkbox`, `QGroupBox` → `ft.Card`.
  - Ganti `QSpinBox`/`QDoubleSpinBox` → Custom `SpinBox` component.
  - Ganti `QProgressBar` → `ft.ProgressBar`.
- [ ] **`gui/views/preview_view.py`** — Migrasi preview & media player
  - Ganti `QMediaPlayer` + `QVideoWidget` → `ft.Video`.
  - Ganti `QSlider` → `ft.Slider` (untuk seek).
  - Pertahankan fitur heatmap visualization (render sebagai `ft.Canvas` atau `ft.Image`).
- [ ] **`gui/views/creator_hub_view.py`** — Migrasi Creator Hub
  - Ganti `QScrollArea` + grid of cards → `ft.GridView` atau `ft.ResponsiveRow`.
  - Ganti `QPixmap` untuk thumbnail → `ft.Image(src=url)`.
  - Ganti `QPushButton` → `ft.ElevatedButton` / `ft.IconButton`.
- [ ] **`gui/views/upload_view.py`** — Migrasi Auto Upload
  - Ganti `QTabWidget` → `ft.Tabs`.
  - Migrasi form konfigurasi setiap platform (YouTube, TikTok, Instagram).
  - Ganti `QFileDialog` → `ft.FilePicker` (untuk import cookies).
- [ ] **`gui/views/settings_view.py`** — Migrasi Settings & AI Config
  - Migrasi `AISettingsWidget` dan `DependencyManagerWidget`.
  - Gunakan `ft.ExpansionPanelList` untuk collapsible section groups.
- [ ] **`gui/views/login_view.py`** — Migrasi Login Dialog
  - Ganti `QDialog` → `ft.AlertDialog` atau dedicated view.
  - Ganti `QFormLayout` → `ft.Column` dengan labeled `ft.TextField`.

### 3.3 — Komponen Reusable

- [ ] **`gui/components/spin_box.py`** — Custom SpinBox
  - `ft.Row` berisi `ft.IconButton(-)` + `ft.TextField` + `ft.IconButton(+)`.
  - Support `min`, `max`, `step`, `value`, `on_change`.
- [ ] **`gui/components/log_viewer.py`** — Log Console
  - `ft.ListView` dengan auto-scroll-to-bottom.
  - Terima log messages dari `EventBus`.
- [ ] **`gui/components/progress_indicator.py`** — Unified Progress
  - Wrapper `ft.ProgressBar` + `ft.Text(label)` yang tersinkronisasi.
- [ ] **`gui/components/video_card.py`** — Video Thumbnail Card
  - `ft.Card` berisi `ft.Image` + `ft.Text(title)` + metadata.
  - Reusable di Creator Hub dan Preview.

---

## ⚙️ Fase 4 — Migrasi Fitur Lanjutan

> Tujuan: Migrasi fitur-fitur yang memerlukan integrasi OS-level atau third-party.

### 4.1 — Drag-and-Drop

- [ ] **File Drop dari OS**
  - Flet core `DragTarget` hanya menangani drag internal antar-control.
  - Untuk drag file dari OS File Manager (Finder/Explorer) ke window, gunakan paket **`flet-dropzone`**.
  - Alternatif: Gunakan `ft.FilePicker` sebagai fallback jika `flet-dropzone` bermasalah.
  - Support: `cookies.txt`, file video Intro/Outro, URL YouTube (text drop).
- [ ] **Internal Drag-and-Drop (jika dibutuhkan)**
  - Gunakan `ft.Draggable` + `ft.DragTarget` untuk reorder segmen klip.

### 4.2 — System Tray (Opsional — via `pystray`)

- [ ] **Integrasi `pystray` untuk System Tray**
  - Buat `gui/tray.py` yang menginisialisasi system tray icon secara terpisah.
  - Menu konteks: Show/Hide Window, Quit.
  - Jalankan `pystray` di thread terpisah agar tidak mengganggu event loop Flet.

### 4.3 — Desktop Notifications

- [ ] **Integrasi `desktop-notifier` untuk Notifikasi OS**
  - Buat `gui/notifications.py` sebagai abstraksi notifikasi:
    ```python
    async def notify(title: str, message: str) -> None: ...
    ```
  - Fallback: Gunakan `ft.SnackBar` sebagai notifikasi in-app jika OS notification gagal.

### 4.4 — Video Player

- [ ] **Validasi `ft.Video` dengan File Lokal**
  - Pastikan seek, play/pause, volume berfungsi dengan file `.mp4` lokal.
  - Jika `ft.Video` tidak memadai, pertimbangkan memanggil player eksternal (misal `mpv`) via subprocess.

---

## 🎨 Fase 5 — Styling, Theming & Polish UX

> Tujuan: Buat tampilan Flet setara atau lebih baik dari tema dark PyQt6 yang sudah ada.

### 5.1 — Material Design Theming

- [ ] **Implementasi `gui/theme.py`:**
  - Definisikan `ft.Theme` dengan color scheme custom:
    ```python
    def build_theme() -> ft.Theme:
        return ft.Theme(
            color_scheme_seed=ft.Colors.DEEP_PURPLE,
            color_scheme=ft.ColorScheme(
                primary="#6C5CE7",
                on_primary="#FFFFFF",
                secondary="#00B894",
                error="#FF7675",
                surface="#1E1E2E",
                on_surface="#CDD6F4",
                surface_variant="#313244",
                background="#11111B",
            ),
        )
    ```
  - Replika palette warna dari `gui/styles.py` lama.

### 5.2 — Custom Fonts

- [ ] **Registrasi Font Custom**
  - Pindahkan file font ke `assets/fonts/`.
  - Register via `page.fonts = {"CustomFont": "/fonts/CustomFont.ttf"}`.
  - Terapkan font ke `page.theme.font_family`.

### 5.3 — Micro-Animations & Transitions

- [ ] **Animasi Transisi Halaman**
  - Gunakan `ft.AnimatedSwitcher` atau `ft.Container(animate=...)` untuk transisi saat berpindah view.
- [ ] **Hover Effects**
  - Terapkan `on_hover` pada kartu-kartu video dan tombol untuk efek elevasi/skala.
- [ ] **Smooth Progress**
  - Animasikan perubahan value `ProgressBar` menggunakan `animate` property.

---

## 🧪 Fase 6 — Testing, Packaging & CI/CD

> Tujuan: Validasi kualitas, bundle sebagai standalone, dan otomatisasi pipeline.

### 6.1 — Unit Testing

- [ ] **Test Core Layer (GUI-Agnostic)**
  - Pastikan semua `core/use_cases/` dan `core/processing/` memiliki unit test.
  - Gunakan `pytest` dengan fixtures dan mocking.
  - Target coverage: ≥ 80% untuk `core/`.
- [ ] **Test GUI Components (Opsional)**
  - Flet belum memiliki testing framework resmi. Gunakan snapshot testing jika memungkinkan.

### 6.2 — Linting & Type Checking

- [ ] **Konfigurasi di `pyproject.toml`:**
  ```toml
  [tool.mypy]
  strict = true
  ignore_missing_imports = true

  [tool.ruff]
  target-version = "py310"
  select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "RUF"]
  ```
- [ ] **Jalankan CI checks:** `ruff check .`, `mypy core/`, `pytest tests/`.

### 6.3 — Packaging Desktop Standalone

- [ ] **Konfigurasi `flet build`**
  - Setup `pyproject.toml` dengan metadata Flet:
    ```toml
    [tool.flet]
    app.module = "gui.app"
    app.name = "Cliptzy"
    app.description = "YouTube Clipper & Auto Uploader"
    ```
  - Test `flet build macos`, `flet build windows`, `flet build linux`.
- [ ] **Validasi Bundling Dependensi Berat**
  - Pastikan `faster-whisper`, `opencv-python`, `yt-dlp` ter-bundle dengan benar.
  - Gunakan `--include-packages` jika diperlukan.
- [ ] **Siapkan Aset untuk Bundling**
  - Pindahkan `images/icon.png` → `assets/icon.png`.
  - Pastikan semua path aset menggunakan prefix `/` (konvensi Flet assets).

### 6.4 — CI/CD

- [ ] **Update `.github/workflows/`:**
  - Ganti step build PyInstaller → `flet build` di semua target OS.
  - Pertahankan matrix build: macOS, Windows, Linux.
  - Tambahkan step linting (`ruff`), type checking (`mypy`), dan testing (`pytest`).

---

## 🌟 Fase 7 — Fitur Baru Pasca-Migrasi

> Tujuan: Fitur-fitur baru yang akan lebih mudah diimplementasikan setelah arsitektur baru siap.

### 7.1 — Template Editing / Crop Video

- [ ] **Template System:**
  - Buat `core/templates/` — sistem template untuk preset crop & overlay.
  - Desain model data: `CropTemplate(name, aspect_ratio, overlay_positions, text_zones)`.
  - UI: Gallery template dengan preview thumbnail.
- [ ] **Visual Crop Editor:**
  - Canvas interaktif di Flet (`ft.Canvas` atau `ft.GestureDetector`) untuk:
    - Drag-to-resize area crop.
    - Preview real-time posisi split-screen.
    - Zona teks subtitle yang dapat dipindahkan.

### 7.2 — Generate Outro

- [ ] **Outro Generator Engine:**
  - Buat `core/processing/outro_generator.py`.
  - Input: Teks CTA, logo channel, background music.
  - Output: File video `.mp4` outro yang siap digabungkan.
- [ ] **UI Outro Configurator:**
  - Form konfigurasi: teks, durasi, warna, musik, animasi.
  - Preview real-time dalam `ft.Video`.

### 7.3 — Facebook Pages Uploader

- [ ] **Implementasi `core/uploaders/facebook.py`**
  - Integrasi Meta Graph API.
  - Form konfigurasi Page Access Token & Page ID di settings.

### 7.4 — Batch Processing

- [ ] **Queue System:**
  - Antrian URL video untuk diproses secara berurutan.
  - UI: List view dengan status per-item (queued, processing, done, error).

### 7.5 — Plugin / Extension System (Masa Depan)

- [ ] **Plugin Architecture:**
  - Buat `core/plugins/` — sistem plugin untuk custom AI provider, custom uploader, custom template.
  - Interface: `PluginBase` ABC dengan `register()`, `execute()`.
  - Discovery: Auto-scan folder `plugins/` saat startup.

---

## 📊 Appendix A — Mapping Widget PyQt6 → Flet

| PyQt6 Widget | Flet Equivalent | Catatan |
|---|---|---|
| `QApplication` | `ft.app(target=main)` | Entry point lebih sederhana |
| `QMainWindow` | `ft.Page` | Page = top-level container |
| `QWidget` | `ft.Container` / `ft.Column` / `ft.Row` | Layout containers |
| `QStackedWidget` | `page.views` + routing / manual swap | URL-based routing |
| `QLabel` | `ft.Text`, `ft.Icon` | |
| `QPushButton` | `ft.ElevatedButton` / `ft.FilledButton` / `ft.IconButton` | Varian Material |
| `QLineEdit` | `ft.TextField` | |
| `QComboBox` | `ft.Dropdown` | Single-select |
| `QCheckBox` | `ft.Checkbox` | |
| `QGroupBox` | `ft.Card` / `ft.Container` with border | |
| `QScrollArea` | `ft.ListView` / `ft.Column(scroll=True)` | |
| `QProgressBar` | `ft.ProgressBar` / `ft.ProgressRing` | Nilai 0.0–1.0 |
| `QTextEdit` | `ft.TextField(multiline=True)` | |
| `QSlider` | `ft.Slider` | |
| `QSpinBox` | Custom component (TextField + IconButton) | ⚠️ Tidak ada built-in |
| `QTabWidget` | `ft.Tabs` | |
| `QSystemTrayIcon` | `pystray` (third-party) | ⚠️ Tidak built-in |
| `QMediaPlayer` + `QVideoWidget` | `ft.Video` | Berbasis `libmpv` |
| `QMessageBox` | `ft.AlertDialog` | |
| `QFileDialog` | `ft.FilePicker` | Callback-based |
| `QThread` | `threading.Thread` / `asyncio` | Standard Python |
| `pyqtSignal` | Event Bus (pub/sub) / callbacks | Custom implementation |
| `QTimer` | `threading.Timer` / `asyncio.sleep` | |
| `QMenu` / `QAction` | `ft.PopupMenuButton` | |
| Qt Style Sheets (QSS) | `ft.Theme` + Material Design | Paradigma berbeda |
| `QHBoxLayout` | `ft.Row` | |
| `QVBoxLayout` | `ft.Column` | |
| `QGridLayout` | `ft.ResponsiveRow` / `ft.GridView` | |
| `QPixmap` / `QImage` | `ft.Image` | |
| Drag-and-Drop Events | `ft.Draggable` / `ft.DragTarget` / `page.on_drop` | |

---

## ⚠️ Appendix B — Risiko & Mitigasi

| # | Risiko | Dampak | Mitigasi |
|---|---|---|---|
| 1 | **Packaging native extensions** (`faster-whisper`, `opencv-python`) tidak kompatibel dengan `flet build` | 🔴 Kritis — Aplikasi tidak bisa di-bundle | PoC di Fase 0. Jika gagal, pertahankan PyInstaller sebagai fallback packaging. Flet tetap dipakai untuk development mode. |
| 2 | **`ft.Video` tidak stabil** untuk playback file lokal | 🟡 Sedang — Fitur preview terdegradasi | Fallback: panggil `mpv` via subprocess, atau gunakan `ft.Image` + frame extraction. |
| 3 | **System Tray & Desktop Notifications** tidak built-in | 🟢 Rendah — Fitur non-esensial | Gunakan `pystray` + `desktop-notifier`. In-app SnackBar sebagai fallback. |
| 4 | **Performa rendering Flet** (Flutter engine) untuk UI-heavy | 🟡 Sedang | Flet berbasis Flutter yang sudah dioptimasi. Benchmark di Fase 0. |
| 5 | **Kurva belajar** tim/kontributor terhadap Flet | 🟢 Rendah | Flet API sangat Pythonic. Dokumentasi lengkap. |
| 6 | **Breaking changes** dari Flet yang masih relatif muda | 🟡 Sedang | Pin versi Flet di `requirements.in`. Pantau changelogs. |

---

## 📖 Appendix C — Prinsip Best Practice Python

Prinsip-prinsip berikut **WAJIB** diterapkan di seluruh kode pasca-refactoring:

### C.1 — DRY (Don't Repeat Yourself)
- Eliminasi duplikasi kode. Ekstrak _common logic_ ke fungsi/kelas utilitas.
- Gunakan _base class_ atau _mixin_ untuk perilaku yang di-share (contoh: `BaseUploader`).

### C.2 — SOLID Principles
- **S**ingle Responsibility: Satu kelas/modul = satu tanggung jawab.
- **O**pen/Closed: Terbuka untuk ekstensi, tertutup untuk modifikasi (Strategy & Factory pattern).
- **L**iskov Substitution: Subclass harus bisa menggantikan parent tanpa breaking.
- **I**nterface Segregation: Interface/Protocol kecil dan terfokus.
- **D**ependency Inversion: Layer atas bergantung pada abstraksi, bukan implementasi konkret.

### C.3 — Clean Code Standards
- **Naming**: Gunakan nama deskriptif berbahasa Inggris. `snake_case` untuk fungsi/variabel, `PascalCase` untuk kelas.
- **Docstrings**: Setiap modul, kelas, dan fungsi publik harus memiliki docstring (Google-style).
- **Max Line Length**: 100 karakter (konfigurasi di `ruff`).
- **Imports**: Terorganisir (stdlib → third-party → local). Di-enforce oleh `isort` / `ruff`.

### C.4 — Separation of Concerns
- UI Layer tidak boleh mengandung business logic.
- Core/Engine Layer tidak boleh mengandung kode GUI.
- Controller/Use Case sebagai penghubung.

### C.5 — Scalability Patterns
- **Factory Pattern**: Untuk pembuatan objek dinamis (AI provider, uploader, template).
- **Strategy Pattern**: Untuk algoritma yang bisa di-swap (crop mode, AI provider).
- **Observer/Pub-Sub Pattern**: Untuk komunikasi antar-komponen (Event Bus).
- **Repository Pattern**: Untuk akses data/config yang terabstraksi.

### C.6 — Dependency Injection
- Hindari `import` langsung ke implementasi konkret dari layer luar.
- Gunakan constructor injection untuk menyuntikkan dependensi.
- Ini memudahkan testing (mocking) dan memungkinkan swap implementasi.

---

_Dokumen ini adalah panduan hidup (living document) yang akan diperbarui seiring progres migrasi. Setiap fase yang selesai harus di-checklist dan di-commit._
