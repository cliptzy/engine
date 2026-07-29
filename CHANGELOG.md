# Changelog

Semua catatan pembaruan dari proyek Cliptzy akan didokumentasikan di dalam file ini.

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
