import os
import sys
import shutil
import subprocess
import platform
from typing import Any
from core.logger import log

def open_dir(dir_path):
    sysops = platform.system()

    try:
        if sysops == "Windows":
            os.startfile(dir_path)  # type: ignore
        elif sysops == "Darwin":
            subprocess.Popen(["open", dir_path])
        else:
            subprocess.Popen(["xdg-open", dir_path])
    except Exception as e:
        print(f"Terjadi kesalahan saat membuka folder: {e}")

def inject_local_bin_to_path():
    """
    Unconditionally prepends the local app bin/ directory to the system PATH.
    This ensures that downloaded dependencies (FFmpeg, Deno) take highest priority.
    """
    if getattr(sys, 'frozen', False):
        app_root = os.path.dirname(sys.executable)
    else:
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    bin_dir = os.path.join(app_root, "bin")
    if os.path.isdir(bin_dir) and bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"

# Execute immediately on import to ensure all subprocesses see the local bin directory
inject_local_bin_to_path()

def is_ffmpeg_available() -> bool:
    """Checks if ffmpeg is accessible from PATH."""
    return bool(shutil.which("ffmpeg"))

def is_ffmpeg_libass_supported() -> bool:
    """Checks if the available FFmpeg supports the 'subtitles' filter (requires libass)."""
    if not is_ffmpeg_available():
        return False
    try:
        import re
        res = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True, timeout=3)
        return bool(re.search(r'\bsubtitles\b', res.stdout))
    except Exception:
        return False

def is_deno_available() -> bool:
    """Checks if deno is accessible from PATH."""
    return bool(shutil.which("deno"))

def attempt_add_ffmpeg_to_path() -> bool:
    """
    Attempts to find ffmpeg in local app bin/ directory, WinGet packages, or system PATH.
    Returns True if ffmpeg is successfully found and added to PATH.
    """
    if is_ffmpeg_available():
        return True

    # 1. Check local bin/ folder in application directory
    # (Already handled by inject_local_bin_to_path, but keeping check just in case)
    if is_ffmpeg_available():
        return True

    # 2. Check Windows Winget packages if on Windows
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        winget_packages = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
        gyan_root = os.path.join(winget_packages, "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe")
        
        if os.path.isdir(gyan_root):
            for root, _, files in os.walk(gyan_root):
                if ("ffmpeg.exe" in files or "ffmpeg" in files) and os.path.basename(root).lower() == "bin":
                    os.environ["PATH"] = f"{root}{os.pathsep}{os.environ.get('PATH', '')}"
                    break

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
    is_frozen = getattr(sys, 'frozen', False)
    
    if not skip_update_ytdlp and not is_frozen:
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
            if not is_frozen:
                log.info("Installing Faster-Whisper package...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "faster-whisper"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                log.info("Faster-Whisper package installed successfully.")
                log.warning(f"Model '{whisper_model}' (~{get_model_size(whisper_model)}) will be downloaded on first use.")
            else:
                log.error("Faster-Whisper is not bundled in this executable. Subtitle features will be unavailable.")

    attempt_add_ffmpeg_to_path()
    if not is_ffmpeg_available():
        log.error("FFmpeg not found. Please install FFmpeg and ensure it is in PATH.")
        if fatal:
            sys.exit(1)
        return False
        
    return True

def read_json(file_path: str, default: Any = None) -> Any:
    """Reads a JSON file safely. Returns 'default' if it fails or file doesn't exist."""
    import os, json
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Gagal membaca {file_path}: {e}")
    return default if default is not None else {}

def write_json(file_path: str, data: Any, indent: int = 2) -> bool:
    """Writes a JSON file safely."""
    import os, json
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
        return True
    except Exception as e:
        log.warning(f"Gagal menulis ke {file_path}: {e}")
        return False

def get_preview_data(job_dir: str | None = None, video_id: str | None = None) -> dict:
    """
    Reads and returns the content of preview.json.
    Priority:
    1. job_dir
    2. video_id (resolves to clips/<video_id>)
    3. config.job_dir
    """
    import os
    if not job_dir and not video_id:
        try:
            from core.config import config
            job_dir = config.job_dir
        except ImportError:
            pass

    if not job_dir and video_id:
        job_dir = os.path.join("clips", video_id)

    if not job_dir:
        return {}

    preview_path = os.path.join(job_dir, "preview.json")
    return read_json(preview_path, default={})
