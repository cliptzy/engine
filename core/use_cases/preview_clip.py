import os
import json
import subprocess
import sys
import threading
from typing import Dict, Any, Optional

from core.config import config
from core.interfaces import ProgressReporter

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

        import yt_dlp
        from typing import Any
        ydl_opts: dict[str, Any] = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        if config.youtube.session and os.path.exists(config.youtube.session):
            ydl_opts['cookiefile'] = config.youtube.session
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
                raw: Any = ydl.extract_info(url_clean, download=False)
        except Exception as e:
            raise RuntimeError(f"Gagal mengambil metadata video: {e}")

        item = raw["entries"][0] if isinstance(raw, dict) and "entries" in raw and raw.get("entries") else raw

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
            "language": lang
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
