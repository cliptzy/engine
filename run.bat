@echo off
setlocal

:: Cek apakah uv sudah terinstal
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo uv belum terinstal. Menginstal uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    :: Tambahkan path uv ke sesi saat ini agar bisa langsung dipakai
    set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
)

echo.
echo Mengonfigurasi environment dan menginstal dependensi...
:: Menggunakan Python 3.13 sesuai pyproject.toml
uv sync --python 3.13

echo.
echo Memulai aplikasi Cliptzy...
uv run main.py

pause
