# Cliptzy Desktop Standalone 🎬

🇮🇩 **Bahasa Indonesia** | [🇺🇸 English](README_EN.md)

Aplikasi Desktop Standalone native (berbasis Python & PyQt6) untuk mengambil momen paling ramah engangement (*Most Replayed / Heatmap*) dari video YouTube dan mengubahnya secara otomatis menjadi klip vertikal siap unggah untuk Shorts/Reels/TikTok — dilengkapi dengan animasi subtitle AI (Faster-Whisper), pemotong split-screen facecam, dan alur integrasi auto-upload.

---

## 🌟 Keunggulan Standalone Desktop

- ⚡ **Native GUI (PyQt6)**: Tanpa server Flask, tanpa browser eksternal, dan responsif 100%.
- 🎯 **Sidebar Navigation**: Navigasi intuitif untuk pemotong klip, kesiapan distribusi auto-upload, dan pengaturan.
- 🎨 **Modern Dark Aesthetics**: Tampilan UI modern, navbar flat, dan kontrol visual yang presisi.
- 📂 **Drag-and-Drop Native**: Tarik & lepas file `cookies.txt`, video Intro/Outro, atau link URL YouTube langsung ke jendela aplikasi.
- 🔔 **System Tray & Desktop Notifications**: Indikator status taskbar dan notifikasi pop-up saat clipping selesai.
- 🧹 **Clear Cache Manager**: Bersihkan file cache heatmap `segments.json` dan hasil klip video dalam satu klik.
- 📦 **Standalone Executable Ready**: Kompilasi aplikasi menjadi 1 folder executable mandiri via PyInstaller.

---

## 🚀 Cara Menjalankan Aplikasi

### Cara 1: Menggunakan Executable / Launcher (Paling Gampang)

Cukup double-click file **`start.bat`**.

Script ini akan otomatis:
1. Menyiapkan environment Python secara aman.
2. Memeriksa dependensi sistem (FFmpeg).
3. Meluncurkan antarmuka Desktop GUI.

---

### Cara 2: Menjalankan Manual dari Source Code

Pastikan Python 3.10+ dan FFmpeg terinstal di sistem Anda:

```bash
# Install dependensi
pip install -r requirements.txt

# Menjalankan Aplikasi Desktop GUI
python run.py
```

*Jika ingin menjalankan dalam mode CLI interaktif (terminal saja):*
```bash
python run.py --cli --url "https://youtu.be/VIDEO_ID"
```

---

## 🛠️ Kompilasi Standalone Executable (PyInstaller)

Anda dapat membuat aplikasi biner standalone (sehingga dapat dijalankan di komputer pengguna tanpa perlu menginstal Python):

```bash
python build_executable.py
```

Hasil kompilasi biner executable akan tersimpan di dalam folder **`dist/cliptzy/`**.

---

## 🎬 Fitur Utama Aplikasi

### 1. YouTube Clipper Dashboard
- **Heatmap Scanner**: Membaca grafik *Most Replayed* YouTube dan menampilkan daftar segmen interaktif.
- **Crop Modes**:
  - `Default`: Center Crop vertikal 9:16 dari video asli.
  - `Split Left`: Atas = Konten Tengah, Bawah = Facecam Kiri Bawah.
  - `Split Right`: Atas = Konten Tengah, Bawah = Facecam Kanan Bawah.
- **Rasio Output**: 9:16 (Shorts/TikTok), 1:1 (Square Feed), 16:9 (Landscape), Original.
- **Auto Subtitle AI**: Transkripsi audio otomatis via `Faster-Whisper` dengan animasi font ASS.

### 2. Auto Upload & Distribution Workflow Layout
- Layout dan persiapan integrasi API publikasi otomatis ke:
  - 🔴 **YouTube Shorts** (Data API v3)
  - 🎵 **TikTok** (Content Posting API)
  - 📸 **Instagram Reels** (Graph API)

### 3. Integrated Video Player & Output Gallery
- Pemutar video native built-in (`QMediaPlayer` + `QVideoWidget`) dengan slider *Play/Pause/Seek* dan tombol *Open Output Folder*.

---

## 🧪 Pengujian Unit Test

Proyek ini dilengkapi dengan *unit test suite* internal:

```bash
python -m unittest tests/test_clipper.py
```

---

## 📄 Lisensi

Proyek ini dirilis di bawah lisensi MIT.
