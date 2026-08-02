# 📜 AGENTS.md — Peraturan Ketat AI Model & Pengembang

Dokumen ini berisi **peraturan ketat dan pedoman arsitektur** yang **WAJIB** dipatuhi oleh seluruh AI Model (Antigravity, subagents, LLM) dan pengembang human yang bekerja pada proyek refactoring **Cliptzy Desktop Standalone**.

---

## 🚫 1. LARANGAN UTAMA (STRICT PROHIBITIONS)

1. **DILARANG MENGGUNAKAN SERVER FLASK / HTTP DALAM PRODUCTION DESKTOP APP**
   - Refactoring desktop GUI standalone harus murni berjalan sebagai proses desktop native tanpa membuat HTTP web server lokal (tidak ada `app.run()`, `localhost:5000`, atau membuka browser web eksternal).
2. **DILARANG PROSES HEAVY I/O DI MAIN UI THREAD**
   - Tidak boleh ada pemanggilan `yt_dlp`, `subprocess.run()`, `WhisperModel.transcribe()`, atau operasi file berukuran besar di Main Thread GUI. Setiap task berat wajib dieksekusi di background worker thread (`QThread` / `threading.Thread`).
3. **DILARANG HARDCODE PATH ABSOLUT LOKAL**
   - Dilarang keras menuliskan path sistem lokal (seperti `/home/user/...` atau `C:\Users\...`) di dalam kode. Seluruh path harus bersifat relatif terhadap root aplikasi atau lokasi biner executable (`sys._MEIPASS` / `os.path.dirname(sys.executable)`).
4. **DILARANG MEMATIKAN DUKUNGAN SUBTITLE / FFMPEG DENGAN FIX DUMMY**
   - Dilarang menyembunyikan error atau mengembalikan nilai _dummy/empty fallback_ saat pemrosesan subtitle atau cropping gagal. Setiap kegagalan harus memiliki penanganan error eksplisit (_graceful degradation_) dan pesan log yang rinci.
5. **DILARANG MENGUBAH ALGORITMA CORE VIDEO CROP & TIMELINE TANPA VERIFIKASI**
   - Dilarang mengubah rumus perhitungan crop, vstack split-screen (`get_split_heights`), atau penyusunan file `.ass` subtitle di `core/` tanpa pengujian empiris bahwa output video tetap valid.

---

## 🏗️ 2. ATURAN ARSITEKTURA & SEPARATION OF CONCERNS

1. **Pemisahan Lapisan Tiga Tingkat (Three-Tier Architecture)**:
   - **UI Layer (`gui/`)**: Hanya bertanggung jawab atas tampilan, komponen widget, layout, input user, dan visualisasi status.
   - **Controller Layer (`core/controller.py`)**: Mengelola state aplikasi, alur kerja (workflow), validasi input, serta koordinasi antarthread.
   - **Engine Core Layer (`core/`)**: Modul murni pemrosesan video, YouTube API, transkripsi Whisper, dan FFmpeg filter. Layer ini tidak boleh memiliki ketergantungan pada pustaka GUI (`PyQt6`, `tkinter`, dll.).
2. **Sistem Event & Callback Thread-Safe**:
   - Seluruh pembaruan dari `core/` ke GUI harus melalui event hook atau Qt Signal. Jangan pernah memanggil fungsi pembaruan UI secara langsung dari thread latar belakang.

---

## 🧵 3. ATURAN MANAJEMEN THREADING & RESPONSIFITAS UI

1. **Non-Blocking UI Policy**:
   - Aplikasi tidak boleh mengalami kondisi _not responding_ atau _freeze_ saat sedang mengunduh video, memotong video, atau mengekstrak subtitle.
2. **Arsitektur Native Async Task Flet (DILARANG MENGGUNAKAN `threading.Thread`)**:
   - Sejak Flet 0.80+, pemanggilan `threading.Thread` murni dari Python akan membuat thread kehilangan konteks sesi (_session contextvars_) WebSocket, menyebabkan pembaruan UI (seperti `page.update()`) tidak terkirim secara *real-time* ke antarmuka pengguna.
   - Pekerjaan latar belakang (background workers) **WAJIB** diimplementasikan menggunakan fungsi _async_ dan dieksekusi melalui `self.page.run_task(nama_fungsi)`.
   - Untuk melakukan pemblokiran I/O dari inti program di dalam task async, gunakan `await asyncio.to_thread(fungsi_blocking, args)`.
3. **Cancellation Handling**:
   - Fitur pembatalan (_Abort/Cancel Job_) harus didukung. Worker thread harus secara berkala mengecek flag pembatalan (`is_cancelled`) untuk menghentikan proses subprocess FFmpeg/yt-dlp secara aman tanpa meninggalkan file sampah (_leftover temp files_).
4. **Pembersihan Temporary File**:
   - Semua file mentah temporer (`*_raw.mkv`, `*.ass`, `*_nosub.mp4`) wajib dibersihkan secara otomatis jika proses selesai atau terjadi kegagalan/pembatalan.

---

## 📂 4. ATURAN PENGELOLAAN DEPENDENSI & STANDALONE BUNDLING

1. **Kompatibilitas Standalone Executive**:
   - Seluruh impor dependensi harus kompatibel dengan PyInstaller / Nuitka.
   - Deteksi lokasi executable FFmpeg harus mendukung pencarian di PATH sistem, direktori aplikasi internal (`bin/ffmpeg`), serta installer OS lokal.
2. **Manajemen Model Whisper**:
   - Pengunduhan model Faster-Whisper harus didukung secara terisolasi. Jika model belum ada di cache, tampilkan indikator unduhan di GUI sebelum proses clipping dimulai.
3. **Struktur Pembatalan Paket Web**:
   - Modul Flask (`webapp.py`, `templates/`, `static/`) yang sudah tidak dipakai harus diisolasi atau dihapus secara aman setelah GUI Desktop murni selesai diimplementasikan.
4. **Manajemen Pustaka (Dependency Management) yang Ketat**:
   - DILARANG mengedit `requirements.txt` secara manual atau menggunakan perintah `pip freeze > requirements.txt` biasa karena akan mengotori daftar dependensi dengan *sub-dependencies*.
   - Pustaka inti (Top-Level) HANYA boleh didaftarkan di dalam berkas `requirements.in`.
   - AI Model dan Pengembang WAJIB menggunakan script `scripts/manage_reqs.py` (berbasis `pip-tools`) untuk segala aktivitas manajemen dependensi:
     - **Penambahan**: Gunakan perintah `python scripts/manage_reqs.py add "nama-paket"` untuk menginstal pustaka baru (otomatis mengompilasi ulang dan melakukan sinkronisasi).
     - **Kompilasi**: Gunakan `python scripts/manage_reqs.py compile` untuk merapikan dan mengunci versi paket (lock) ke dalam `requirements.txt`.
     - **Sinkronisasi**: Gunakan `python scripts/manage_reqs.py sync` untuk memastikan *virtual environment* bebas dari pustaka yatim (*orphans*) dan paket sisa yang tak terpakai.

---

## 📋 5. ATURAN LOGGING & DIAGNOSIS ERROR

1. **Silent Log Inspection & Professional Reporting**:
   - Gunakan logger terpusat di `core/logger.py`. Log output dari subprocess FFmpeg dan yt-dlp harus dialirkan secara _real-time_ ke file log lokal (`logs/cliptzy.log`) dan ke widget log viewer di GUI.
2. **Investigasi Error Berbasis Log Empiris**:
   - Jika terjadi _runtime error_ atau _crash_, AI Model harus mengekstrak log lengkap sebelum mendiagnosis penyebab utama. Dilarang menebak-nebak tanpa melihat _stack trace_.

---

## 🛡️ 6. ATURAN TYPE CHECKING & PYLANCE (FLET MIGRATION)

1. **Resolusi Strict Typing Flet Event Handlers**:
   - Dilarang memberikan anotasi spesifik `(e: ft.ControlEvent)` pada fungsi _event handler_ jika memicu error _contravariance_ dari Pylance (seperti *"is not assignable to type Event[Button]"*). Gunakan parameter `(e)` tanpa anotasi untuk menghindari bentrok tipe generik.
2. **Pengecualian Properti Dinamis Flet (Type Ignore)**:
   - Flet mendefinisikan event parameter dengan *base class* (seperti `_BaseControlType`) yang secara bawaan tidak menyimpan metadata properti spesifik subclass (contoh: `.value`, `.selected_index`). Gunakan komentar `# type: ignore` secara selektif saat mengakses properti turunan tersebut agar Pylance tidak menganggapnya sebagai error.
3. **Casting Koleksi List**:
   - Saat mendeklarasikan list yang berisi berbagai macam subclass Flet (contoh campuran `ft.IconButton`, `ft.Text`, `ft.Slider`), Anda **WAJIB** membungkusnya menggunakan `typing.cast(list[ft.Control], [...])`. Hal ini mencegah Pylance mengunci inferensi tipe ke spesifik _union_ subclass yang membuat list tersebut _invariant_ (ditolak saat dilempar ke parameter `controls=`).

---

## 🧪 7. ATURAN VERIFIKASI SEBELUM MENYATAKAN SELESAI

Setiap pekerjaan refactoring atau penambahan fitur dianggap **SELESAI** hanya apabila AI Model telah memenuhi kriteria berikut:

- [ ] Kode terkompilasi / berjalan tanpa syntax error atau missing import error, **serta lulus evaluasi Pylance / `pyright` dengan 0 errors.**
- [ ] Fitur GUI dapat diluncurkan dan diuji secara empiris (menjalankan tes atau script verifikasi).
- [ ] Operasi pemrosesan klip menghasilkan file output `.mp4` yang valid di direktori tujuan.
- [ ] Log menunjukkan tidak ada error fatal yang disembunyikan.

---

_Peraturan dalam AGENTS.md ini mengikat untuk semua aktivitas pengembangan proyek Cliptzy._
