import os
from typing import Dict, Any, Optional

from core.config import config
from core.youtube import extract_video_id, fetch_most_replayed, get_video_duration
from core.utils import check_dependencies, is_ffmpeg_available, read_json, write_json
from core.interfaces import ProgressReporter

class ScanVideoUseCase:
    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter

    def execute(self, url: str) -> Dict[str, Any]:
        """Scans YouTube video for heatmap segments and returns total duration and heatmap segments."""
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("URL YouTube tidak valid")

        if not is_ffmpeg_available():
            ok = check_dependencies(install_whisper=False, skip_update_ytdlp=True, fatal=False)
            if not ok:
                raise RuntimeError("FFmpeg tidak ditemukan di sistem")

        job_dir = os.path.join("clips", video_id)
        os.makedirs(job_dir, exist_ok=True)
        cache_file = os.path.join(job_dir, "segments.json")
        
        if os.path.exists(cache_file):
            data_cache = read_json(cache_file)
            if data_cache:
                return {
                    "video_id": video_id,
                    "duration": data_cache.get("duration", 0),
                    "segments": data_cache.get("segments", [])
                }

        if self.reporter:
            self.reporter.on_log("Memindai segmen most replayed...")

        segments = fetch_most_replayed(video_id, config.min_score, config.max_duration)
        total_duration = get_video_duration(video_id)
        
        write_json(cache_file, {"duration": total_duration, "segments": segments})
            
        return {"video_id": video_id, "duration": total_duration, "segments": segments}
