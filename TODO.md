# Rencana Refactoring Cliptzy: Web-Based ke Desktop GUI Standalone

Dokumen ini berisi rencana kerja terstruktur (*roadmap*) untuk merombak aplikasi **Cliptzy** dari aplikasi berbasis Web (Flask + HTML/CSS/JS) dan CLI menjadi aplikasi **Desktop GUI Standalone** berbasis Python yang modern, efisien, dan siap didistribusikan.

---

## 🎯 Tujuan Utama Refactoring
1. **Menghilangkan ketergantungan pada server Flask / HTTP local port** (`webapp.py`).
2. **Menyediakan antarmuka desktop native** yang responsif, visual modern (dark theme), tanpa perlu membuka browser eksternal.
3. **Meningkatkan *User Experience* (UX)** dengan integrasi fitur native (File Picker native system, notifikasi desktop, drag-and-drop, internal media player preview).
4. **Memudahkan distribusi pengguna (Standalone Executable)**: Pengguna dapat menjalankan satu file exe/biner tanpa perlu menginstal Python, Flask, atau mengonfigurasi lingkungan secara manual.

---

## 📋 Daftar Tugas & Roadmap Refactoring

### Phase 1: Analisis & Pemilihan Teknologi Desktop GUI
- [x] **1.1 Evaluasi & Pemilihan UI Framework**
  - [x] **Terpilih: PyQt6 (Qt for Python)** — Dipilih sebagai kerangka kerja GUI native karena performa tinggi, arsitektur event `QThread` & `pyqtSignal` yang thread-safe, kontrol widget kaya, serta dukungan multimedia native (`QMediaPlayer`).
  - [x] Tambahkan dependensi `PyQt6>=6.6.0` ke `requirements.txt` dan terverifikasi terinstal di lingkungan Python (`.venv`).
- [x] **1.2 Pemetaan Fitur & Flow Data (Arsitektur PyQt6)**
  - [x] **Data Flow & Signal Mapping**:
    - `PreviewWorker (QThread)` ➔ Signal `preview_loaded(dict)` ➔ Update UI Thumbnail, Title, Duration.
    - `ScanWorker (QThread)` ➔ Signal `scan_completed(dict)` ➔ Populate Heatmap Segments list & duration.
    - `ClipWorker (QThread)` ➔ Signal `stage_changed(str, dict)` & `log_emitted(str)` ➔ Update Progress Bar & Real-time Console.
  - [x] **Pemisahan Modul GUI**:
    - `gui/`: Berisi seluruh komponen tampilan PyQt6 (`main_window.py`, `widgets/`, `workers.py`).
    - `core/controller.py`: Pengelola logika bisnis, penanganan job, dan abstraksi `core/` engine.

---

### Phase 2: Refactoring Core Engine (Decoupling dari Flask)
- [x] **2.1 Abstraksi Controller / Service Layer (`core/controller.py`)**
  - [x] Dibuat `ClipController` (`core/controller.py`) dan diekspor melalui `core/__init__.py` sebagai pengelola tunggal alur kerja antarmuka GUI dan engine.
  - [x] Seluruh logika backend (`get_preview`, `scan_segments`, `execute_clipping`, `import_cookies`, `set_intro_video`, `set_outro_video`) dipindahkan dari `webapp.py` ke controller terisolasi.
  - [x] Modul core tidak lagi memerlukan dependensi framework web (`Flask`, `Werkzeug`, `Jinja2`).
- [x] **2.2 Pembaruan Sistem Event & Callback Status**
  - [x] Diimplementasikan sistem event hook pada `execute_clipping` dan `process_single_clip` dengan stage granular (`start_clip`, `download`, `crop`, `subtitle_model_load`, `subtitle_transcribe`, `burn_subtitle`, `finalize`, `done_clip`).
  - [x] Ditambahkan penanganan pembatalan (*cancellation handling*) via parameter callback `is_cancelled`.
- [x] **2.3 Pengelolaan Konfigurasi & Persistence (`core/config.py`)**
  - [x] Ditambahkan metode `save_to_file()`, `load_from_file()`, `to_dict()`, dan `update_from_dict()` pada class `AppConfig`.
  - [x] Konfigurasi pengguna otomatis tersimpan dan dimuat dari file `config.json` lokal.

---

### Phase 3: Desain & Implementasi Interface Desktop GUI
- [x] **3.1 Layout Main Window (`gui/main_window.py`)**
  - [x] **Header Bar (`gui/widgets/header_widget.py`)**: Menampilkan Logo Cliptzy, versi, indikator status FFmpeg (Ready/Missing), serta status cookie dengan gaya **Navbar Flat (tidak rounded)**.
  - [x] **Sidebar Navigation Widget (`gui/widgets/sidebar_widget.py`)**: Panel navigasi samping untuk berpindah antara YouTube Clipper, Auto Upload Platform, dan Pengaturan.
  - [x] **Input Section (`gui/widgets/video_input_widget.py`)**: Input URL YouTube (dengan tombol Paste, Clear, dan "Load Video").
  - [x] **Video Metadata & Timeline Preview Box (`gui/widgets/preview_widget.py`)**: Menampilkan Thumbnail, Judul, Uploader, Durasi, serta pilihan Mode Heatmap vs Kustom Range.
  - [x] **Auto Upload & Distribution View (`gui/widgets/auto_upload_widget.py`)**: Layout alur kerja dan konfigurasi auto-upload ke YouTube Shorts, TikTok, dan Instagram Reels.
  - [x] **Clear Cache & Generated Clips**: Tombol "Bersihkan Cache & Klip" di Sidebar yang menghapus seluruh segmen `segments.json`, temporary files, dan klip video di folder `clips/` secara otomatis.

- [x] **3.2 Panel Parameter & Konfigurasi Clip (`gui/widgets/settings_widget.py`)**
  - [x] **Mode Pemotongan**: Dropdown (Default Center, Split Left Facecam, Split Right Facecam).
  - [x] **Rasio Output**: Selector (9:16 Shorts/TikTok, 1:1 Square, 16:9 Landscape, Original).
  - [x] **Pengaturan Subtitle (Faster-Whisper)**: Toggle Auto Subtitle, Model Whisper selector (`tiny` s/d `large-v3`), Subtitle Font selector (auto-scan `.ttf`/`.otf`), Subtitle Location (Bottom/Center), & Delay (ms).
  - [x] **Media Tambahan & Cookies**: Tombol import `cookies.txt`, video Intro, dan video Outro via native file dialog.
- [x] **3.3 Dashboard Eksekusi & Processing Log (`gui/widgets/log_console_widget.py`)**
  - [x] Progress Bar Keseluruhan (misal: Clip 2 dari 5).
  - [x] Badge Indikator Stage Aktif (Downloading, Cropping, Transcribing, Burning Subtitles, Finalizing).
  - [x] Terminal/Console Log Viewer interaktif dalam GUI dengan tombol "Clear Log" dan "Export Log".
  - [x] Tombol Start & Cancel / Abort Job saat proses berjalan.
- [x] **3.4 Gallery Clips & Embedded Media Player (`gui/widgets/media_player_widget.py`)**
  - [x] List Gallery klip hasil olahan yang telah selesai diproses.
  - [x] Video Player internal berbasis QtMultimedia (`QMediaPlayer` + `QVideoWidget`) dengan Play/Pause/Seek slider.
  - [x] Tombol "Open Output Folder" untuk membuka Explorer/Nautilus ke folder klip.


---

### Phase 4: Integrasi Fitur Nativ Desktop & Threading Model
- [x] **4.1 File Dialog Native & Drag-and-Drop**
  - [x] Digunakan Native File Open Dialog untuk memilih file `cookies.txt`, video intro, dan video outro.
  - [x] Ditambahkan dukungan Drag-and-Drop file `.txt` (auto-import cookies) dan file video `.mp4`/`.mkv`/`.mov` (set intro/outro) serta URL YouTube langsung ke jendela aplikasi.
- [x] **4.2 Multithreading & Asynchronous Management**
  - [x] Seluruh operasi I/O berat (yt-dlp download, transkripsi Whisper, render FFmpeg) dipastikan berjalan di background worker thread (`PreviewWorker`, `ScanWorker`, `ClipWorker`).
  - [x] UI thread (Main GUI) tetap 100% responsif tanpa freeze saat proses clipping berlangsung.
- [x] **4.3 Notifikasi & System Tray (`QSystemTrayIcon`)**
  - [x] Diintegrasikan **System Tray Icon** (`QSystemTrayIcon`) dengan menu kontekstual (Tampilkan, Buka Folder Output, Keluar).
  - [x] Ditambahkan notifikasi native OS (*Desktop Balloon Notification*) saat proses pembuatan klip selesai atau mengalami error.


---

### Phase 5: Dependency Management & Standalone Packaging
- [x] **5.1 Otomatisasi & Pengecekan FFmpeg**
  - [x] Diimplementasikan fungsi `attempt_add_ffmpeg_to_path()` di `core/utils.py` yang mendeteksi FFmpeg dari folder aplikasi `bin/`, WinGet package di Windows, atau PATH sistem OS (Linux/Windows/macOS).
- [x] **5.2 Manajemen Model Faster-Whisper**
  - [x] Penanganan unduhan model Whisper otomatis dengan deteksi cache `~/.cache/huggingface/hub` dan laporan indikator status di GUI.
- [x] **5.3 Konfigurasi Build Standalone (PyInstaller)**
  - [x] Dibuat spesifikasi build **[cliptzy.spec](file:///home/dickymuliafiqri/Downloads/Code/cliptzy/cliptzy.spec)** yang membundel PyQt6, ctranslate2, faster_whisper, av, yt_dlp, serta asset `fonts/` dan `images/`.
  - [x] Dibuat skrip otomatisasi build **[build_executable.py](file:///home/dickymuliafiqri/Downloads/Code/cliptzy/build_executable.py)** untuk menghasilkan paket executable standalone tanpa memerlukan instalasi Python pada komputer pengguna.


---

### Phase 6: Pengujian, Polish & Cleanup Codebase
- [x] **6.1 Hapus Kode Obsolete**
  - [x] Dihapus file `webapp.py`, folder `templates/`, dan folder `static/` yang tidak lagi dipakai.
  - [x] Dibersihkan paket web server (`Flask`, `Jinja2`, `Werkzeug`, `blinker`, `itsdangerous`) dari `requirements.txt`.
- [x] **6.2 Unit Testing & Integration Testing**
  - [x] Dibuat unit test suite di **[tests/test_clipper.py](file:///home/dickymuliafiqri/Downloads/Code/cliptzy/tests/test_clipper.py)** untuk pengujian ekstraksi ID YouTube, format waktu, konfigurasi persistence, fonts controller, dan fungsi bersihkan cache.
  - [x] Seluruh unit test terverifikasi lulus 100% (`Ran 4 tests OK`).
- [x] **6.3 Dokumentasi Pembaruan**
  - [x] Diperbarui **[README.md](file:///home/dickymuliafiqri/Downloads/Code/cliptzy/README.md)** dan **[README_EN.md](file:///home/dickymuliafiqri/Downloads/Code/cliptzy/README_EN.md)** dengan panduan arsitektur Desktop GUI Standalone, petunjuk penggunaan, dan instruksi build PyInstaller.


---

## 🛠️ Ringkasan Perubahan Arsitektur

```
[SEBELUM]
YouTube URL -> Flask webapp.py (Port 5000) -> Web Browser (HTML/JS) -> Core Modules -> FFmpeg/Whisper

[SESUDAH]
YouTube URL -> Desktop GUI (PyQt6/PyWebView) -> Controller Layer -> Worker Thread -> Core Modules -> FFmpeg/Whisper
```
