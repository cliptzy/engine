# Cliptzy Refactoring Plan

## 1. GUI Modifications (Clipper View to Tabbed View)

- [x] Refactor `gui/views/clipper_view.py` to use `ft.Tabs` containing 2 main tabs: **Clipper** and **Publisher**.
- [x] Pindahkan komponen yang ada (seperti `VideoInput`, `Preview`, `ClipConfig`, `ProcessControl`) ke dalam tab **Clipper**.
- [x] Pindahkan komponen `UploadDistribution` dan tombol upload/render ke dalam tab **Publisher**.

## 2. Core Processing Pipeline Split (Phase 1 & Phase 2)

- [x] Modifikasi `core/controller.py` dan pipeline proses.
- [x] **Phase 1 (Data Extraction & AI Analysis)**: Download raw video, cropping dinamis, deteksi DeepFace (emosi visual), transkripsi Whisper (audio), dan analisa LLM (metadata & emosi teks). Semua data disimpan ke dalam JSON (`metadata.json` / `emotion.json`).
- [x] **Phase 2 (Rendering)**: Parse updated metadata, create ASS, dan burn subtitle beserta video/audio filter secara otomatis menggunakan `VideoEffectManager` di `core/video_effects.py`.

## 3. Publisher Tab Implementation

- [x] Buat antarmuka untuk me-load project untuk upload otomatis.
- [x] Integrasi auto-upload ke platform (TikTok/YouTube dll) setelah video sukses di-render.
- [x] Integrasikan `FletProgressReporter` untuk melaporkan proses _rendering_ dan _upload_ dengan baik ke UI.

## 4. Verification & Testing

- [x] Pastikan tidak ada GUI blocking (menggunakan `page.run_task` & `asyncio.to_thread`).
- [x] Lakukan pengujian proses render FFmpeg dengan efek visual menggunakan `core/video_effects.py`.
- [x] Jalankan `npx --yes pyright --pythonpath .venv/bin/python .` untuk memastikan 0 errors.
- [ ] Pengujian menyeluruh pada executable (_frozen_) build untuk mencegah regresi (_seperti isu sys.executable_).

## 5. TikTok Retention Optimization (Views Booster Roadmap)

- [x] **Split-Screen / "Brain Rot" B-Roll (Visual Stimulus)**
  - **B-Roll Sourcing Strategy**:
    - _Opsi 1 (API)_: Integrasi Pexels API (gratis) untuk query video _satisfying_ (keyword: "abstract", "kinetic sand", "soap cutting"). Kelemahan: Jarang ada video _gameplay_ (seperti GTA V/Subway Surfers).
    - _Opsi 2 (Non-API / Rekomendasi)_: Buat utilitas `scripts/download_broll.py` menggunakan `yt-dlp` untuk mengunduh video "No Copyright Gameplay" dari YouTube (berdurasi panjang), menyimpannya di `assets/broll/`. Saat render, `Cliptzy` akan memilih _start time_ secara acak dari kumpulan video ini.
  - **FFmpeg Integration**: Gunakan filter `vstack` untuk menumpuk _face-cam podcast_ di setengah layar atas (rasio 1:1) dan _b-roll gameplay_ di layar bawah (rasio 1:1) sehingga menghasilkan format TikTok (9:16).
- [x] **Dynamic Subtitles (Hormozi Style)**
  - Unduh dan letakkan _font_ modern tebal (seperti TheBoldFont atau Montserrat-Black) ke dalam folder `fonts/`.
  - Refactor `core/processing/subtitle.py` untuk menginjeksi tag gaya `.ass` (seperti `{\c&H00FFFF&}` untuk pergantian warna atau `{\k}` untuk efek karaoke) berdasarkan _word-level timestamps_ dari Faster-Whisper.
  - Tambahkan _outline_ tebal dan efek pop-in pada sub-teks.
- [ ] **Trending Background Music (BGM)**
  - Siapkan _directory_ `assets/bgm/` untuk musik _viral/phonk/lo-fi_.
  - Modifikasi FFmpeg _builder_ untuk menggabungkan suara _podcast_ dengan BGM (volume rendah, misal 10% - 15%) menggunakan filter audio `amix`.
- [ ] **Silence Removal (Pacing & Jump Cuts)**
  - Lakukan iterasi pada data _word timestamps_ Whisper untuk mencari jeda (silence) > 0.4 detik.
  - Gunakan filter pemotongan _timeline_ (seperti `select` filter, tetapi perhatikan batas AST Node 95 sesuai aturan `AGENTS.md`) untuk memotong bagian yang sepi sehingga klip terasa _fast-paced_.
- [ ] **Video Hook (3-Detik Awal)**
  - Modifikasi _prompt_ LLM di fase ekstraksi untuk mencari kalimat paling kontroversial, mengejutkan, atau mengundang rasa penasaran sebagai penentu _clip segment_ awal.
