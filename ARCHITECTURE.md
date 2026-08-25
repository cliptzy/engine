# 🏗️ ARCHITECTURE.md — Struktur & Desain Sistem Cliptzy

Dokumen ini mendeskripsikan arsitektur sistem dari **Cliptzy Engine** sebagai backend API yang independen. Proyek ini dibangun sebagai REST API (FastAPI) yang akan dipanggil oleh Rust Orchestrator dan Vue Frontend melalui arsitektur Hybrid Tauri.

## 1. Pemisahan Lapisan (Layer Separation)

Aplikasi dibangun dengan memisahkan API Layer, Controller, dan Core Engine.

### A. API Layer (`api/`)

Bertanggung jawab sebagai interface HTTP yang melayani permintaan dari Rust (proxy dari frontend Vue).
Dibangun menggunakan **FastAPI**.

- **`server.py`**: Entry point utama FastAPI (`uvicorn`). Menginisialisasi server, lifespan event, dan router.
- **`api/health.py`**: Router untuk health checks.
- **`api/clipper.py`**: Router untuk operasi clipping, analyze, compile, dll.
- **`api/subtitle.py`**: Router untuk operasi transkripsi dan ass rendering.
- **`api/upload.py`**: Router untuk auto-upload (YouTube, TikTok, dll).
- **`api/job_manager.py`**: Sistem queue dan job management untuk long-running tasks.

### B. Controller Layer (`core/controller.py`)

Bertindak sebagai orkestrator dan penghubung antara API Layer dan modul Core.
Berisi _business logic_ untuk alur kerja yang melibatkan beberapa modul inti (mis: download -> crop -> transkripsi -> subtitle -> efek -> render).

### C. Engine Layer (`core/`)

Lapisan murni yang tidak memiliki ketergantungan pada interface eksternal. Berisi inti pemrosesan data, pengolahan file, operasi jaringan, dan machine learning.

- **`core/ai/detector.py`**: Logika deteksi _highlight_ menggunakan LLM (Ollama, Gemini API, OpenAI API).
- **`channel_manager.py`**: Logika manajemen dan kurasi channel YouTube kreator.
- **`config.py`**: Pengelolaan konfigurasi aplikasi (membaca dan menyimpan ke `config.json`).
- **`ffmpeg.py`**: Wrapper untuk pemanggilan perintah komando FFmpeg.
- **`logger.py`**: Sistem logging terpusat yang menulis log ke stdout (untuk ditangkap Rust) dan file lokal di folder `logs/`.
- **`processor.py`**: Logika utama untuk pemotongan (cropping), penambahan padding, serta penggabungan video (stacking split-screen).
- **`core/use_cases/compile_video.py`**: Orkestrator eksekusi kompilasi multi-video lokal menjadi kompilasi "Top N", lengkap dengan thumbnail, numbering cards, dan AI metadata.
- **`core/processing/numbering.py`**: Menghasilkan video numbering card beserta narasi TTS singkat untuk mode kompilasi.
- **`core/processing/thumbnail.py`**: Ekstraksi frame video dan overlay efek untuk membuat thumbnail dinamis atau thumbnail collage.
- **`subtitle.py`**: Ekstraksi transkripsi menggunakan Whisper (atau Faster-Whisper) dan pemformatan file `.ass`.
- **`utils.py`**: Fungsi utilitas untuk system pathing, pengecekan dependensi, dan helper IO lainnya.
- **`youtube.py`**: Modul integrasi `yt-dlp` untuk mengunduh video dan mengekstrak metadata dari YouTube.
- **`yt_dlp_logger.py`**: Adapter terpusat yang menjembatani antarmuka logger kustom yt-dlp dengan sistem logging standar Python (`core/logger.py`).

## 2. Manajemen Threading & Aliran Data (Data Flow)

Engine Cliptzy berfungsi sebagai background processor. Oleh karena itu:

- API call yang berat (seperti transkripsi, rendering) berjalan melalui **Job Queue**.
- Endpoint REST langsung mengembalikan response _202 Accepted_ dan `job_id`.
- Operasi sinkron (seperti `subprocess.call` untuk FFmpeg) **HARUS** di-offload ke background thread menggunakan `asyncio.to_thread` atau dijalankan di worker async terpisah agar tidak memblokir _event loop_ FastAPI.

## 3. Direktori Penyimpanan Lokal (Local Storage & Cache)

- **`clips/`**: Menyimpan hasil render `.mp4` akhir.
- **`logs/`**: Menyimpan berkas log dari jalannya aplikasi dan pesan error (`cliptzy.log`).
- **`config.json`**: Menyimpan preferensi yang disetel oleh pengguna (misal pengaturan AI, rasio crop, konfigurasi subtitle).
- **`cred/`**: Folder penyimpan kredensial atau cookie (`yt_cookies.txt`, `tiktok_cookies.txt`, dsb).
- **`fonts/`**: Koleksi file font untuk render ASS.

## 4. Distribusi Engine (Portable)

- Engine ini dipaket ke dalam arsip `engine.zip` terpisah dari aplikasi Tauri utama.
- Berisi _Portable Python_ environment (atau virtualenv mandiri).
- Akan diekstrak otomatis oleh fitur _Bootstrapper_ milik Rust Orchestrator.

---

_Dokumen ini diperbarui secara berkala mengikuti arsitektur FastAPI (Tauri Hybrid)._
