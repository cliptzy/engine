# Cliptzy Refactoring Plan - 3 Stage Workflow (Clipper, Editor, Publisher)

## 1. GUI Modifications (Clipper View to Tabbed View)
- [x] Refactor `gui/views/clipper_view.py` to use `ft.Tabs` containing 3 main tabs: **Clipper**, **Editor**, and **Publisher**.
- [x] Pindahkan komponen yang ada (seperti `VideoInput`, `Preview`, `ClipConfig`, `ProcessControl`) ke dalam tab **Clipper**.
- [x] Buat layout baru untuk tab **Editor**.
- [x] Pindahkan atau modifikasi komponen `UploadDistribution` dan tombol render ke dalam tab **Publisher**.

## 2. Core Processing Pipeline Split (Phase 1 & Phase 2)
- [x] Modifikasi `core/controller.py` dan `core/use_cases/clip_video.py` untuk menghentikan proses *rendering* (FFmpeg burn) saat menekan tombol "Mulai Proses Clip" di tab Clipper.
- [x] **Phase 1 (Data Extraction & AI Analysis)**: Pipeline akan melakukan download raw/cut video, cropping dinamis, deteksi DeepFace (emosi visual), transkripsi Whisper (audio), dan analisa LLM (metadata & emosi teks). Semua data ini disimpan ke dalam JSON (`metadata.json` / `emotion.json`).
- [x] **Phase 2 (Rendering)**: Implement render engine to parse updated metadata, create ASS, and burn subtitle & visual filters.

## 3. Editor Tab Implementation
- [x] Load daftar project yang telah menyelesaikan *Phase 1* (membaca isi direktori `clips/` dan meload `metadata.json`).
- [x] Buat antarmuka (timeline / list view) untuk menampilkan *keyframes* (misal: detik 01.00 ke 02.00, emosi marah).
- [x] Sediakan dropdown / list pilihan bagi pengguna untuk menimpa atau memilih secara manual **VFX**, **SFX**, dan **Overlay** dari referensi file `sfx.json`, `vfx.json`, `overlay.json`.
- [x] Buat fungsi untuk menyimpan (*save*) konfigurasi baru pengguna kembali ke dalam file JSON project, sehingga menimpa hasil default AI jika diubah.

## 4. Publisher Tab Implementation
- [x] Buat antarmuka untuk me-load project yang sudah dikonfirmasi konfigurasinya dari tab Editor, untuk me-render dan melakukan upload.
- [x] Tambahkan tombol "Render Project" yang akan memanggil *Phase 2* (mengeksekusi render FFmpeg untuk menghasilkan final output `clip_X.mp4`).
- [x] Pertahankan form/tombol integrasi *auto-upload* ke platform (TikTok/YouTube dll) setelah video sukses di-render.
- [x] Integrasikan `FletProgressReporter` untuk melaporkan proses *rendering* dan *upload* dengan baik ke UI.

## 5. Verification & Testing
- [ ] Pastikan tidak ada GUI blocking (menggunakan `page.run_task` & `asyncio.to_thread`).
- [ ] Lakukan pengujian proses render FFmpeg dengan efek visual (VFX) pada *timeline* yang dimodifikasi melalui tab Editor.
- [ ] Jalankan `npx --yes pyright --pythonpath .venv/bin/python .` untuk memastikan 0 errors.
