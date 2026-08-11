import json
import os
import threading
from typing import Any, Dict, Optional

from core.config import config
from core.interfaces import ProgressReporter
from core.yt_dlp_logger import create_yt_dlp_logger

_preview_lock = threading.Lock()
_preview_cache: Dict[str, Dict[str, Any]] = {}


class PreviewClipUseCase:
    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter

    def execute(self, url: str) -> Dict[str, Any]:
        """Fetches metadata (title, thumbnail, duration, uploader) for a YouTube URL."""
        url_clean = url.strip()
        if not url_clean:
            raise ValueError("URL YouTube tidak boleh kosong")

        with _preview_lock:
            cached = _preview_cache.get(url_clean)
            if cached:
                return cached

        import os

        if os.path.isfile(url_clean):
            import subprocess

            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                url_clean,
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True)
                dur = int(float(res.stdout.strip())) if res.stdout.strip() else 0
            except Exception:
                dur = 0

            import hashlib

            base_name = os.path.basename(url_clean)
            safe_name = "".join([c if c.isalnum() else "_" for c in base_name])
            video_id = (
                f"local_{safe_name}_{hashlib.md5(url_clean.encode()).hexdigest()[:6]}"
            )

            preview = {
                "title": os.path.basename(url_clean),
                "thumbnail": None,
                "uploader": "Local Video",
                "duration": dur,
                "webpage_url": url_clean,
                "id": video_id,
                "language": "id",
            }
            with _preview_lock:
                _preview_cache[url_clean] = preview
                if len(_preview_cache) > 200:
                    _preview_cache.clear()
            return preview

        from typing import Any

        import yt_dlp

        ydl_opts: dict[str, Any] = {
            "skip_download": True,
            "no_warnings": True,
            "logger": create_yt_dlp_logger("[yt-dlp:preview]"),
        }

        if config.youtube.session and os.path.exists(config.youtube.session):
            ydl_opts["cookiefile"] = config.youtube.session

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                raw: Any = ydl.extract_info(url_clean, download=False)
        except Exception as e:
            raise RuntimeError(f"Gagal mengambil metadata video: {e}")

        item = (
            raw["entries"][0]
            if isinstance(raw, dict) and "entries" in raw and raw.get("entries")
            else raw
        )

        lang = item.get("language")
        if lang and "-" in lang:
            lang = lang.split("-")[0]

        preview = {
            "title": item.get("title", "Unknown Title"),
            "thumbnail": item.get("thumbnail"),
            "uploader": item.get("uploader", "Unknown Uploader"),
            "duration": item.get("duration", 0),
            "webpage_url": item.get("webpage_url") or url_clean,
            "id": item.get("id"),
            "language": lang,
        }

        with _preview_lock:
            _preview_cache[url_clean] = preview
            if len(_preview_cache) > 200:
                _preview_cache.clear()

        return preview

    def get_cached_preview(self, url: str) -> Optional[Dict[str, Any]]:
        url_clean = url.strip()
        with _preview_lock:
            return _preview_cache.get(url_clean)
