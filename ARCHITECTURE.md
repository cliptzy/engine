# 🏗️ ARCHITECTURE.md — Struktur & Desain Sistem Cliptzy

Dokumen ini mendeskripsikan arsitektur sistem dari **Cliptzy Desktop Standalone**. Aplikasi ini menggunakan arsitektur _Three-Tier_ (Tiga Lapisan) yang dirancang untuk memisahkan logika UI, alur kerja (controller), dan pemrosesan utama (engine).

## 1. Pemisahan Lapisan (Layer Separation)

Aplikasi dibangun dengan memisahkan UI dan Engine (Core) yang dihubungkan oleh Controller.

### A. UI Layer (`gui/`)

Bertanggung jawab murni atas antarmuka pengguna (tampilan), tata letak, penerimaan input dari user, dan pembaruan visual. Dibangun menggunakan **Flet**.

- **`app.py`**: Inisialisasi aplikasi Flet dan tata letak dasar.
- **`router.py`**: Navigasi dan routing view aplikasi.
- **`state.py`**: Pengelolaan status reaktif aplikasi.
- **`theme.py`**: Konfigurasi tema gelap Flet.
- **`event_bus.py`**: Sistem komunikasi antar-komponen asinkron.
- **`workers.py`**: Implementasi `BackgroundWorker` berbasis multi-threading Python yang thread-safe untuk UI update Flet.
- **`layout/`**: Tata letak dasar (Header, Sidebar, MainLayout, StatusBar).
- **`views/`**: Halaman utama aplikasi (LoginView, ClipperView, CreatorHubView, SettingsView).
- **`components/`**: Komponen visual modular yang reusable (seperti LogViewer, ProgressIndicator, SpinBox, VideoCard, ClipConfig, Preview, dll.).

### B. Controller Layer (`core/controller.py`)

Bertindak sebagai penghubung antara UI Layer dan Engine Layer.

- **Tugas**:
  - Menerima dan memvalidasi input dari UI.
  - Mengelola _state_ (status) global dari aplikasi.
  - Mengorkestrasi pemanggilan ke modul-modul di _Engine Layer_.
  - Menyediakan _interface_ terpusat untuk _worker threads_ yang berjalan di latar belakang sehingga UI tidak memanggil langsung fungsi berat di _Engine Layer_.

### C. Engine Layer (`core/`)

Lapisan murni yang tidak memiliki ketergantungan pada UI (Flet). Berisi inti pemrosesan data, pengolahan file, dan operasi jaringan.

- **`core/ai/detector.py`**: Logika deteksi _highlight_ menggunakan LLM (Ollama, Gemini API, OpenAI API).
- **`channel_manager.py`**: Logika manajemen dan kurasi channel YouTube kreator.
- **`config.py`**: Pengelolaan konfigurasi aplikasi (membaca dan menyimpan ke `config.json`).
- **`ffmpeg.py`**: Wrapper untuk pemanggilan perintah komando FFmpeg.
- **`logger.py`**: Sistem logging terpusat yang menulis log ke file lokal di folder `logs/`.
- **`processor.py`**: Logika utama untuk pemotongan (cropping), penambahan padding, serta penggabungan video (stacking split-screen).
- **`subtitle.py`**: Ekstraksi transkripsi menggunakan Whisper (atau Faster-Whisper) dan pemformatan file `.ass`.
- **`utils.py`**: Fungsi utilitas untuk system pathing, pengecekan dependensi, dan helper IO lainnya.
- **`youtube.py`**: Modul integrasi `yt-dlp` untuk mengunduh video dan mengekstrak metadata dari YouTube.
- **`yt_dlp_logger.py`**: Adapter terpusat yang menjembatani antarmuka logger kustom yt-dlp dengan sistem logging standar Python (`core/logger.py`). Semua pesan yt-dlp secara otomatis muncul di GUI `LogViewer` melalui `EventBusLogHandler`.

## 2. Manajemen Threading & Aliran Data (Data Flow)

Cliptzy memiliki kebijakan **Non-Blocking UI**. Oleh karena itu:

- Fungsi berat (seperti `yt-dlp` download, `Whisper` transkripsi, `FFmpeg` filter) **DILARANG** dijalankan di _Main Thread_ GUI.
- **BackgroundWorker (di `gui/workers.py`)**: Digunakan untuk mengeksekusi operasi tersebut secara asinkron menggunakan multi-threading Python yang aman untuk pembaruan UI Flet.
- **Cancellation**: Controller dan Worker mendukung pengecekan flag `is_cancelled` untuk menghentikan pemrosesan (`yt-dlp`, FFmpeg subprocess) dengan aman dan membersihkan _temporary files_.

## 3. Direktori Penyimpanan Lokal (Local Storage & Cache)

- **`clips/`**: Menyimpan hasil render `.mp4` akhir.
- **`logs/`**: Menyimpan berkas log dari jalannya aplikasi dan pesan error (`cliptzy.log`).
- **`config.json`**: Menyimpan preferensi yang disetel oleh pengguna (misal pengaturan AI, rasio crop, konfigurasi subtitle).
- **`cookies.txt`**: File autentikasi Netscape untuk `yt-dlp` guna mengakses video yang memiliki restriksi usia atau akun.
- **`bin/ffmpeg`**: (Opsional) Lokasi internal untuk _standalone_ binary FFmpeg jika aplikasi dirilis secara bundling.

## 4. Standalone & Bundling

- Aplikasi ini dapat di-_compile_ dengan PyInstaller atau Nuitka.
- Semua pemanggilan _path_ file (seperti font atau aset UI) menggunakan _relative path_ berbasis _execution root_ (melalui `sys._MEIPASS` untuk _frozen executable_) seperti yang terimplementasi di fungsi-fungsi _utils_.

---

_Dokumen ini diperbarui secara berkala mengikuti arsitektur terkini dari proyek refactoring Cliptzy._
