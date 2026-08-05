import os
import sys
import ssl
import zipfile
import urllib.request
import subprocess
import shutil
from typing import Optional, Callable
from core.config import APP_ROOT
from core.logger import log

def get_dependency_info(name: str) -> tuple[bool, str, str]:
    """Memeriksa status, versi, dan lokasi path dari FFmpeg dan Deno."""
    is_windows = sys.platform == "win32"
    bin_name = name + ".exe" if is_windows else name
    
    # Cek lokal dulu
    local_path = os.path.abspath(os.path.join(APP_ROOT, "bin", bin_name))
    bin_path = None
    if os.path.exists(local_path) and os.path.isfile(local_path):
        bin_path = local_path
    else:
        bin_path = shutil.which(name)
        
    if not bin_path:
        return False, "Tidak terpasang", "Tidak ditemukan di PATH atau folder bin/"
        
    try:
        bin_dir = os.path.dirname(bin_path)
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
        
        if name == "ffmpeg":
            res = subprocess.run([bin_path, "-version"], capture_output=True, text=True, check=True, timeout=3, env=env)
            first_line = res.stdout.splitlines()[0]
            version = first_line.split("Copyright")[0].replace("ffmpeg version", "").strip()
        elif name == "deno":
            res = subprocess.run([bin_path, "--version"], capture_output=True, text=True, check=True, timeout=3, env=env)
            first_line = res.stdout.splitlines()[0]
            version = first_line.replace("deno", "").strip()
        else:
            version = "Unknown"
    except Exception as e:
        version = f"Gagal membaca versi ({e})"
        
    return True, version, bin_path

def install_dependencies(on_progress: Optional[Callable[[str], None]] = None) -> bool:
    """Mengunduh dan mengekstrak FFmpeg dan Deno ke folder bin lokal."""
    def emit_log(msg: str):
        log.info(msg)
        if on_progress:
            on_progress(msg)

    try:
        # Bypass macOS SSL certificate verification errors globally
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            pass

        emit_log("[INFO] Memulai proses instalasi dependensi secara otomatis...")
        bin_dir = os.path.join(APP_ROOT, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        emit_log(f"[INFO] Direktori bin: {bin_dir}")

        is_windows = sys.platform == "win32"
        is_linux = sys.platform.startswith("linux")
        is_mac = sys.platform == "darwin"

        # 1. Install Deno
        emit_log("\n--- Instalasi Deno ---")
        deno_dest = os.path.join(bin_dir, "deno.exe" if is_windows else "deno")
        if is_windows:
            deno_url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
        elif is_mac:
            deno_url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-apple-darwin.zip"
        else:
            deno_url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip"

        deno_zip = os.path.join(bin_dir, "deno.zip")
        emit_log(f"Mengunduh Deno dari {deno_url}...")
        
        try:
            urllib.request.urlretrieve(deno_url, deno_zip)
            emit_log("Berhasil mengunduh Deno. Mengekstrak...")
            with zipfile.ZipFile(deno_zip, 'r') as zip_ref:
                zip_ref.extractall(bin_dir)
            os.remove(deno_zip)
            emit_log("Deno berhasil diekstrak.")
            if not is_windows:
                os.chmod(deno_dest, 0o755)
        except Exception as e:
            emit_log(f"[ERROR] Gagal mengunduh Deno: {e}")

        # 2. Install FFmpeg
        emit_log("\n--- Instalasi FFmpeg ---")
        if is_windows:
            ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            ffmpeg_zip = os.path.join(bin_dir, "ffmpeg.zip")
            emit_log(f"Mengunduh FFmpeg dari {ffmpeg_url}...")
            try:
                urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
                emit_log("Berhasil mengunduh FFmpeg. Mengekstrak...")
                with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
                    for file_info in zip_ref.infolist():
                        if file_info.filename.endswith("ffmpeg.exe") or file_info.filename.endswith("ffprobe.exe") or file_info.filename.endswith("ffplay.exe"):
                            file_info.filename = os.path.basename(file_info.filename)
                            zip_ref.extract(file_info, bin_dir)
                os.remove(ffmpeg_zip)
                emit_log("FFmpeg berhasil diekstrak.")
            except Exception as e:
                emit_log(f"[ERROR] Gagal mengunduh FFmpeg: {e}")
        elif is_linux:
            ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
            ffmpeg_tar = os.path.join(bin_dir, "ffmpeg.tar.xz")
            emit_log(f"Mengunduh FFmpeg dari {ffmpeg_url}...")
            try:
                urllib.request.urlretrieve(ffmpeg_url, ffmpeg_tar)
                emit_log("Berhasil mengunduh FFmpeg. Mengekstrak...")
                subprocess.run(["tar", "-xf", ffmpeg_tar, "-C", bin_dir, "--strip-components=1", "--wildcards", "*/ffmpeg", "*/ffprobe", "*/ffplay"], check=True)
                os.remove(ffmpeg_tar)
                emit_log("FFmpeg berhasil diekstrak.")
            except Exception as e:
                emit_log(f"[ERROR] Gagal mengunduh FFmpeg: {e}")
        elif is_mac:
            ffmpeg_url = "https://evermeet.cx/ffmpeg/getrelease/zip"
            ffmpeg_zip = os.path.join(bin_dir, "ffmpeg.zip")
            emit_log(f"Mengunduh FFmpeg dari {ffmpeg_url}...")
            try:
                urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
                emit_log("Berhasil mengunduh FFmpeg. Mengekstrak...")
                with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
                    zip_ref.extractall(bin_dir)
                os.remove(ffmpeg_zip)
                os.chmod(os.path.join(bin_dir, "ffmpeg"), 0o755)
                emit_log("FFmpeg berhasil diekstrak.")
            except Exception as e:
                emit_log(f"[ERROR] Gagal mengunduh FFmpeg: {e}")

        # Append bin_dir to PATH globally for current session
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        emit_log("[INFO] Proses instalasi selesai.")
        return True
    except Exception as e:
        emit_log(f"[FATAL ERROR] {e}")
        return False
