# 🚀 Roadmap & TODO: Fitur Auto Uploader Cliptzy

Dokumen ini berisi rencana pengembangan dan daftar tugas (TODO) untuk mengimplementasikan fitur Auto Upload & Multi-Platform Distribution pada aplikasi Cliptzy. Seluruh pengembangan harus mematuhi arsitektur yang ditetapkan di `AGENTS.md`.

---

## 🏗️ 1. Tugas General (Infrastruktur & Arsitektur)

- [x] **Modul Core Uploader (`core/uploader.py`)**
  - Buat modul abstrak/induk untuk menangani standarisasi *upload* (kelas `BaseUploader`).
  - Implementasi sistem balikan (*return value*) yang seragam (Sukses/Gagal, URL Video, Pesan Error).
- [x] **Sistem Antrean & Threading (`QThread`)**
  - Buat `UploadWorker` di UI agar proses *upload* tidak menyebabkan GUI *freeze* (*Non-Blocking UI Policy*).
  - Implementasikan fungsi jeda (*delay/sleep*) antar *upload* untuk menghindari *rate-limiting* atau deteksi spam dari platform.
- [x] **Pembaruan Antarmuka Pengguna (GUI)**
  - Tambahkan **Progress Bar** (0-100%) untuk memantau proses *upload* file besar.
  - Tambahkan **Indikator Status** pada widget *Uploader* (misalnya: `⏳ Menunggu...`, `🚀 Mengunggah...`, `✅ Selesai`, `❌ Gagal`).
- [x] **Manajemen Error & Log**
  - Tangkap dan teruskan semua *exception* (seperti *network timeout* atau *cookie expired*) ke *Global Log*.
  - Implementasikan *Graceful Degradation*: Jika satu platform gagal, catat error tersebut namun tetap lanjutkan proses *upload* ke platform berikutnya.

---

## 🔴 2. Spesifik: YouTube Shorts

- [x] **Instalasi Dependensi**
  - Tambahkan `google-auth-oauthlib`, `google-auth-httplib2`, dan `google-api-python-client`.
- [x] **Sistem Autentikasi (OAuth 2.0)**
  - Buat skrip untuk memicu jendela login *browser* pada penggunaan pertama.
  - Simpan dan kelola `token.json` secara lokal agar *login* persisten tanpa perlu input manual berulang kali.
- [x] **Logika Upload API**
  - Integrasikan endpoint `youtube.videos.insert`.
  - Suntikkan metadata (Judul AI, Deskripsi AI, dan hashtag dari `config.yt_tags`).
  - Pastikan visibilitas (*Public*, *Unlisted*, *Private*) diset secara dinamis sesuai dengan `config.yt_visibility`.

---

## 🎵 3. Spesifik: TikTok

- [ ] **Instalasi Dependensi**
  - Mengingat TikTok tidak memiliki API publik untuk akun personal, siapkan *library* otomasi. Sangat direkomendasikan menggunakan `playwright` (atau *wrapper* khusus seperti `tiktok-uploader`).
- [ ] **Sistem Autentikasi (Cookies/Session)**
  - Bangun logika untuk membaca token/sesi dari `config.tt_session` atau menggunakan sistem *cookie injection*.
- [ ] **Logika Upload Otomatis (Headless Browser)**
  - Inisialisasi *headless browser* untuk melakukan unggah video seolah-olah dilakukan oleh manusia.
  - Otomatisasi pengetikan *caption* (gabungan dari Judul AI + `config.tt_caption`).
  - Implementasi logika pemilihan Dropdown privasi (*Public*, *Friends*, *Private*).

---

## 📸 4. Spesifik: Instagram Reels

- [ ] **Instalasi Dependensi**
  - Evaluasi kebutuhan API. Jika targetnya akun Bisnis/Kreator, persiapkan library *requests* untuk berinteraksi dengan Instagram Graph API Meta. 
  - (Opsi Cadangan): Gunakan `instagrapi` untuk meniru perilaku *mobile client* jika Graph API ditolak atau tidak memadai.
- [ ] **Sistem Autentikasi**
  - Hubungkan *Access Token* (`config.ig_access_token`) dan *Business Account ID* (`config.ig_business_id`).
- [ ] **Logika Upload Reels**
  - Susun mekanisme pengiriman *media container* ke server Meta dan peluncuran perintah *publishing*.
  - Sisipkan *caption* bawaan (`config.ig_caption`) bersama dengan *metadata* tambahan hasil *generate* AI.

---

*Catatan Akhir: Fitur auto-upload harus tetap bekerja secara opsional. Aplikasi tidak boleh melempar error kritis jika pengguna memutuskan untuk tidak mengisi token/kredensial untuk salah satu platform di atas.*
