# 📜 AGENTS.md — Peraturan Ketat AI Model & Pengembang

Dokumen ini berisi **peraturan ketat dan pedoman arsitektur** yang **WAJIB** dipatuhi oleh seluruh AI Model (Antigravity, subagents, LLM) dan pengembang human yang bekerja pada proyek **Cliptzy Desktop Standalone** pasca-migrasi ke **Flet**.

> ⚠️ **Dokumen ini adalah kontrak kerja.** Setiap pelanggaran terhadap aturan di bawah ini berpotensi menyebabkan _crash_ aplikasi di production (khususnya pada _frozen executable_), merusak arsitektur, atau menurunkan kualitas output video. Baca seluruh dokumen ini **sebelum** menulis/mengubah satu baris kode pun.

---

## 🚫 1. LARANGAN UTAMA (STRICT PROHIBITIONS)

### 1.1 DILARANG MENGGUNAKAN SERVER FLASK / HTTP DALAM PRODUCTION DESKTOP APP

- Aplikasi desktop standalone harus murni berjalan sebagai proses desktop native (Flet Desktop App) **tanpa** membuat HTTP web server lokal (tidak ada `app.run()`, `localhost:5000`, atau membuka browser web eksternal untuk core UI).
- Modul web lama (`webapp.py`, `templates/`, `static/`) yang sudah tidak dipakai **harus dihapus**, bukan sekadar diabaikan.

### 1.2 DILARANG PROSES HEAVY I/O DI MAIN UI THREAD

- Tidak boleh ada pemanggilan `yt_dlp`, `subprocess.run()`, `WhisperModel.transcribe()`, atau operasi file berukuran besar di Main Thread GUI Flet.
- Setiap task berat **WAJIB** dieksekusi menggunakan arsitektur asinkron Flet (`page.run_task`) dan didelegasikan ke thread executor menggunakan `await asyncio.to_thread(...)`.

### 1.3 DILARANG HARDCODE PATH ABSOLUT LOKAL

- Dilarang keras menuliskan path sistem lokal (seperti `/home/user/...` atau `C:\Users\...`) di dalam kode.
- Seluruh path harus bersifat relatif terhadap root aplikasi atau lokasi biner executable.
- **Gunakan helper terpusat** (mis. `core/utils.py` → `get_app_root()`, `core/config.py` → `get_user_data_dir()`) yang sudah menangani deteksi `frozen` dengan benar. **JANGAN** menulis logika deteksi path sendiri di modul lain.

### 1.4 🚨 DILARANG MENGGUNAKAN `sys.executable` UNTUK MENJALANKAN SUBPROCESS PYTHON / PIP (PENYEBAB CRASH FROZEN EXECUTABLE)

- **LARANGAN MUTLAK.** Dilarang keras menulis kode yang memanggil interpreter Python atau `pip` melalui `sys.executable`, contoh:
  - `subprocess.run([sys.executable, "-m", "edge_tts", ...])` ❌
  - `subprocess.run([sys.executable, "-m", "pip", "install", ...])` ❌
  - `subprocess.run([sys.executable, "-m", "piptools", "compile", ...])` ❌
- **Kenapa dilarang?** Saat aplikasi dikompilasi menjadi _frozen executable_ (PyInstaller / `flet build` / Nuitka), nilai `sys.executable` **tidak lagi menunjuk ke interpreter Python**, melainkan **menunjuk ke biner aplikasi itu sendiri** (mis. `cliptzy.exe`). Akibatnya:
  - Menjalankan `sys.executable -m <modul>` akan membuat aplikasi **memanggil dirinya sendiri**, menyebabkan _crash_, perilaku tak terduga, atau loop.
  - `pip install` akan gagal karena `sys.executable` bukan interpreter Python.
  - Ini adalah **bug kritis production** yang pernah terjadi (lihat `CHANGELOG.md` v3.0.1 — edge-tts) dan **tidak boleh terulang**.
- **Alternatif yang benar:**
  - **Gunakan Python API langsung** dari pustaka (mis. `edge_tts.Communicate(...)` + `asyncio.run()`) alih-alih subprocess `-m`.
  - Untuk operasi yang memang membutuhkan subprocess (FFmpeg, yt-dlp, ffprobe), panggil **binary eksternal** (FFmpeg/ffprobe) — **bukan** `sys.executable`.
  - Jika benar-benar membutuhkan `pip` saat runtime, **guard dengan `getattr(sys, 'frozen', False)`** dan **jangan** jalankan saat frozen (lihat `core/utils.py`). Lebih baik lagi: **hindari pemasangan paket saat runtime** — semua dependensi wajib sudah ada di bundle.
  - Script pengembangan lama (`scripts/manage_reqs.py`) dan `build_executable.py` adalah **alat pengembangan/build-time** yang berjalan di environment Python developer — di sana `sys.executable` sah. Aturan ini berlaku untuk **kode yang berjalan di dalam aplikasi production** (`core/` dan `gui/`).

### 1.5 DILARANG MEMATIKAN DUKUNGAN SUBTITLE / FFMPEG DENGAN FIX DUMMY

- Dilarang menyembunyikan error atau mengembalikan nilai _dummy/empty fallback_ saat pemrosesan subtitle atau cropping gagal.
- Setiap kegagalan harus memiliki penanganan error eksplisit (_graceful degradation_) dan pesan log yang rinci.

### 1.6 DILARANG MENGUBAH ALGORITMA CORE VIDEO CROP & TIMELINE TANPA VERIFIKASI

- Dilarang mengubah rumus perhitungan crop, vstack split-screen (`get_split_heights`), atau penyusunan file `.ass` subtitle di `core/` tanpa pengujian empiris bahwa output video tetap valid.

### 1.7 DILARANG MENAMBAHKAN DEPENDENSI BARU TANPA PROSES RESMI

- Dilarang mengedit `requirements.txt` secara manual atau menggunakan `pip freeze > requirements.txt`.
- Dilarang menambah pustaka ke kode tanpa mendaftarkannya melalui manajer paket modern, yakni perintah `uv add <nama-paket>`.

---

## 🏗️ 2. ATURAN ARSITEKTUR & SEPARATION OF CONCERNS

1. **Pemisahan Lapisan Tiga Tingkat (Three-Tier Architecture)**:
   - **UI Layer (`gui/`)**: Hanya bertanggung jawab atas tampilan, komponen widget, layout Flet, input user, dan visualisasi status menggunakan framework Flet.
   - **Controller Layer (`core/controller.py`)**: Mengelola state aplikasi, alur kerja (workflow), validasi input, serta koordinasi antar task/thread.
   - **Engine Core Layer (`core/`)**: Modul murni pemrosesan video, YouTube API, transkripsi Whisper, dan FFmpeg filter. Layer ini **tidak boleh memiliki ketergantungan** pada pustaka GUI (`flet`, `PyQt6`, `tkinter`, dll.).
2. **Sistem Event & Callback Thread-Safe**:
   - Seluruh pembaruan dari `core/` ke GUI harus melalui event hook, EventBus, atau callbacks asinkron. Jangan pernah memanggil fungsi pembaruan UI Flet secara langsung dari thread latar belakang di luar task Flet.
3. **Konsistensi Dokumentasi**:
   - Setiap perubahan arsitektur/modul **WAJIB** disinkronkan ke `ARCHITECTURE.md`, `README.md`, `README_EN.md`, dan `CHANGELOG.md`.
   - Dilarang membiarkan dokumentasi menyebut framework/teknologi lama (mis. menyebut **PyQt6 / QThread / QMediaPlayer**) saat kode sudah Flet — ini menyesatkan AI model berikutnya.

---

## 🧵 3. ATURAN MANAJEMEN THREADING & RESPONSIFITAS UI

1. **Non-Blocking UI Policy**:
   - Aplikasi tidak boleh mengalami kondisi _not responding_ atau _freeze_ saat sedang mengunduh video, memotong video, atau mengekstrak subtitle.
2. **Arsitektur Native Async Task Flet (DILARANG MENGGUNAKAN `threading.Thread` untuk UI Update)**:
   - Pemanggilan `threading.Thread` murni dari Python untuk melakukan pembaruan UI akan membuat thread kehilangan konteks sesi (_session contextvars_) WebSocket Flet, menyebabkan pembaruan UI (seperti `page.update()`) tidak terkirim secara _real-time_ ke antarmuka pengguna.
   - Pekerjaan latar belakang (background workers) **WAJIB** diimplementasikan menggunakan fungsi _async_ dan dieksekusi melalui `page.run_task(nama_fungsi)`.
   - Untuk melakukan pemblokiran I/O dari inti program di dalam task async, gunakan `await asyncio.to_thread(fungsi_blocking, *args, **kwargs)`.
3. **Cancellation Handling**:
   - Fitur pembatalan (_Abort/Cancel Job_) harus didukung. Worker task harus secara berkala mengecek flag pembatalan (`is_cancelled`) untuk menghentikan proses subprocess FFmpeg/yt-dlp secara aman tanpa meninggalkan file sampah (_leftover temp files_).
4. **Pembersihan Temporary File**:
   - Semua file mentah temporer (`*_raw.mkv`, `*.ass`, `*_nosub.mp4`) wajib dibersihkan secara otomatis jika proses selesai atau terjadi kegagalan/pembatalan.

---

## 📂 4. ATURAN PENGELOLAAN DEPENDENSI & STANDALONE BUNDLING

1. **Kompatibilitas Standalone Executive**:
   - Seluruh impor dependensi harus kompatibel dengan `flet build` / PyInstaller / Nuitka.
   - Deteksi lokasi executable FFmpeg harus mendukung pencarian di PATH sistem, direktori aplikasi internal (`bin/ffmpeg`), serta installer OS lokal.
   - **Seluruh kode production harus berjalan dengan benar dalam kondisi `frozen`** — artinya tidak boleh bergantung pada interpreter Python eksternal (lihat Larangan 1.4).
2. **Manajemen Model Whisper**:
   - Pengunduhan model Faster-Whisper harus didukung secara terisolasi. Jika model belum ada di cache, tampilkan indikator unduhan di GUI sebelum proses clipping dimulai.
3. **Struktur Pembatalan Paket Web**:
   - Modul Flask (`webapp.py`, `templates/`, `static/`) yang sudah tidak dipakai harus diisolasi atau dihapus secara aman setelah GUI Desktop murni berbasis Flet selesai diimplementasikan.
4. **Manajemen Pustaka (Dependency Management) yang Ketat dengan `uv`**:
   - DILARANG mengedit `requirements.txt` secara manual atau menggunakan alat lama seperti `scripts/manage_reqs.py` / `pip-tools`.
   - AI Model dan Pengembang WAJIB menggunakan **`uv`** (Astral) untuk segala aktivitas manajemen dependensi karena proyek ini sudah bermigrasi ke `uv`.
     - **Penambahan Paket**: Gunakan perintah `uv add "nama-paket"` untuk menambah dependensi.
     - **Penghapusan Paket**: Gunakan perintah `uv remove "nama-paket"`.
     - **Sinkronisasi**: Gunakan perintah `uv sync` untuk menyelaraskan _virtual environment_ dengan `uv.lock` (memastikan dependensi yatim terhapus).
     - **Ekspor (Opsional)**: Jika membutuhkan `requirements.txt` untuk kompatibilitas build lama, gunakan `uv export --format requirements-txt > requirements.txt`.

---

## 📋 5. ATURAN LOGGING & DIAGNOSIS ERROR

1. **Silent Log Inspection & Professional Reporting**:
   - Gunakan logger terpusat di `core/logger.py`. Log output dari subprocess FFmpeg and yt-dlp harus dialirkan secara _real-time_ ke file log lokal (`logs/cliptzy.log`) dan ke widget log viewer di GUI Flet.
   - Semua modul yang memakai yt-dlp **wajib** meneruskan log ke `LogViewer` GUI melalui `event_bus` / `EventBusLogHandler`. Dilarang membungkam output dengan `quiet: True`.
2. **Investigasi Error Berbasis Log Empiris**:
   - Jika terjadi _runtime error_ atau _crash_, AI Model harus mengekstrak log lengkap sebelum mendiagnosis penyebab utama. Dilarang menebak-nebak tanpa melihat _stack trace_.
3. **Verifikasi Frozen Build**:
   - Setiap perubahan yang menyentuh subprocess / path / dependensi runtime **wajib** diuji dalam kondisi `frozen` (build + jalankan executable), bukan hanya di mode development.
4. **Dilarang Keras Menggunakan `event_hook("log", ...)` Secara Langsung**:
   - Dilarang mengirim log teks menggunakan `event_hook("log", ...)` karena akan menyebabkan pencetakan duplikat (double-logging) di antarmuka `LogViewer` dan tidak memiliki format tingkatan (_leveling_).
   - **Solusi**: SELALU gunakan pustaka standar `from core.logger import log` (contoh: `log.info(...)`, `log.error(...)`). Semua pemanggilan metode pada `core.logger` secara otomatis sudah terhubung dan diteruskan ke UI `LogViewer` melalui `EventBusLogHandler`.

---

## 🛡️ 6. ATURAN TYPE CHECKING & PYLANCE (FLET MIGRATION)

1. **Resolusi Strict Typing Flet Event Handlers**:
   - Dilarang memberikan anotasi spesifik `(e: ft.ControlEvent)` pada fungsi _event handler_ jika memicu error _contravariance_ dari Pylance (seperti _"is not assignable to type Event[Button]"_). Gunakan parameter `(e)` tanpa anotasi untuk menghindari bentrok tipe generik.
2. **Pengecualian Properti Dinamis Flet (Type Ignore)**:
   - Flet mendefinisikan event parameter dengan _base class_ (seperti `_BaseControlType`) yang secara bawaan tidak menyimpan metadata properti spesifik subclass (contoh: `.value`, `.selected_index`). Gunakan komentar `# type: ignore` secara selektif saat mengakses properti turunan tersebut agar Pylance tidak menganggapnya sebagai error.
3. **Casting Koleksi List**:
   - Saat mendeklarasikan list yang berisi berbagai macam subclass Flet (contoh campuran `ft.IconButton`, `ft.Text`, `ft.Slider`), Anda **WAJIB** membungkusnya menggunakan `typing.cast(list[ft.Control], [...])`. Hal ini mencegah Pylance mengunci inferensi tipe ke spesifik _union_ subclass yang membuat list tersebut _invariant_ (ditolak saat dilempar ke parameter `controls=`).

---

## 🧪 7. ATURAN VERIFIKASI SEBELUM MENYATAKAN SELESAI

Setiap pekerjaan refactoring atau penambahan fitur dianggap **SELESAI** hanya apabila AI Model telah memenuhi kriteria berikut:

- [ ] **WAJIB** menjalankan `make typecheck` (static type check) dengan **0 errors** sebelum menyatakan selesai. Pastikan hasil akhirnya `0 errors`.
- [ ] Kode terkompilasi / berjalan tanpa syntax error atau missing import error (`python -m py_compile`).
- [ ] Fitur GUI dapat diluncurkan dan diuji secara empiris (menjalankan tes atau script verifikasi).
- [ ] Operasi pemrosesan klip menghasilkan file output `.mp4` yang valid di direktori tujuan.
- [ ] Log menunjukkan tidak ada error fatal yang disembunyikan.
- [ ] Tidak ada penggunaan `sys.executable` untuk subprocess Python/pip di kode production (`core/` dan `gui/`).
- [ ] Tidak ada path absolut lokal yang di-hardcode.
- [ ] Dokumentasi (`ARCHITECTURE.md`, `README*.md`, `CHANGELOG.md`) sinkron dengan perubahan kode.
- [ ] Tidak ada dependensi baru yang ditambahkan tanpa melalui mekanisme `uv add`.

---

## 📌 8. DAFTAR KESALAHAN YANG PERNAH TERJADI (JANGAN DIULANGI)

Daftar ini adalah _lesson learned_ dari riwayat proyek. AI Model **WAJIB** membaca dan menghindari pola-pola berikut:

1. **`sys.executable -m edge_tts` di `core/processing/stacker.py`** → menyebabkan _frozen executable_ memanggil dirinya sendiri dan _crash_. Solusi: gunakan `edge_tts.Communicate` (Python API) langsung. ✅ Sudah diperbaiki di v3.0.1 — **jangan regresi**.
2. **`pip install` via `sys.executable` di `core/utils.py`** → gagal saat frozen. Solusi: guard dengan `getattr(sys, 'frozen', False)` dan lewati saat frozen. ✅ Sudah diperbaiki — **jangan regresi**.
3. **Subprocess `sys.executable -m piptools` / `pip` di script build lama (`scripts/manage_reqs.py`)** → **SAH** karena ini dulunya alat build-time developer, **bukan** kode production. Jangan menyalin pola ini ke `core/` atau `gui/`.
4. **Dokumentasi tidak sinkron** (ARCHITECTURE.md / README masih menyebut PyQt6 & QThread saat kode sudah Flet) → menyesatkan AI model berikutnya. **Wajib** perbarui dokumentasi setiap kali arsitektur berubah.
5. **Error Command Line Too Long di Windows & FFmpeg AST Node Limit** → Sebagian besar FFmpeg binaries tidak mendukung flag `-filter_complex_script` secara universal. Selain itu, fungsi `eval.c` pada FFmpeg memiliki batasan kedalaman AST (Abstract Syntax Tree) maksimal sekitar 95 node (terms). Walaupun sudah menggunakan struktur jumlahan datar (*flat sum*) `(expr1)*lt(t, a) + (expr2)*gte(t, a)*lt(t, b) + ...`, jika jumlah *terms* lebih dari 95, FFmpeg akan *crash* dengan error `Invalid argument` (Failed to configure input pad). Solusi mutlaknya adalah membatasi maksimal titik dinamis (`MAX_KEYFRAMES = 85`) dan melakukan simplifikasi iteratif berdasarkan toleransi jarak pergerakan, lalu membuang titik-titik minor. File `.vf` tetap dibuat secara permanen hanya untuk tujuan debugging dan logging.
---

## 🎭 9. ATURAN PENGELOLAAN VIDEO EFFECTS (MENGGANTIKAN SFX & VFX)

Sistem efek suara (SFX), efek visual (VFX), dan overlay yang lama telah **dihapus dan digantikan sepenuhnya** oleh sistem `video_effect` yang terintegrasi (melalui `VideoEffectManager` di `core/video_effects.py`).

1. **Sentralisasi Melalui Manager (`core/video_effects.py`)**:
   - Dilarang keras melakukan _hardcode_ pencocokan emosi (seperti `if emo == "sad": ...`) langsung di dalam `core/processing/subtitle.py` atau tempat lain.
   - Penambahan, pengurangan, atau pengubahan emosi beserta aset videonya **WAJIB** dilakukan melalui mapping pada `VideoEffectManager`.
   - Setiap emosi harus memiliki setidaknya 5 variasi aset video untuk menghindari repetisi.
2. **Aturan Audio untuk Video Effects**:
   - Semua efek video secara default **wajib** memiliki `audio_filter` yang mengatur volume agar selalu lebih rendah dari audio utama (misalnya `volume=0.2`).
   - Efek video **wajib** memiliki konfigurasi _audio fade out_ (menggunakan `afade=t=out:st=...:d=...`) agar transisinya mulus dan tidak terpotong tiba-tiba di akhir efek.
3. **Kesesuaian Filter FFmpeg (Timeline Support)**:
   - Hindari filter tambahan yang menyebabkan _crash_. Jika menambahkan efek visual dinamis, pastikan opsi filter FFmpeg mendukung evaluasi timeline/waktu (`enable='between(...)'`).
4. **Skema Pengujian (Testing Scheme)**:
   - **Verifikasi Substring Emosi**: Ujicoba logika `map_emotion` menggunakan script Python singkat untuk memastikan string respon AI (meski kotor/bercampur kata lain) dapat dipetakan dengan tepat ke _key_ di manager.
   - **Verifikasi Keutuhan Render FFmpeg (Kritis)**: Lakukan uji coba rendering untuk melihat apakah command string FFmpeg gagal terbentuk atau ditolak oleh _binary_ FFmpeg (contoh: error sintaks filter, argumen tidak dikenali, atau _timeline not supported_). Pastikan log tidak memunculkan "FFmpeg subtitle/video effect filter failed".

---

## 🎨 10. ATURAN MIGRASI FLET 0.23+ (PENTING)

1. **Penggunaan Warna (Colors)**:
   - Dilarang keras menggunakan `ft.colors.<WARNA>` (huruf kecil). Flet telah memperbarui API-nya, gunakan **`ft.Colors.<WARNA>`** (kapital C) atau enum yang sesuai.
2. **Penggunaan Ikon (Icons)**:
   - Dilarang keras menggunakan string referensi lama seperti `ft.icons.MOVIE_EDIT`. Gunakan enum resmi **`ft.Icons.<IKON>`** (misal: `ft.Icons.MOVIE`, `ft.Icons.TUNE`, `ft.Icons.PUBLISH`).
3. **Struktur Komponen Tabs**:
   - Komponen `ft.Tabs` tidak lagi menerima list dari `ft.Tab` secara langsung sebagai parameter `tabs`.
   - Anda **WAJIB** menggunakan struktur `Tabs(length=..., content=ft.Column([ft.TabBar(tabs=[...]), ft.TabBarView(controls=[...])]))`.
   - Parameter judul untuk `ft.Tab` sekarang menggunakan argumen `label=`, bukan `text=`.
4. **Penggunaan Border dan Margin (PENTING)**:
   - Dilarang menggunakan metode fungsi usang seperti `ft.border.all()` (huruf kecil) atau `ft.margin.symmetric()`.
   - Gunakan selalu class/metode dengan **huruf kapital** dan konstruktor yang tepat: **`ft.Border.all(...)`** dan **`ft.Margin(...)`**.
5. **Penghapusan Variabel Warna Usang (Error `__getattr__`)**:
   - Beberapa properti warna (seperti `ft.Colors.SURFACE_VARIANT`) telah dihapus/direstrukturisasi pada Enum `ft.Colors` di versi Flet terbaru.
   - Jika terjadi `AttributeError: 'super' object has no attribute '__getattr__'` saat menggunakan warna tertentu, segera ganti dengan palet yang lebih aman/didukung (contoh: `ft.Colors.BLUE_GREY_900` atau `ft.Colors.SURFACE`).
6. **Konsistensi Gaya Container (Styling)**:
   - Komponen `ft.Container` di dalam UI diutamakan menggunakan garis tepi (_border_) alih-alih warna latar belakang (`bgcolor`) untuk menjaga konsistensi desain yang bersih (clean design).
   - Gunakan atribut: `border_radius=8` dan `border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)`. Jangan menetapkan `bgcolor` kecuali diperlukan secara khusus untuk menyorot (_highlight_) bagian tertentu.
---

_Peraturan dalam AGENTS.md ini mengikat untuk semua aktivitas pengembangan proyek Cliptzy. Pelanggaran terhadap Larangan 1.4 (`sys.executable`) dianggap **bug kritis** dan mengharuskan perbaikan segera._

7. **Perubahan Parameter Dropdown**: Dilarang keras menggunakan keyword on_change pada komponen ft.Dropdown. Flet terbaru menggunakan keyword on_select sebagai parameter event.
