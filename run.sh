#!/bin/bash

# Cek apakah uv sudah terinstal
if ! command -v uv &> /dev/null
then
    echo "uv belum terinstal. Menginstal uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Tambahkan path uv ke sesi saat ini
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

echo ""
echo "Mengonfigurasi environment dan menginstal dependensi..."
# Menggunakan Python 3.13 sesuai pyproject.toml
uv sync --python 3.13

echo ""
echo "Memulai aplikasi Cliptzy..."
uv run main.py
