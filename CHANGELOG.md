# Changelog

Semua catatan pembaruan dari proyek Cliptzy akan didokumentasikan di dalam file ini.

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
