# Changelog

Semua catatan pembaruan dari proyek Cliptzy akan didokumentasikan di dalam file ini.

## [v3.0.6] - 2026-08-05

### Changed

- **Menyembunyikan Terminal Window di Windows:** Menyisipkan _monkey-patch_ pada `subprocess.Popen` di `main.py` sehingga semua proses latar belakang bawaan FFmpeg, ffprobe, dan yt-dlp tidak lagi memunculkan _jendela terminal (CMD)_ tambahan saat aplikasi beroperasi dalam versi _standalone GUI executable_.

### Fixed

- **Filter Watermark FFmpeg:** Memperbaiki galat (`Undefined constant or missing '(' in 'W*0.8)'`) pada algoritma filter `scale` saat memproses penambahan _watermark_ gambar. Variabel `W` telah diganti dengan referensi nilai konkrit `{out_w}` agar kalkulasi batas maksimal lebar 80% aman diproses oleh _FFmpeg filtergraph_ di `core/processing/stacker.py`.

## [v3.0.3] - 2026-08-04

### Added

- **Efek Video & Audio Dinamis Berbasis Emosi AI:** Menambahkan logika FFmpeg _filtergraph_ tingkat lanjut (`geq`, `vignette`, `hue`, `vibrato`, `flanger`) di `core/processing/subtitle.py`. Fitur ini otomatis memberikan efek visual dan audio pada video sesuai transkrip emosi (contoh: Hitam Putih + Suara Redam saat 'sedih', Layar Bergetar + _Bass Boost_ saat 'kaget', dan _Zoom Out_ + _Alien Voice_ saat 'heran') tanpa mengacaukan sinkronisasi _framerate_ menggunakan dukungan parameter _timeline_ FFmpeg (`enable='between(t,start,end)'`).
- **Fallback Ekstraksi Frame FFmpeg:** Mengatasi bug OpenCV (`cv2.VideoCapture`) yang sering gagal membaca file kontainer `.mkv` (AV1/VP9) hasil `yt-dlp`. Sistem `face_tracker.py` sekarang secara otomatis mengalihkan tugas (_fallback_) penyedotan _frame_ ke _subprocess_ FFmpeg asli, menjamin _full_face tracking_ tidak akan pernah gagal karena isu _codec_.
- **Latar Belakang Blur pada `full_face`:** Mode _crop_ `full_face` sekarang tidak lagi menggunakan latar belakang warna hitam statis. Fitur ini di-_upgrade_ menggunakan manipulasi `boxblur=20:20` berlapis sehingga menghasilkan estetika _background_ video buram yang identik dengan mode `full`.

### Changed

- **UI Pengaturan Subtitle:** Memperbarui antarmuka pengguna pada Clipper. Label opsi animasi kini berubah menjadi "Timbul (Scale Up) Per Kata" untuk memperjelas fungsinya, serta memindahkan _input_ **Ukuran Font** agar bersebelahan langsung dengan **Subtitle Delay (ms)**.
- **Warna Teks Netral:** Memperbarui _prompt_ kecerdasan buatan (`core/ai/detector.py`) untuk memaksakan pemakaian warna Kuning (`#FFFF00`) sebagai pewarnaan _default_ (netral) transkrip kata.
- **Sensitivitas Pelacakan Wajah:** Menurunkan _threshold_ skor keandalan model AI YuNet dari `0.8` menjadi `0.6` pada `face_tracker.py` untuk meningkatkan sensitivitas terhadap wajah manusia yang agak buram.
- **Pesan Log Pendeteksi Wajah:** Meningkatkan kualitas laporan diagnosis pada _log viewer_ untuk menyertakan alasan kegagalan spesifik jika wajah gagal dideteksi secara teknis maupun karena tidak ada wajah sama sekali.

### Fixed

- **Audio Sync pada FFmpeg Concat:** Memperbaiki sistem penggabungan (_concat_) di `core/processing/stacker.py` yang sebelumnya menyebabkan eror _matches no streams_ atau ketidaksinkronan karena _hack_ `anullsrc`. Skrip kini secara cerdas mengabaikan klip Intro/Outro yang tidak memiliki aliran _audio_ (_audio stream_) dari daftar proses penggabungan.

## [v3.0.2] - 2026-08-03

### Fixed

- **Outro:** Memperbaiki state tombol Set Video Outro pada Clipper

## [v3.0.1] - 2026-08-03

### Added

- **Modul Logger yt-dlp Terpusat (`core/yt_dlp_logger.py`):** Menambahkan adapter logger terpusat baru yang menjembatani antarmuka logger kustom yt-dlp dengan sistem logging standar Python (`core/logger.py`). Dibangun mengikuti prinsip SOLID (_Single Responsibility_, _Open/Closed_, _Dependency Inversion_). Modul ini menyediakan `YtDlpLoggerAdapter`, `create_yt_dlp_logger()`, dan `create_yt_dlp_progress_hook()` yang dapat digunakan oleh seluruh modul yang menggunakan yt-dlp.
- **Visibilitas Log yt-dlp di GUI:** Seluruh 5 modul yang menggunakan yt-dlp (`processor.py`, `youtube.py`, `channel_manager.py`, `detect_highlights.py`, `preview_clip.py`) kini meneruskan log ke `LogViewer` GUI secara otomatis melalui `EventBusLogHandler`. Sebelumnya, hanya `processor.py` yang menampilkan log parsial, sementara 4 modul lainnya membungkam output sepenuhnya (`quiet: True`).

### Changed

- **Pemanggilan `edge-tts` via API Langsung:** Menggantikan pemanggilan `edge-tts` melalui subprocess (`sys.executable -m edge_tts`) di `core/processing/stacker.py` dengan pemanggilan Python API langsung menggunakan `edge_tts.Communicate` dan `asyncio.run()`. Perubahan ini menghilangkan ketergantungan pada `sys.executable` yang menyebabkan _crash_ saat aplikasi dijalankan sebagai _frozen executable_.
- **Modularisasi `YtDlpLogger` dari `processor.py`:** Class `YtDlpLogger` dan fungsi `yt_dlp_progress_hook` yang sebelumnya didefinisikan secara lokal di dalam fungsi `process_single_clip()` kini dipindahkan ke modul terpusat `core/yt_dlp_logger.py`, sehingga dapat diakses dari seluruh bagian aplikasi.
- **Pembersihan Import:** Menghapus `import sys` yang tidak lagi digunakan dari `processor.py`, `stacker.py`, `youtube.py`, `channel_manager.py`, `detect_highlights.py`, dan `preview_clip.py`. Menghapus `import subprocess` yang tidak terpakai dari `detect_highlights.py` dan `preview_clip.py`.
- **Dokumentasi Arsitektur:** Memperbarui `ARCHITECTURE.md` dengan dokumentasi modul baru `yt_dlp_logger.py`.

### Fixed

- **Bug Kritis `sys.executable` di Production:** Memperbaiki pemanggilan `sys.executable -m edge_tts` di `core/processing/stacker.py` yang menyebabkan _frozen executable_ (`cliptzy.exe`) memanggil dirinya sendiri alih-alih interpreter Python, mengakibatkan _crash_ atau perilaku tak terduga saat aplikasi di-_bundle_.
- **Guard `is_frozen` untuk `pip install faster-whisper`:** Menambahkan pengecekan `is_frozen` pada blok instalasi `faster-whisper` di `core/utils.py` agar tidak mencoba menjalankan `pip install` saat aplikasi berjalan sebagai _standalone executable_, yang akan gagal karena `sys.executable` menunjuk ke biner aplikasi, bukan interpreter Python.

## [v2.0.7] - 2026-08-01

### Added

- **Penggabungan Klip (Merge Clips):** Menambahkan mode baru "Merge Video". Jika diaktifkan, setelah pemotongan selesai, seluruh klip akan digabungkan secara otomatis menjadi satu file `merged.mp4`.
- **Dukungan AI Metadata untuk Merged Video:** Fitur Auto Generate via AI kini mampu menangkap konteks keseluruhan dari gabungan semua klip pada file `merged.mp4` dan men-generate _metadata_ tunggal (Title, Deskripsi, Tags, Highlight) secara komprehensif.
- **Kustomisasi TTS Mutakhir:** Menggantikan pustaka lawas `gTTS` dengan `edge-tts` (Microsoft Edge Neural Voices) berkualitas tinggi. Menambahkan konfigurasi GUI untuk memilih **Bahasa TTS AI** (EN, ID, ES, JA, KO, MS) dan **Gender Suara** (Pria/Wanita).
- **Meme Voiceover (Loquendo Jorge):** Pemetaan spesifik untuk suara pria bahasa Spanyol (ES - Male) akan memanggil aktor suara meme legendaris `es-MX-JorgeNeural` ("numero uno").
- **Pemotongan via Padding Negatif:** Kolom konfigurasi "Padding Klip" kini mendukung angka negatif (hingga -30 detik) yang berfungsi merampingkan (memotong) durasi klip langsung dari awal dan akhir batas klip.

### Changed

- **Engine Face Detection:** Meng-upgrade algoritma pencarian wajah _(face tracking)_ dari HAAR cascades (`cv2.CascadeClassifier`) lama menjadi model _Deep Neural Network (DNN)_ OpenCV YuNet (`cv2.FaceDetectorYN`) dengan sistem _auto-download_ otomatis (tanpa eror aset eksternal yang hilang).
- **Penyesuaian Tempo TTS:** Memperlambat kecepatan pembacaan _voiceover_ TTS secara bawaan (`--rate=-15%`) agar terdengar lebih santai dan artikulatif.
- **Isolasi Lingkungan Python (`edge-tts`):** Memastikan proses pemanggilan `edge-tts` dieksekusi secara aman menggunakan rute Python aktif saat ini (`sys.executable -m edge_tts`) untuk mencegah _fallback_ ke versi lawas.

### Fixed

- Mengatasi _crash_ aplikatif (`TypeError`) saat proses indikator antarmuka (_GUI progress bar_) mencoba memperbarui persentase dari tugas berlabel `"merge"`.
- Memperbaiki peringatan linter/Pylance pada _overload type-checking_ di komponen `subprocess.run()`.
- Menyelesaikan _UnboundLocalError_ (`sys` diakses sebelum inisialisasi) akibat isu ruang lingkup _(scope)_ variabel Python selama pemanggilan modul _download_.

## [v2.0.3] - 2026-07-31

### Added

- **AI Highlight Text-to-Speech (TTS):** Menambahkan fitur baru berupa pembuatan otomatis video pembuka (Intro) yang berisi narasi suara (_text-to-speech_) menggunakan `gTTS` berdasarkan hasil deteksi sorotan AI. Video intro akan langsung digabungkan ke klip akhir secara otomatis.
- **Auto-Refresh Cookies:** Cookies untuk akun TikTok dan Instagram sekarang akan ditarik ulang secara otomatis setelah sesi _upload_ selesai, memastikan masa aktif cookie tetap _fresh_ dan tidak mudah kedaluwarsa.
- **Dependency Management Script:** Menambahkan perangkat manajemen dependensi canggih di `scripts/manage_reqs.py` (berbasis `pip-tools`) dan `requirements.in` demi memastikan _environment_ pengembangan selalu bersih tanpa sisa paket usang (_orphans_).

### Fixed

- **TikTok Asyncio Bug:** Memperbaiki permasalahan pengunggahan jamak ke TikTok (Playwright asyncio loop error) dengan menggunakan ulang satu instansi peramban (_reusable browser context_).
- **Instagram Moviepy Crash:** Mengeliminasi ketergantungan pada pustaka `moviepy` (yang menyebabkan error `VideoFileClip`) dalam alur _instagrapi_. Pembuatan _thumbnail_ klip kini ditangani 100% oleh `ffmpeg` murni.
- **Standalone Build Environment:** Memperbaiki sistem konfigurasi (_Supabase_) agar aplikasi versi kompilasi eksekutabel (_.exe/binary_) dapat diluncurkan mandiri secara instan tanpa membutuhkan ketersediaan berkas `.env` lokal lagi.

## [v2.0.1] - 2026-07-31

### Added

- **Instagram Reels Uploader:** Implementasi penuh fitur _auto-upload_ klip video ke Instagram Reels terintegrasi dengan _library_ `instagrapi`.
- **Import Cookies UI:** Menambahkan tombol antarmuka "Import Cookies" untuk Instagram pada halaman Auto Upload. Fitur ini menyederhanakan proses _login_ Instagram dan TikTok menggunakan file _cookies_ (berbasis format JSON atau Netscape TXT).

### Changed

- **Instagram Authentication:** Mengubah metode autentikasi Instagram dari penggunaan Graph API (Business ID & Access Token) ataupun _Username/Password_ mentah menjadi autentikasi aman berbasis _session cookie_ (`sessionid`). File sesi kini tersimpan secara otomatis di direktori `cred/`.
- Pembaruan _roadmap_ proyek (`TODO.md`) dengan menambahkan target implementasi fase selanjutnya untuk publikasi otomatis ke Facebook Pages.

## [v2.0.0] - 2026-07-29

### Added

- **Rilis Perdana (Initial Release):** Aplikasi Cliptzy Desktop Standalone versi perdana (migrasi dari versi Web / Flask).
- **Creator Hub:** Fitur untuk mencari, menambahkan, dan menjelajahi video YouTuber favorit. Pengambilan data profil dan _thumbnail_ sekarang dimuat secara dinamis menggunakan `yt-dlp` tanpa menahan _(freeze)_ antarmuka program.
- **YouTube Clipper:** Fitur utama untuk melakukan ekstraksi dan pemotongan klip dengan tiga mode cerdas:
  - **Heatmap:** Pemotongan otomatis dari titik yang paling banyak diputar ulang _(most replayed)_.
  - **Custom Range:** Pengaturan batas klip awal dan akhir secara manual oleh pengguna.
  - **AI Highlight Detector:** Deteksi klip sorotan terbaik _(highlights)_ dengan bantuan Transkripsi Whisper serta Analisa Bahasa dari AI (mendukung LLM lokal via Ollama, Google Gemini, dan OpenAI).
- **Auto Subtitle:** Sinkronisasi teks otomatis menggunakan _Faster-Whisper_ yang dirender _hardcode_ ke video melalui FFmpeg dengan kustomisasi posisi, penundaan _(delay)_, dan pemilihan bentuk tulisan _(font)_.
- **Settings Widget:** Pemusatan halaman pengaturan _(settings)_ khusus, memisahkan pengaturan berat seperti kredensial AI agar pengalaman UI jauh lebih bersih.
- **Otomatisasi Lintas Sistem Operasi:** Setup _Continuous Integration / Continuous Deployment (CI/CD)_ via GitHub Actions untuk kompilasi rilis Windows, Linux, dan macOS.

### Changed

- Perbaikan layout antarmuka (UI) sehingga seluruh card berjejer rapi dari sisi kiri-atas, _background_ diselaraskan, dan bebas tumpang-tindih (proporsional tanpa _stretching_).
- Menghapus semua _data hardcode_ pada katalog awal, memastikan program mengambil 100% data langsung dan aktual (segar) dari internet berdasarkan _input_ dari Anda.
