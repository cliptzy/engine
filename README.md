# Cliptzy AI Engine 🧠

🇮🇩 **Bahasa Indonesia** | [🇺🇸 English](README_EN.md)

**FastAPI REST API Server** yang menyediakan layanan pemrosesan video AI untuk aplikasi desktop [Cliptzy](https://github.com/cliptzy/cliptzy) (Tauri). Engine ini menjalankan model-model AI berat (Faster-Whisper, DeepFace, Torch, Kokoro TTS) sebagai HTTP service lokal yang dikelola oleh Rust orchestrator.

---

## 🏗️ Arsitektur

Engine ini adalah **headless API server** yang:
- **Diluncurkan** oleh Rust (Tauri) sebagai child process.
- **Berkomunikasi** melalui REST API di `127.0.0.1:<port>`.
- **Tidak memiliki GUI** — semua UI ditangani oleh Tauri/Vue frontend.
- **Entry point**: `server.py` (FastAPI + Uvicorn).

```
Tauri App (Rust) ──HTTP──▶ FastAPI Server (Python)
     │                         │
     │ std::process::Command   │ core/ modules
     │                         │
     ▼                         ▼
  Manage lifecycle         Whisper, yt-dlp, FFmpeg,
  (start/stop/health)      DeepFace, Torch, TTS
```

---

## 🚀 Menjalankan Engine (Development)

### Prasyarat

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (package manager)
- FFmpeg terinstal dan tersedia di PATH

### Instalasi & Jalankan

```bash
# Install dependensi menggunakan uv
uv sync

# Jalankan API server
uv run python server.py --port 9721
```

Server akan berjalan di `http://127.0.0.1:9721`. Cek status:

```bash
curl http://127.0.0.1:9721/health
# {"status": "ok", "version": "4.0.0"}
```

---

## 📡 API Endpoints

### Health & System
| Method | Path | Deskripsi |
|--------|------|-----------|
| `GET` | `/health` | Health check dasar |
| `GET` | `/health/models` | Status model AI (Whisper, GPU, FFmpeg) |

### Clipper
| Method | Path | Deskripsi |
|--------|------|-----------|
| `POST` | `/clipper/analyze` | Analisis heatmap YouTube, return segmen |
| `POST` | `/clipper/process` | Proses single clip (crop, subtitle, effects) |
| `POST` | `/clipper/compile` | Kompilasi multi-clip (Top N) |
| `GET` | `/clipper/progress/{job_id}` | Status progress job |
| `POST` | `/clipper/cancel/{job_id}` | Batalkan job |

### Subtitle & AI
| Method | Path | Deskripsi |
|--------|------|-----------|
| `POST` | `/subtitle/transcribe` | Transkripsi audio via Whisper |
| `GET` | `/subtitle/models` | List model Whisper + status |
| `POST` | `/subtitle/models/download` | Download model Whisper |

### Upload
| Method | Path | Deskripsi |
|--------|------|-----------|
| `POST` | `/upload/youtube` | Upload ke YouTube Shorts |
| `POST` | `/upload/tiktok` | Upload ke TikTok |
| `POST` | `/upload/instagram` | Upload ke Instagram Reels |
| `GET` | `/upload/status/{job_id}` | Status upload |

---

## 🎬 Fitur Utama

### 1. YouTube Clipper
- **Heatmap Scanner**: Membaca grafik *Most Replayed* YouTube.
- **Crop Modes**: Default, Split Left/Right, Face Track, Full, Multi Face (Podcast).
- **Rasio Output**: 9:16, 1:1, 16:9, Original.
- **Auto Subtitle AI**: Transkripsi via Faster-Whisper dengan animasi font ASS.

### 2. Video Compilation (Top N)
- Menggabungkan multiple clips menjadi satu video kompilasi.
- Numbering card + TTS narasi otomatis.
- AI-generated metadata (judul viral, deskripsi, hashtag).

### 3. Auto Upload & Distribution
- YouTube Shorts (Data API v3).
- TikTok (Content Posting API).
- Instagram Reels (Graph API).

### 4. AI Features
- **Whisper Transcription**: Multi-language speech-to-text.
- **Face Tracking**: DeepFace + RetinaFace untuk dynamic crop.
- **AI Highlight Detection**: Gemini/OpenAI/Ollama untuk menemukan momen viral.
- **TTS Engine**: Kokoro TTS + Edge TTS untuk narasi.

---

## 📁 Struktur Proyek

```
engine/
├── server.py              # Entry point FastAPI server
├── api/                   # API endpoint routers
│   ├── health.py          # Health check endpoints
│   ├── clipper.py         # Clipper endpoints
│   ├── subtitle.py        # Subtitle/Whisper endpoints
│   ├── upload.py          # Upload endpoints
│   └── job_manager.py     # In-memory job queue & tracking
├── core/                  # Engine core (tanpa dependensi GUI/web)
│   ├── ai/                # AI detection (LLM integration)
│   ├── processing/        # Video processing pipeline
│   ├── uploaders/         # Platform upload adapters
│   ├── use_cases/         # Business logic orchestration
│   ├── config.py          # Konfigurasi aplikasi
│   ├── controller.py      # Workflow controller
│   ├── processor.py       # Video crop & processing
│   ├── subtitle.py        # Whisper transcription & ASS
│   ├── youtube.py         # yt-dlp integration
│   ├── ffmpeg.py          # FFmpeg wrapper
│   ├── logger.py          # Centralized logging
│   └── utils.py           # Path resolution & helpers
├── fonts/                 # Subtitle fonts
├── assets/                # Static assets
├── tests/                 # Unit & integration tests
├── config.json            # User configuration
├── pyproject.toml         # Python project & dependencies
└── AGENTS.md              # Aturan ketat AI & developer
```

---

## 🧪 Pengujian

```bash
# Unit tests
uv run python -m pytest tests/

# Test API endpoint
uv run python -m pytest tests/test_api.py

# Type checking
make typecheck
```

---

## 🔒 Keamanan

- Server **hanya bind ke `127.0.0.1`** — tidak dapat diakses dari luar mesin.
- Tidak ada authentication karena hanya diakses oleh Rust orchestrator lokal.
- Tidak ada CORS karena tidak diakses langsung oleh browser.

---

## 📦 Production Deployment

Di production, engine ini di-package sebagai **Portable Python bundle** (`.zip`):

```
engine.zip/
├── python/           # Portable Python runtime
├── server.py         # Entry point
├── api/              # API endpoints
├── core/             # Engine core
├── fonts/            # Fonts
└── assets/           # Assets
```

Rust orchestrator (Tauri) akan:
1. Mengecek apakah engine sudah terinstall.
2. Jika belum → download `.zip` dari server → extract ke AppData.
3. Menjalankan `python server.py --port <PORT>` sebagai child process.
4. Melakukan health check polling sampai server ready.
5. Mematikan proses Python saat aplikasi ditutup (graceful shutdown).

---

## 📄 Lisensi

Proyek ini dirilis di bawah lisensi MIT.
