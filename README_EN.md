# Cliptzy Desktop Standalone 🎬

[🇮🇩 Bahasa Indonesia](README.md) | 🇺🇸 **English**

Native Standalone Desktop Application (Python & Flet) for extracting YouTube high-engagement moments (*Most Replayed / Heatmap*) and automatically generating vertical clips ready for Shorts/Reels/TikTok — powered by AI Subtitles (Faster-Whisper), split-screen facecam cropping, and auto-upload distribution workflow.

---

## 🌟 Standalone Desktop Highlights

- ⚡ **Native GUI (Flet)**: No Flask server, no external browser window, 100% responsive.
- 🎯 **Sidebar Navigation**: Intuitive navigation panel for Clipper dashboard, distribution readiness, and settings.
- 🎨 **Modern Dark Aesthetics**: Sleek UI theme, flat unrounded navbar, and precise visual controls.
- 📂 **Native Drag-and-Drop**: Drag & drop `cookies.txt`, Intro/Outro videos, or YouTube URL links directly into the app window.
- 🔔 **System Tray & Desktop Notifications**: Taskbar status indicator and pop-up notifications when clipping finishes.
- 🧹 **Clear Cache Manager**: Delete cached `segments.json` files and generated video clips in one click.
- 📦 **Standalone Executable Ready**: Bundle application into a single standalone executable folder via PyInstaller.

---

## 🚀 How to Run

### Option 1: Executable / Launcher (Easiest)

Simply double-click **`start.bat`**.

The launcher will automatically:
1. Prepare a secure Python virtual environment.
2. Verify system dependencies (FFmpeg).
3. Launch the Desktop GUI interface.

---

### Option 2: Manual Run from Source

Ensure Python 3.10+ and FFmpeg are installed on your system:

```bash
# Install dependencies
pip install -r requirements.txt

# Run Desktop GUI App
python run.py
```

*To run in interactive CLI mode (terminal only):*
```bash
python run.py --cli --url "https://youtu.be/VIDEO_ID"
```

---

## 🛠️ Build Standalone Executable (PyInstaller)

You can build a standalone executable folder (so users can run Cliptzy without installing Python):

```bash
python build_executable.py
```

The compiled standalone executable directory will be saved to **`dist/cliptzy/`**.

---

## 🎬 Key Features

### 1. YouTube Clipper Dashboard
- **Heatmap Scanner**: Reads YouTube *Most Replayed* graph data and renders interactive segment checklists.
- **Crop Modes**:
  - `Default`: Center Crop 9:16 vertical from original video.
  - `Split Left`: Top = Center Content, Bottom = Bottom-Left Facecam.
  - `Split Right`: Top = Center Content, Bottom = Bottom-Right Facecam.
- **Output Aspect Ratios**: 9:16 (Shorts/TikTok), 1:1 (Square Feed), 16:9 (Landscape), Original.
- **AI Auto Subtitle**: Automatic audio transcription via `Faster-Whisper` with animated ASS subtitles.

### 2. Auto Upload & Distribution Workflow Layout
- Workflow layout and configuration setup for auto-publishing clips to:
  - 🔴 **YouTube Shorts** (Data API v3)
  - 🎵 **TikTok** (Content Posting API)
  - 📸 **Instagram Reels** (Graph API)

### 3. Integrated Video Player & Output Gallery
- Built-in multimedia player (`QMediaPlayer` + `QVideoWidget`) with *Play/Pause/Seek* slider and *Open Output Folder* button.

---

## 🧪 Unit Testing

Includes an internal unit test suite:

```bash
python -m unittest tests/test_clipper.py
```

---

## 📄 License

This project is licensed under the MIT License.
