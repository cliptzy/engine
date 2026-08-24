# 📜 AGENTS.md — Peraturan Ketat AI Model & Pengembang

Dokumen ini berisi **peraturan ketat dan pedoman arsitektur** yang **WAJIB** dipatuhi oleh seluruh AI Model (Antigravity, subagents, LLM) dan pengembang human yang bekerja pada proyek **Cliptzy AI Engine** — sebuah **FastAPI REST API Server** yang menyediakan layanan pemrosesan video AI untuk aplikasi desktop Cliptzy (Tauri).

> ⚠️ **Dokumen ini adalah kontrak kerja.** Setiap pelanggaran terhadap aturan di bawah ini berpotensi menyebabkan kegagalan API, crash engine, atau menurunkan kualitas output video. Baca seluruh dokumen ini **sebelum** menulis/mengubah satu baris kode pun.

---

## 🏗️ KONTEKS ARSITEKTUR

Proyek ini adalah **AI Engine** yang berjalan sebagai **FastAPI HTTP Server** lokal. Engine ini:
- **Diluncurkan** oleh Rust (Tauri) sebagai child process.
- **Berkomunikasi** dengan Tauri frontend melalui REST API di `127.0.0.1`.
- **Tidak memiliki GUI sendiri** — semua UI ditangani oleh Tauri/Vue.
- **Entry point tunggal**: `server.py` (dijalankan via `python server.py --port <PORT>`).
- **Tidak ada eksekusi CLI** — tidak ada `main.py --url ... --crop ...` atau argparse interactive.

---

## 🚫 1. LARANGAN UTAMA (STRICT PROHIBITIONS)

### 1.1 DILARANG MENGGUNAKAN FRAMEWORK GUI (FLET, PYQT, TKINTER, DLL.)

- Engine ini adalah **headless API server**. Tidak boleh ada import atau dependensi ke library GUI manapun.
- Dilarang keras mengimpor `flet`, `flet-video`, `flet-audio`, `PyQt6`, `tkinter`, `pystray`, `desktop-notifier`, atau library GUI lainnya.
- Semua interaksi user dilakukan melalui Tauri (Vue) → Rust → HTTP API → Engine.

### 1.2 DILARANG PROSES HEAVY I/O DI MAIN API THREAD

- Tidak boleh ada pemanggilan `yt_dlp`, `subprocess.run()`, `WhisperModel.transcribe()`, atau operasi file berukuran besar di handler API secara sinkron.
- Setiap task berat **WAJIB** dieksekusi menggunakan background task (`asyncio.create_task`, `asyncio.to_thread`, atau `BackgroundTasks` FastAPI) dan di-track via Job Manager.

### 1.3 DILARANG HARDCODE PATH ABSOLUT LOKAL

- Dilarang keras menuliskan path sistem lokal (seperti `/home/user/...` atau `C:\Users\...`) di dalam kode.
- Seluruh path harus bersifat relatif terhadap root engine atau menggunakan helper terpusat di `core/utils.py` (`get_app_root()`, dll.).

### 1.4 🚨 DILARANG MENGGUNAKAN `sys.executable` UNTUK MENJALANKAN SUBPROCESS PYTHON / PIP

- **LARANGAN MUTLAK.** Dilarang keras menulis kode yang memanggil interpreter Python atau `pip` melalui `sys.executable`.
- **Kenapa dilarang?** Engine ini akan di-deploy sebagai Portable Python bundle. Nilai `sys.executable` mungkin tidak menunjuk ke interpreter yang diharapkan.
- **Alternatif yang benar:**
  - Gunakan Python API langsung dari pustaka (mis. `edge_tts.Communicate(...)`).
  - Untuk subprocess (FFmpeg, yt-dlp, ffprobe), panggil **binary eksternal** — **bukan** `sys.executable`.

### 1.5 DILARANG MEMATIKAN DUKUNGAN SUBTITLE / FFMPEG DENGAN FIX DUMMY

- Dilarang menyembunyikan error atau mengembalikan nilai _dummy/empty fallback_ saat pemrosesan subtitle atau cropping gagal.
- Setiap kegagalan harus memiliki penanganan error eksplisit dan pesan log yang rinci.

### 1.6 DILARANG MENGUBAH ALGORITMA CORE VIDEO CROP & TIMELINE TANPA VERIFIKASI

- Dilarang mengubah rumus perhitungan crop, vstack split-screen, atau penyusunan file `.ass` subtitle di `core/` tanpa pengujian empiris.

### 1.7 DILARANG MENAMBAHKAN DEPENDENSI BARU TANPA PROSES RESMI

- Dilarang mengedit `requirements.txt` secara manual.
- WAJIB menggunakan `uv add <nama-paket>` untuk menambah dependensi.

### 1.8 DILARANG MEMBUAT ENDPOINT CLI / ARGPARSE INTERACTIVE

- Engine ini **hanya** berjalan sebagai API server. Tidak boleh ada entry point CLI interactive seperti `main.py --url ... --crop ...`.
- Satu-satunya argparse yang diperbolehkan adalah untuk konfigurasi server: `server.py --port <PORT> --host <HOST>`.

---

## 🏗️ 2. ATURAN ARSITEKTUR & SEPARATION OF CONCERNS

1. **Pemisahan Lapisan Tiga Tingkat (Three-Tier Architecture)**:
   - **API Layer (`api/`)**: Endpoint HTTP (FastAPI routers). Menerima request, memvalidasi input, mendelegasikan ke Controller/Core, dan mengembalikan response JSON.
   - **Controller Layer (`core/controller.py`)**: Mengelola alur kerja (workflow), validasi bisnis, koordinasi antar-modul core, dan manajemen job/task.
   - **Engine Core Layer (`core/`)**: Modul murni pemrosesan video, YouTube API, transkripsi Whisper, dan FFmpeg filter. Layer ini **tidak boleh memiliki ketergantungan** pada pustaka GUI atau framework web (FastAPI boleh hanya di `api/` layer).
2. **Stateless API Design**:
   - Setiap request harus bersifat stateless. State persisten disimpan di filesystem (config.json, output files) atau in-memory job store.
   - Gunakan Job ID untuk melacak operasi yang berjalan lama (long-running tasks).
3. **Konsistensi Dokumentasi**:
   - Setiap perubahan arsitektur/modul **WAJIB** disinkronkan ke `ARCHITECTURE.md`, `README.md`, `README_EN.md`, dan `CHANGELOG.md`.

---

## 🧵 3. ATURAN MANAJEMEN THREADING & RESPONSIVITAS API

1. **Non-Blocking API Policy**:
   - API tidak boleh mengalami kondisi timeout atau hang saat sedang memproses video.
   - Operasi berat harus di-offload ke background task dan di-track via Job Manager.
2. **Arsitektur Async Task**:
   - Pekerjaan latar belakang WAJIB diimplementasikan menggunakan `asyncio.create_task()` atau `asyncio.to_thread()` untuk blocking I/O.
   - Job Manager menyimpan status setiap job: `queued`, `running`, `completed`, `failed`, `cancelled`.
3. **Cancellation Handling**:
   - Setiap job harus mendukung pembatalan. Worker task harus secara berkala mengecek flag pembatalan (`is_cancelled`) untuk menghentikan subprocess FFmpeg/yt-dlp secara aman.
4. **Pembersihan Temporary File**:
   - Semua file temporer wajib dibersihkan secara otomatis jika proses selesai atau terjadi kegagalan/pembatalan.

---

## 📂 4. ATURAN PENGELOLAAN DEPENDENSI

1. **Kompatibilitas Portable Python**:
   - Seluruh kode harus kompatibel dengan Portable Python environment (python-build-standalone).
   - Deteksi lokasi executable FFmpeg harus mendukung pencarian di PATH sistem dan direktori engine (`bin/ffmpeg`).
2. **Manajemen Model Whisper**:
   - Pengunduhan model Faster-Whisper harus didukung via API endpoint (`POST /subtitle/models/download`).
   - Status download model harus bisa di-query via `GET /subtitle/models`.
3. **Manajemen Pustaka (Dependency Management) yang Ketat dengan `uv`**:
   - WAJIB menggunakan `uv` (Astral) untuk segala aktivitas manajemen dependensi.
   - **Penambahan Paket**: `uv add "nama-paket"`
   - **Penghapusan Paket**: `uv remove "nama-paket"`
   - **Sinkronisasi**: `uv sync`

---

## 📋 5. ATURAN LOGGING & DIAGNOSIS ERROR

1. **Structured Logging**:
   - Gunakan logger terpusat di `core/logger.py`. Semua log ditulis ke file (`logs/cliptzy.log`) dan stdout.
   - Log output dari subprocess FFmpeg dan yt-dlp harus dialirkan ke logger terpusat.
   - Semua modul yang memakai yt-dlp **wajib** meneruskan log ke logger terpusat.
2. **Investigasi Error Berbasis Log Empiris**:
   - AI Model harus mengekstrak log lengkap sebelum mendiagnosis penyebab utama error. Dilarang menebak tanpa _stack trace_.
3. **API Error Responses**:
   - Semua error harus dikembalikan sebagai JSON response dengan field `error`, `detail`, dan HTTP status code yang sesuai.
   - Dilarang mengembalikan HTML error page atau plain text error.

---

## 🎭 6. ATURAN PENGELOLAAN VIDEO EFFECTS

Sistem efek video dikelola melalui `VideoEffectManager` di `core/video_effects.py`.

1. **Sentralisasi Melalui Manager**: Dilarang hardcode pencocokan emosi di luar `VideoEffectManager`.
2. **Aturan Audio**: Semua efek video wajib memiliki `audio_filter` dengan volume lebih rendah dari audio utama.
3. **Kesesuaian Filter FFmpeg**: Pastikan filter FFmpeg mendukung evaluasi timeline.

---

## 🧪 7. ATURAN VERIFIKASI SEBELUM MENYATAKAN SELESAI

Setiap pekerjaan dianggap **SELESAI** hanya apabila:

- [ ] **WAJIB** menjalankan `make typecheck` dengan **0 errors**.
- [ ] Kode berjalan tanpa syntax error atau missing import.
- [ ] API endpoint bisa diuji menggunakan `httpx` / `curl` / test suite.
- [ ] Operasi pemrosesan klip menghasilkan file output `.mp4` yang valid.
- [ ] Log menunjukkan tidak ada error fatal.
- [ ] Tidak ada penggunaan `sys.executable` di kode production (`core/` dan `api/`).
- [ ] Tidak ada path absolut lokal yang di-hardcode.
- [ ] Tidak ada import GUI library (`flet`, `PyQt6`, dll.).
- [ ] Dokumentasi sinkron dengan perubahan kode.
- [ ] Tidak ada dependensi baru tanpa `uv add`.

---

## 📌 8. DAFTAR KESALAHAN YANG PERNAH TERJADI (JANGAN DIULANGI)

1. **`sys.executable -m edge_tts`** → Gunakan `edge_tts.Communicate` (Python API) langsung.
2. **`pip install` via `sys.executable`** → Dilarang. Semua dependensi harus sudah ada di bundle.
3. **Dokumentasi tidak sinkron** → WAJIB perbarui dokumentasi setiap kali arsitektur berubah.
4. **FFmpeg AST Node Limit** → Batasi `MAX_KEYFRAMES = 85` dan lakukan simplifikasi iteratif.

---

## 🔌 9. ATURAN API DESIGN

1. **REST Convention**:
   - Gunakan HTTP methods yang tepat: `GET` untuk read, `POST` untuk create/action, `DELETE` untuk cancel.
   - Gunakan path parameters untuk resource ID: `/clipper/progress/{job_id}`.
   - Response selalu JSON dengan struktur konsisten.

2. **Long-Running Operations**:
   - Endpoint yang memulai operasi berat harus mengembalikan `202 Accepted` dengan `job_id`.
   - Client melakukan polling via `GET /clipper/progress/{job_id}` atau subscribe ke SSE stream.

3. **Error Handling**:
   ```python
   # Contoh response error
   {"error": "VideoNotFound", "detail": "Video with ID 'xxx' not found on YouTube", "status": 404}
   ```

4. **CORS**:
   - CORS **tidak diperlukan** karena API hanya diakses oleh Rust (bukan browser langsung).
   - Jangan tambahkan CORS middleware kecuali benar-benar dibutuhkan.

5. **Security**:
   - API hanya bind ke `127.0.0.1` (localhost). DILARANG bind ke `0.0.0.0`.
   - Tidak perlu authentication karena hanya diakses oleh proses lokal (Rust orchestrator).

---

_Peraturan dalam AGENTS.md ini mengikat untuk semua aktivitas pengembangan proyek Cliptzy Engine. Pelanggaran terhadap Larangan 1.4 (`sys.executable`) dan 1.1 (GUI library) dianggap **bug kritis** dan mengharuskan perbaikan segera._
