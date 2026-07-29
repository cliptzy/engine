import os
import sys
import shutil
import subprocess
from core.logger import log

def is_ffmpeg_available() -> bool:
    """Checks if ffmpeg is accessible from PATH."""
    return bool(shutil.which("ffmpeg"))

def attempt_add_ffmpeg_to_path() -> bool:
    """
    Attempts to find ffmpeg installed via winget on Windows and add it to PATH.
    Returns True if ffmpeg is successfully found and added (or already available).
    """
    if is_ffmpeg_available():
        return True

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return False

    winget_packages = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
    gyan_root = os.path.join(winget_packages, "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe")
    
    if not os.path.isdir(gyan_root):
        return False

    found_bin_dir = None
    for root, _, files in os.walk(gyan_root):
        if "ffmpeg.exe" in files and os.path.basename(root).lower() == "bin":
            found_bin_dir = root
            break

    if not found_bin_dir:
        return False

    os.environ["PATH"] = f"{found_bin_dir};{os.environ.get('PATH', '')}"
    return is_ffmpeg_available()

def get_model_size(model_name: str) -> str:
    """Returns the approximate size of a Whisper model."""
    sizes = {
        "tiny": "75 MB",
        "base": "142 MB",
        "small": "466 MB",
        "medium": "1.5 GB",
        "large-v1": "2.9 GB",
        "large-v2": "2.9 GB",
        "large-v3": "2.9 GB"
    }
    return sizes.get(model_name, "unknown size")

def check_dependencies(install_whisper: bool = False, skip_update_ytdlp: bool = False, fatal: bool = True, whisper_model: str = "small") -> bool:
    """
    Ensures required dependencies are available.
    Automatically updates yt-dlp and checks FFmpeg availability.
    """
    if not skip_update_ytdlp:
        log.info("Updating yt-dlp...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    if install_whisper:
        try:
            import faster_whisper
            log.info("Faster-Whisper package is already installed.")
            
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            model_folder_name = f"faster-whisper-{whisper_model}"
            
            model_cached = False
            if os.path.exists(cache_dir):
                try:
                    cached_items = os.listdir(cache_dir)
                    model_cached = any(model_folder_name in item.lower() for item in cached_items)
                except Exception as e:
                    log.warning(f"Could not read cache directory: {e}")
            
            if model_cached:
                log.info(f"Model '{whisper_model}' is already cached and ready.")
            else:
                log.warning(f"Model '{whisper_model}' not found in cache.")
                log.info(f"Will auto-download ~{get_model_size(whisper_model)} on first transcribe.")
                
        except ImportError:
            log.info("Installing Faster-Whisper package...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "faster-whisper"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log.info("Faster-Whisper package installed successfully.")
            log.warning(f"Model '{whisper_model}' (~{get_model_size(whisper_model)}) will be downloaded on first use.")

    attempt_add_ffmpeg_to_path()
    if not is_ffmpeg_available():
        log.error("FFmpeg not found. Please install FFmpeg and ensure it is in PATH.")
        if fatal:
            sys.exit(1)
        return False
        
    return True
