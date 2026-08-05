import os
import shutil
from typing import Dict, Any, List, Optional, Callable

from core.config import config
from core.logger import log
from core.interfaces import ProgressReporter, BaseUploader
from core.use_cases.scan_video import ScanVideoUseCase
from core.use_cases.clip_video import ClipVideoUseCase
from core.use_cases.preview_clip import PreviewClipUseCase
from core.use_cases.detect_highlights import DetectHighlightsUseCase
from core.use_cases.upload_clip import UploadClipUseCase

class ClipController:
    """
    Central Controller layer for Cliptzy.
    Decouples business logic, API processing, and job execution from GUI.
    Acts as a Facade delegating tasks to specific Use Cases.
    """

    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter
        config.load_from_file()

        # Initialize use cases
        self.scan_uc = ScanVideoUseCase(reporter=self.reporter)
        self.clip_uc = ClipVideoUseCase(reporter=self.reporter)
        self.preview_uc = PreviewClipUseCase(reporter=self.reporter)
        self.detect_uc = DetectHighlightsUseCase(reporter=self.reporter)

    def get_preview(self, url: str) -> Dict[str, Any]:
        """Fetches metadata (title, thumbnail, duration, uploader) for a YouTube URL."""
        return self.preview_uc.execute(url)

    def scan_segments(self, url: str) -> Dict[str, Any]:
        """Scans YouTube video for heatmap segments and returns total duration and heatmap segments."""
        return self.scan_uc.execute(url)

    def get_cached_ai_highlights(self, url: str) -> Optional[Dict[str, Any]]:
        from core.youtube import extract_video_id
        from core.utils import read_json
        video_id = extract_video_id(url)
        if not video_id:
            return None
        job_dir = os.path.join("clips", video_id)
        ai_cache_file = os.path.join(job_dir, "ai_segments.json")
        return read_json(ai_cache_file) if os.path.exists(ai_cache_file) else None

    def execute_clipping(
        self,
        payload: Dict[str, Any],
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes the clipping pipeline based on settings payload.
        """
        return self.clip_uc.execute(payload, is_cancelled)

    def generate_subtitle_preview_sample(self, payload: Dict[str, Any]) -> str:
        """
        Generates a short 10-second preview clip with subtitles burned in for tuning subtitle delay.
        """
        return self.clip_uc.generate_subtitle_preview_sample(payload)

    def scan_ai_highlights(self, url: str, ai_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribes audio and uses AI to detect highlights.
        """
        return self.detect_uc.execute(url, ai_config)
        
    def upload_clip(self, uploader: BaseUploader, video_path: str, title: str, description: str, tags: List[str]) -> bool:
        """
        Uploads a video to a specific platform.
        """
        from pathlib import Path
        upload_uc = UploadClipUseCase(uploader=uploader, reporter=self.reporter)
        return upload_uc.execute(Path(video_path), title, description, tags)

    def import_cookies(self, file_path: str) -> bool:
        """Imports Netscape cookies file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError("File cookies tidak ditemukan")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "# Netscape HTTP Cookie File" not in content and ".youtube.com" not in content:
            raise ValueError("Format file cookie tidak valid. Harus format Netscape HTTP Cookie File.")

        dest = "cred/yt_cookies.txt"
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(file_path, dest)
        config.youtube.session = dest
        config.save_to_file()
        return True

    def set_intro_video(self, file_path: str) -> str:
        """Sets and copies intro video to assets folder."""
        if not os.path.exists(file_path):
            raise FileNotFoundError("File intro video tidak ditemukan")
        os.makedirs("assets", exist_ok=True)
        ext = os.path.splitext(file_path)[1]
        dest = os.path.join("assets", f"intro{ext}")
        shutil.copy2(file_path, dest)
        config.intro_video = dest
        config.save_to_file()
        return dest

    def set_outro_video(self, file_path: str) -> str:
        """Sets and copies outro video to assets folder."""
        if not os.path.exists(file_path):
            raise FileNotFoundError("File outro video tidak ditemukan")
        os.makedirs("assets", exist_ok=True)
        ext = os.path.splitext(file_path)[1]
        dest = os.path.join("assets", f"outro{ext}")
        shutil.copy2(file_path, dest)
        config.outro_video = dest
        config.save_to_file()
        return dest

    def clear_outro_video(self) -> None:
        """Clears the configured outro video (does not delete the assets file)."""
        config.outro_video = None
        config.save_to_file()

    def set_watermark_image(self, file_path: str) -> str:
        """Sets and copies watermark image to assets folder."""
        if not os.path.exists(file_path):
            raise FileNotFoundError("File watermark tidak ditemukan")
        os.makedirs("assets", exist_ok=True)
        ext = os.path.splitext(file_path)[1]
        dest = os.path.join("assets", f"watermark{ext}")
        shutil.copy2(file_path, dest)
        config.watermark_image = dest
        config.save_to_file()
        return dest

    def clear_watermark_image(self) -> None:
        """Clears the configured watermark image."""
        config.watermark_image = None
        config.save_to_file()

    def get_available_fonts(self) -> List[str]:
        """Lists available fonts in fonts directory."""
        fonts = ["Arial", "Poppins", "Montserrat", "Impact", "Trebuchet MS"]
        if os.path.isdir("fonts"):
            for fname in os.listdir("fonts"):
                if fname.lower().endswith((".ttf", ".otf")):
                    name = os.path.splitext(fname)[0]
                    if name not in fonts:
                        fonts.append(name)
        return fonts

    def clear_cache_and_clips(self) -> Dict[str, Any]:
        """
        Clears cached segment JSON files, temporary MKV/MP4 files, and generated clips in clips/ directory.
        """
        import core.use_cases.preview_clip as pc
        with pc._preview_lock:
            pc._preview_cache.clear()

        deleted_files = 0
        deleted_bytes = 0
        clips_dir = "clips"

        if os.path.exists(clips_dir):
            for root, dirs, files in os.walk(clips_dir, topdown=False):
                for f in files:
                    file_path = os.path.join(root, f)
                    try:
                        size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_files += 1
                        deleted_bytes += size
                    except Exception as e:
                        log.warning(f"Gagal menghapus file cache {file_path}: {e}")
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    try:
                        os.rmdir(dir_path)
                    except Exception:
                        pass

        return {
            "deleted_files": deleted_files,
            "deleted_size_mb": round(deleted_bytes / (1024 * 1024), 2)
        }

# For backward compatibility during migration, provide a global controller instance, 
# although it won't have a ProgressReporter injected by default.
controller = ClipController()
