# Cliptzy — Rencana Implementasi Fitur Kompilasi Video (Top N Meme)

## Deskripsi Fitur

Mode kompilasi memungkinkan user memasukkan **beberapa file video lokal** beserta **nama momen** untuk setiap file. Cliptzy akan memproses masing-masing klip dan menggabungkannya menjadi **satu video kompilasi "Top N"** lengkap dengan numbering card, TTS narasi, dan subtitle otomatis.

**Contoh Input:**
| # | File Video | Nama Momen |
|---|---|---|
| 5 | `clip_a.mp4` | Momen Paling Biasa |
| 4 | `clip_b.mp4` | Momen Cringe Abis |
| 3 | `clip_c.mp4` | Momen Plot Twist |
| 2 | `clip_d.mp4` | Momen Kocak Parah |
| 1 | `clip_e.mp4` | Momen Paling Epic |

**Output:** Satu file `compilation.mp4` berisi: `[Intro?] → [Card "NOMOR 5" + TTS] → [Clip 5 + Subtitle] → [Card "NOMOR 4" + TTS] → [Clip 4 + Subtitle] → ... → [Card "NOMOR 1" + TTS] → [Clip 1 + Subtitle] → [Outro?]`

---

## Phase 1: Core Engine — Numbering Card & Compilation Pipeline

- [x] **Buat `core/processing/numbering.py`** — Generator numbering card
  - Fungsi `generate_numbering_card(number, moment_name, output_path, duration, ...)`:
    - Membuat video pendek (2-3 detik) dengan background hitam/gradien
    - Teks besar: "NOMOR {N}" + nama momen di bawahnya
    - TTS narasi via `core/processing/tts_engine.py`: "Nomor {n}! {nama momen}!"
    - Output: file `.mp4` (resolusi sesuai `config.out_width` × `config.out_height`)
  - Mengadaptasi pola dari `generate_intro()` di `core/processing/stacker.py`
  - Subtitle ASS untuk teks yang muncul di layar (pop-in animation opsional)

- [x] **Tambah `CompilationConfig` di `core/config.py`**
  - Field: `ordering` (countdown/countup), `numbering_duration`, `use_tts`, `tts_template`, `use_subtitle`, `crop_mode`
  - Serialisasi ke/dari `config.json`

- [x] **Buat `core/use_cases/compile_video.py`** — Use Case utama
  - Kelas `CompileVideoUseCase`:
    - Menerima `List[CompilationItem]` (file_path, moment_name, number)
    - Untuk setiap item: crop video lokal via `process_single_clip()` (yang sudah ada, dengan `source_url=file_path`)
    - Generate numbering card via `generate_numbering_card()`
    - Concat semua segmen menggunakan FFmpeg concat demuxer: `card_N.mp4 + clip_N.mp4 + card_N-1.mp4 + ...`
    - Prepend intro (opsional) + append outro (opsional)
    - Output: `compilation.mp4` di `clips/compilation_<timestamp>/`
  - Processing paralel per klip (reuse `ThreadPoolExecutor` pattern dari `clip_video.py`)
  - Progress reporting via `event_hook` ke GUI
  - Cancellation support (`is_cancelled` flag)

- [x] **Tambah `execute_compilation()` di `core/controller.py`**
  - Method baru pada `ClipController` yang mendelegasikan ke `CompileVideoUseCase`

- [x] **Verifikasi**: Jalankan `make typecheck` — harus 0 errors (3 error pre-existing di `scripts/poc_maya1.py`, bukan kode production)

---

## Phase 2: GUI — Compilation View

- [x] **Buat `gui/views/compilation_view.py`** — Halaman UI kompilasi
  - Layout utama:
    - Tombol "Tambah Video" → `FilePicker` async (multi-select)
    - List item berisi: nomor urut, nama file, input teks "Nama Momen", tombol hapus
    - Drag & drop reorder (atau tombol ↑↓) untuk mengubah urutan
    - Dropdown: ordering style (Countdown 5→1 / Countup 1→5)
    - Toggle: TTS narasi on/off, Subtitle on/off
    - Dropdown: crop mode (reuse pilihan dari ClipperView)
    - Tombol utama: "Generate Compilation"
  - Desain mengikuti aturan AGENTS.md §11 (Modern Design Guidelines):
    - Glassmorphism, gradien CTA, shadow elevation, micro-interactions
    - Spacing kelipatan 8, tipografi hirarki jelas

- [x] **Integrasi routing di `gui/router.py`**
  - Tambah route `"compilation"` → `CompilationView`

- [x] **Tambah menu item di sidebar/navigation**
  - Ikon `ft.Icons.VIDEO_LIBRARY` atau `ft.Icons.COLLECTIONS`
  - Label: "Compilation" / "Kompilasi"

- [x] **Register di `gui/views/__init__.py`**

- [x] **Integrasi `BackgroundWorker`**
  - Proses kompilasi dijalankan via `page.run_task()` + `asyncio.to_thread()`
  - Progress bar + log viewer real-time
  - Tombol Cancel/Abort

- [x] **Verifikasi**: Jalankan `make typecheck` — harus 0 errors

---

## Phase 3: Polish & Enhancement

- [x] **AI generate metadata kompilasi**
  - Kirim semua nama momen ke LLM → generate judul viral ("TOP 5 Momen Paling Absurd!"), deskripsi, dan hashtag

- [x] **Thumbnail kompilasi otomatis**
  - Collage/grid dari frame terbaik tiap klip via `core/processing/thumbnail.py`

- [x] **Save/load preset kompilasi**
  - Export list item (file paths + nama momen) ke JSON untuk dipakai ulang

- [x] **Verifikasi akhir**: Jalankan `make typecheck` — harus 0 errors

---

## Catatan Teknis

- **WAJIB** mematuhi seluruh aturan di `AGENTS.md` (terutama: tidak ada `sys.executable` subprocess, tidak ada hardcode path, semua I/O berat di thread terpisah)
- Numbering card generator menggunakan FFmpeg (background hitam + ASS subtitle) + TTS engine yang sudah ada — **bukan** library baru
- Concat menggunakan FFmpeg concat demuxer (`-f concat -safe 0`) — pendekatan paling aman tanpa risiko AST node limit
- Setiap perubahan arsitektur harus disinkronkan ke `ARCHITECTURE.md`
