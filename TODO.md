# 🚀 TODO: Roadmap Pengembangan Cliptzy & Fitur Anti-Reused Content

Dokumen ini berisi **roadmap lengkap** pasca-migrasi GUI framework dari **PyQt6** ke **[Flet](https://flet.dev)**, status penyelesaian tugas, serta penambahan rencana implementasi fitur **Transformative Content (Anti-Reused Content YouTube)** agar klip video yang dihasilkan memenuhi kriteria monetisasi YouTube secara otomatis.

---

## 📋 Daftar Isi

1. [Status Migrasi Flet & Refactoring Arsitektur](#-status-migrasi-flet--refactoring-arsitektur)
2. [Fase 0 sampai 7 — Progres Migrasi & Refactoring](#-fase-0-sampai-7--progres-migrasi--refactoring)
3. [Fase 8 — Fitur Transformative Content (Anti-Reused Content) [NEW]](#-fase-8--fitur-transformative-content-anti-reused-content-new)
4. [Appendix A — Panduan Penerapan FFmpeg Filters](#-appendix-a--panduan-penerapan-ffmpeg-filters)
5. [Appendix B — Standar Pengembangan & AGENTS.md](#-appendix-b--standar-pengembangan--agentsmd)

---

## 📊 Status Migrasi Flet & Refactoring Arsitektur

Migrasi framework UI dari **PyQt6** ke **Flet** dan refactoring engine menjadi _Three-Tier Architecture_ (GUI-Agnostic) hampir sepenuhnya selesai. Berikut adalah status ringkasnya:

- **Engine Core Layer (`core/`)**: 100% GUI-Agnostic. Semua interaksi UI menggunakan callback/interfaces yang didefinisikan di `core/interfaces.py`.
- **UI Layer (`gui/`)**: Flet application fully bootstrapped dengan Router, State Management (AppState), dan asinkron task runner (`page.run_task`).
- **Dependencies**: Menggunakan `flet-video` untuk player preview, `pystray` untuk tray, dan `desktop-notifier` untuk notifikasi OS.

---

## 🛠️ Fase 0 sampai 7 — Progres Migrasi & Refactoring

### Fase 0 — Persiapan & Riset ✅ SELESAI

- [x] Audit kompatibilitas dependensi dengan Flet.
- [x] Verifikasi player video local dengan `flet-video`.
- [x] Riset komponen pengganti PyQt6 (SpinBox custom, Tray via `pystray`).
- [x] Konfigurasi environment baru dan branch git.

### Fase 1 — Refactoring Arsitektur Core ✅ SELESAI

- [x] Pembuatan `core/interfaces.py` untuk protocol layer.
- [x] Dependency injection pada `core/controller.py`.
- [x] Pemecahan modul `core/processor.py` (cropper, stacker, merger, intro_outro, tts).
- [x] Pemecahan `core/controller.py` menjadi use cases modular.
- [x] Pemecahan AI highlight detector dan Uploaders menggunakan Strategy Pattern.
- [x] Standarisasi type hints, data classes, custom exceptions, dan konfigurasi bertipe.

### Fase 2 — Scaffolding Flet & Infrastruktur Baru ✅ SELESAI

- [x] Struktur folder `gui/` baru (views, components, layout).
- [x] Event Bus thread-safe untuk logging/progress updates.
- [x] Observable State Management (`gui/state.py`).
- [x] Background Task Runner berbasis Flet Async (`page.run_task`).
- [x] Entry point aplikasi Flet (`gui/app.py`) dan update `run.py`.

### Fase 3 — Migrasi Komponen UI ✅ SELESAI

- [x] Sidebar layout (`NavigationRail`) & Custom App Bar.
- [x] Clipper View (URL input, crop configuration, controls).
- [x] Preview View dengan video player (`flet-video`).
- [x] Creator Hub View & Settings View.
- [x] Custom components (SpinBox, LogViewer, VideoCard).

### Fase 4 — Migrasi Fitur Lanjutan 🔄 DALAM PROSES

- [ ] Implementasi **Drag-and-Drop file OS** menggunakan `flet-dropzone` untuk import cookies dan aset intro/outro.
- [ ] Daemon system tray menggunakan `pystray`.
- [ ] Desktop notifications menggunakan `desktop-notifier`.

### Fase 5 — Styling, Theming & Polish UX ✅ SELESAI

- [x] Penerapan tema gelap Material Design di `gui/theme.py`.
- [x] Registrasi custom fonts.
- [x] Animasi switch view dan hover effects.

### Fase 6 — Testing, Packaging & CI/CD 🔄 DALAM PROSES

- [ ] Penambahan unit tests untuk use cases.
- [ ] Integrasi linter/type checker (`ruff`, `pyright`).
- [x] Konfigurasi `flet build` / PyInstaller untuk membungkus library berat (`faster-whisper`, `opencv`).
- [x] Update GitHub Actions workflow ke Flet.

### Fase 7 — Fitur Baru Pasca-Migrasi 🔄 DALAM PROSES

- [ ] Visual Crop Editor (Canvas interaktif untuk memosisikan facecam / screen crop).
- [ ] Custom Outro Generator.
- [ ] Batch processing queue untuk memotong banyak video sekaligus.

---

## 🚀 Fase 8 — Fitur Transformative Content (Anti-Reused Content)

> **Tujuan**: Mengintegrasikan fitur manipulasi video & audio tingkat lanjut ke dalam Cliptzy agar video klip yang dihasilkan tidak terdeteksi sebagai "Reused Content" oleh algoritma monetisasi YouTube, melainkan sebagai konten kreatif editorial baru dengan nilai tambah (transformative value).

### 8.1 — Manipulasi Visual yang Masif (Transformative Editing)

- [ ] **Dynamic Zoom & Panning (Ken Burns Effect) via FFmpeg**
  - Implementasikan fungsi `apply_dynamic_zoom` di `core/processing/cropper.py`.
  - Gunakan filter `zoompan` FFmpeg dengan ekspresi matematika berbasis waktu `t` untuk memperbesar area fokus (misalnya: zoom-in perlahan dari 1.0x ke 1.25x lalu kembali lagi, atau melakukan snap-zoom saat volume audio sangat tinggi).
  - Tautkan dengan event audio peak untuk mendeteksi momen dramatis secara otomatis.
- [ ] **Visual Overlays & Efek Dinamis**
  - **Screen Shake (Getaran Layar)**: Implementasikan filter getar menggunakan filter `crop` dinamis di FFmpeg dengan ekspresi koordinat acak/sinusoidal saat audio terdeteksi berisik (misal: streamer berteriak).
  - **Filter Warna Kontekstual**: Tambahkan opsi untuk mengubah filter video menjadi Hitam-Putih (grayscale) atau _sepia_ pada segmen tertentu (misalnya 2 detik setelah kekalahan dalam game) via filter `eq`/`hue`.
- [ ] **Transition Effects**
  - Gunakan filter `xfade` FFmpeg untuk menambahkan efek transisi (fade, wipe, slide) antar-potongan klip saat digabungkan.

### 8.2 — Rekayasa Audio & Efek Suara (Audio Engineering)

- [ ] **Vocal Isolation & Noise Reduction**
  - Integrasikan filter `afftdn` (FFT denoiser) atau `arnndn` (Recurrent Neural Network denoiser) pada modul pemrosesan audio untuk meredam background noise berisik dari streamer.
  - Tambahkan filter Equalizer (`equalizer`) untuk mendongkrak vokal/suara bicara agar terdengar lebih premium dan terisolasi dari suara game (Vocal Booster).
- [ ] **Integrasi Background Music (BGM)**
  - Tambahkan konfigurasi folder musik latar di `gui/views/settings_view.py`.
  - Implementasikan filter `amix` di `core/processing/merger.py` untuk mencampurkan BGM dengan audio asli video secara otomatis, dengan volume BGM yang di-set sangat pelan (misalnya -20dB) agar tidak menimpa suara streamer.
- [ ] **Auto Transition SFX**
  - Sediakan aset audio transisi bawaan (seperti efek _swoosh_ atau _boom_).
  - Masukkan SFX ini secara otomatis di setiap perpindahan segmen klip menggunakan filter `adelay` dan `amix`.

### 8.3 — Subtitle Interaktif Beranimasi (Hardcoded Captions)

- [ ] **Penerapan Dynamic Karaoke & Highlight Color**
  - Tulis ulang logika parser `.ass` di `core/subtitle.py` agar mendukung pembuatan subtitle "Active Word Highlight" menggunakan tag ASS karaoke (`{\k}` atau `{\kf}`).
  - Deteksi kata-kata kunci emosional (seperti kata umpatan, tanda seru, atau kata berhuruf kapital) dan otomatis ubah warnanya (misal: Kuning untuk penekanan, Merah untuk umpatan lucu).

### 8.4 — Custom Branding & Frame Overlays

- [ ] **Animated Watermark & Frame Overlay**
  - Tambahkan folder `assets/frames/` untuk menyimpan template bingkai vertikal (9:16 PNG frames).
  - Gunakan filter `overlay` FFmpeg untuk menempelkan bingkai kustom di atas video.
  - Tambahkan opsi penempelan logo watermark dengan opacity dinamis (transparansi) yang berpindah posisi secara berkala untuk menghindari sensor duplikasi visual YouTube.

---

## 📊 Appendix A — Panduan Penerapan FFmpeg Filters

Berikut adalah referensi sintaks filter FFmpeg yang dapat diimplementasikan dalam engine Python:

### 1. Dynamic Zoom (Slow Zoom In)

```bash
-vf "zoompan=z='min(zoom+0.0015,1.25)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
```

_Efek: Memperbesar video secara perlahan hingga 1.25x dengan titik pusat di tengah layar._

### 2. Screen Shake (Getaran Layar)

```bash
-vf "crop=w=iw-40:h=ih-40:x='in_w/2-w/2+15*sin(2*pi*t*12)':y='in_h/2-h/2+15*cos(2*pi*t*15)'"
```

_Efek: Mengurangi resolusi video sebesar 40px lalu menggetarkan posisi crop secara sinusoidal sepanjang sumbu X dan Y berdasarkan waktu `t`._

### 3. Audio Mixing (Background Music dengan Volume Terkontrol)

```bash
-filter_complex "[0:a]volume=1.0[main_a];[1:a]volume=0.15[bg_a];[main_a][bg_a]amix=inputs=2:duration=first[out_a]" -map 0:v -map "[out_a]"
```

_Efek: Menggabungkan audio utama (volume penuh) dengan audio BGM (volume diturunkan menjadi 15%), memotong audio gabungan agar sesuai durasi audio utama._

### 4. Color Grading (Sad/Loss Grayscale Moment)

```bash
-vf "hue=s=0"
```

_Efek: Mengubah video menjadi hitam-putih total (desaturate)._

---

## 🛡️ Appendix B — Standar Pengembangan & AGENTS.md

Seluruh implementasi di atas **wajib** mengikuti aturan ketat berikut:

1. **Tidak boleh menghalangi Main Thread Flet**: Semua render FFmpeg dan pemrosesan audio wajib dibungkus dalam `asyncio.to_thread` di dalam task asinkron.
2. **Tidak ada dummy code**: Modul `.ass` subtitle generator dan crop engine tidak boleh meniadakan error/menghasilkan dummy file jika terjadi kegagalan render.
3. **Pembersihan cache**: File temporary (seperti audio terpisah untuk isolasi vokal, file subtitle `.ass` sementara) harus dihapus secara otomatis dari storage jika proses render sukses maupun dibatalkan.
