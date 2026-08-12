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
- [x] Integrasikan `FletProgressReporter` untuk melaporkan proses *rendering* dan *upload* dengan baik ke UI.

## 4. Verification & Testing
- [x] Pastikan tidak ada GUI blocking (menggunakan `page.run_task` & `asyncio.to_thread`).
- [x] Lakukan pengujian proses render FFmpeg dengan efek visual menggunakan `core/video_effects.py`.
- [x] Jalankan `npx --yes pyright --pythonpath .venv/bin/python .` untuk memastikan 0 errors.
- [ ] Pengujian menyeluruh pada executable (_frozen_) build untuk mencegah regresi (_seperti isu sys.executable_).
