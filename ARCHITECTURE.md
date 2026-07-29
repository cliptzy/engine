# 🏗️ ARCHITECTURE.md — Struktur & Desain Sistem Cliptzy

Dokumen ini mendeskripsikan arsitektur sistem dari **Cliptzy Desktop Standalone**. Aplikasi ini menggunakan arsitektur *Three-Tier* (Tiga Lapisan) yang dirancang untuk memisahkan logika UI, alur kerja (controller), dan pemrosesan utama (engine).

## 1. Pemisahan Lapisan (Layer Separation)

Aplikasi dibangun dengan memisahkan UI dan Engine (Core) yang dihubungkan oleh Controller.

### A. UI Layer (`gui/`)
Bertanggung jawab murni atas antarmuka pengguna (tampilan), tata letak, penerimaan input dari user, dan pembaruan visual. Dibangun menggunakan **PyQt6**.
- **`app.py`**: Inisialisasi aplikasi Qt dan peluncuran main window.
- **`main_window.py`**: Window utama aplikasi yang memuat layout dasar, sidebar, header, dan mengatur navigasi antar halaman (menggunakan `QStackedWidget`).
- **`styles.py`**: Definisi CSS/stylesheet untuk tema gelap aplikasi.
- **`utils.py`**: Fungsi utilitas UI seperti `get_app_icon`.
- **`workers.py`**: Implementasi `QThread` (seperti `PreviewWorker`, `ScanWorker`, `ClipWorker`, `SubtitlePreviewWorker`, `AIScanWorker`) untuk menjalankan tugas I/O atau pemrosesan berat di latar belakang agar UI tetap responsif.
- **`widgets/`**: Modul UI yang dipecah menjadi komponen lebih kecil.
  - `ai_settings_widget.py`: Antarmuka khusus untuk konfigurasi layanan AI (Provider, Host/Key, Model Name).
  - `auto_upload_widget.py`: Antarmuka untuk fitur auto upload dan distribusi.
  - `creator_hub_widget.py`: Antarmuka untuk mencari dan memilih video dari berbagai kreator.
  - `header_widget.py`: Navigasi bagian atas (top bar) atau status bar.
  - `log_console_widget.py`: Widget untuk menampilkan log proses dan progres operasi (clipping/scanning).
  - `media_player_widget.py`: Widget pemutar video untuk preview hasil klip.
  - `preview_widget.py`: Widget untuk preview timeline, heatmap scan, dan deteksi segmen AI.
  - `clip_config_widget.py`: Antarmuka konfigurasi (Mode crop, rasio, subtitle, aset video intro/outro).
  - `sidebar_widget.py`: Navigasi menu samping aplikasi.
  - `video_input_widget.py`: Input pencarian URL YouTube.

### B. Controller Layer (`core/controller.py`)
Bertindak sebagai penghubung antara UI Layer dan Engine Layer.
- **Tugas**: 
  - Menerima dan memvalidasi input dari UI.
  - Mengelola *state* (status) global dari aplikasi.
  - Mengorkestrasi pemanggilan ke modul-modul di *Engine Layer*.
  - Menyediakan *interface* terpusat untuk *worker threads* yang berjalan di latar belakang sehingga UI tidak memanggil langsung fungsi berat di *Engine Layer*.

### C. Engine Layer (`core/`)
Lapisan murni yang tidak memiliki ketergantungan pada UI (PyQt6). Berisi inti pemrosesan data, pengolahan file, dan operasi jaringan.
- **`ai_detector.py`**: Logika deteksi *highlight* menggunakan LLM (Ollama, Gemini API, OpenAI API).
- **`channel_manager.py`**: Logika manajemen dan kurasi channel YouTube kreator.
- **`config.py`**: Pengelolaan konfigurasi aplikasi (membaca dan menyimpan ke `config.json`).
- **`ffmpeg.py`**: Wrapper untuk pemanggilan perintah komando FFmpeg.
- **`logger.py`**: Sistem logging terpusat yang menulis log ke file lokal di folder `logs/`.
- **`processor.py`**: Logika utama untuk pemotongan (cropping), penambahan padding, serta penggabungan video (stacking split-screen).
- **`subtitle.py`**: Ekstraksi transkripsi menggunakan Whisper (atau Faster-Whisper) dan pemformatan file `.ass`.
- **`utils.py`**: Fungsi utilitas untuk system pathing, pengecekan dependensi, dan helper IO lainnya.
- **`youtube.py`**: Modul integrasi `yt-dlp` untuk mengunduh video dan mengekstrak metadata dari YouTube.

## 2. Manajemen Threading & Aliran Data (Data Flow)

Cliptzy memiliki kebijakan **Non-Blocking UI**. Oleh karena itu:
- Fungsi berat (seperti `yt-dlp` download, `Whisper` transkripsi, `FFmpeg` filter) **DILARANG** dijalankan di *Main Thread* GUI.
- **QThread (di `gui/workers.py`)**: Digunakan untuk mengeksekusi operasi tersebut. Setiap worker mengkomunikasikan progres, error, dan hasil akhirnya ke UI melalui sistem **Qt Signals & Slots**.
- **Cancellation**: Controller dan Worker mendukung pengecekan flag `is_cancelled` untuk menghentikan pemrosesan (`yt-dlp`, FFmpeg subprocess) dengan aman dan membersihkan *temporary files*.

## 3. Direktori Penyimpanan Lokal (Local Storage & Cache)

- **`clips/`**: Menyimpan hasil render `.mp4` akhir.
- **`logs/`**: Menyimpan berkas log dari jalannya aplikasi dan pesan error (`cliptzy.log`).
- **`config.json`**: Menyimpan preferensi yang disetel oleh pengguna (misal pengaturan AI, rasio crop, konfigurasi subtitle).
- **`cookies.txt`**: File autentikasi Netscape untuk `yt-dlp` guna mengakses video yang memiliki restriksi usia atau akun.
- **`bin/ffmpeg`**: (Opsional) Lokasi internal untuk *standalone* binary FFmpeg jika aplikasi dirilis secara bundling.

## 4. Standalone & Bundling
- Aplikasi ini dapat di-*compile* dengan PyInstaller atau Nuitka.
- Semua pemanggilan *path* file (seperti font atau aset UI) menggunakan *relative path* berbasis *execution root* (melalui `sys._MEIPASS` untuk *frozen executable*) seperti yang terimplementasi di fungsi-fungsi *utils*.

---

*Dokumen ini diperbarui secara berkala mengikuti arsitektur terkini dari proyek refactoring Cliptzy.*
