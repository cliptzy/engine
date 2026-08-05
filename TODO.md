# 🚀 Cliptzy Desktop - TODO & Future Enhancements

Berikut adalah daftar ide fitur dan peningkatan yang bisa kita kembangkan selanjutnya untuk membuat Cliptzy semakin _powerful_ dan profesional:

## 1. ⚡ Hardware Acceleration (Akselerasi GPU)

- **FFmpeg NVENC / AMF / QSV**: Menerapkan dukungan _hardware encoding_ pada proses rendering/cropping FFmpeg untuk mempercepat waktu ekspor video secara drastis (menggantikan CPU _software encoding_ murni).
- **Faster-Whisper GPU (CUDA)**: Menambahkan opsi agar deteksi model transkripsi Whisper bisa berjalan menggunakan kartu grafis NVIDIA (jika tersedia), sehingga _subtitle_ bisa digenerasi jauh lebih cepat.

## 2. 🎵 BGM (Background Music) Manager

- Mirip dengan halaman manajemen SFX, tambahkan fitur untuk menyisipkan musik latar belakang secara otomatis.
- Implementasi volume _ducking_ (audio video utama tetap jelas, BGM disesuaikan menjadi lebih pelan seperti -20dB) dan efek _looping_ jika BGM lebih pendek dari klip.

## 5. Mendeteksi tingkat suara

- Kemampuan untuk mendeteksi apakah streamer sedang berteriak atau berbisik atau berbicara dengan normal
- Dipadukan dengan deteksi emosi untuk menentukan sfx yang sesuai

## 4. ✂️ Advanced Timeline / Manual Override

- Menambahkan _slider_ atau antarmuka visual sederhana di GUI agar pengguna bisa menggeser batas awal (`start`) dan akhir (`end`) dari sebuah klip secara manual.
- Berguna jika hasil potongan otomatis (AI/Auto) dirasa kurang pas atau sedikit terpotong.

## 6. 📚 Batch Processing (Antrean Proses)

- Fitur untuk memasukkan banyak URL atau file video sekaligus ke dalam daftar antrean (_Queue_).
- Aplikasi akan memproses semuanya secara berurutan (_sequential_) di latar belakang, sangat cocok untuk ditinggal semalaman (proses _bulk_).

## 8. 🔄 Auto-Update Mechanism (✅ Selesai)

- ~~Sistem pengecekan versi otomatis (misalnya mengecek rilis terbaru di GitHub).~~
- ~~Menampilkan notifikasi di GUI bila ada pembaruan Cliptzy terbaru dan opsi untuk mengunduhnya langsung.~~
