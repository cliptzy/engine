import re
import json
import subprocess
import os
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs
import requests
from core.logger import log
from core.yt_dlp_logger import create_yt_dlp_logger

def extract_video_id(url: str) -> Optional[str]:
    """
    Extracts the YouTube video ID from a given URL.
    Supports standard YouTube URLs, shortened URLs, and Shorts URLs.
    """
    parsed = urlparse(url)

    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path[1:]

    if parsed.hostname in ("youtube.com", "www.youtube.com"):
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)
            return query.get("v", [None])[0]
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/")[2]

    return None

def fetch_most_replayed(video_id: str, min_score: float, max_duration: int) -> List[Dict[str, Any]]:
    """
    Fetches and parses YouTube 'Most Replayed' heatmap data using yt-dlp.
    Returns a list of high-engagement segments.
    """
    log.info(f"Reading YouTube heatmap data for video ID: {video_id}")
    
    import yt_dlp
    from typing import Any
    from core.config import config
    
    ydl_opts: dict[str, Any] = {
        'skip_download': True,
        'no_warnings': True,
        'remote_components': ['ejs:github'],
        'logger': create_yt_dlp_logger('[yt-dlp:heatmap]'),
    }
    
    if config.youtube.session and os.path.exists(config.youtube.session):
        ydl_opts['cookiefile'] = config.youtube.session
        
    url = f"https://youtu.be/{video_id}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
            data: Any = ydl.extract_info(url, download=False)
        heatmap = data.get("heatmap")
        
        if not heatmap:
            log.warning("No heatmap markers found in the video data.")
            return []

        results = []
        for marker in heatmap:
            try:
                score = float(marker.get("value", 0))
                if score >= min_score:
                    start = float(marker.get("start_time", 0))
                    end = float(marker.get("end_time", 0))
                    duration = end - start
                    results.append({
                        "start": start,
                        "duration": min(duration, max_duration),
                        "score": score
                    })
            except Exception:
                continue

        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    except Exception as e:
        log.error(f"Failed to fetch YouTube page/heatmap: {e}")
        return []

def get_video_duration(video_id: str) -> int:
    """
    Retrieves the total duration of a YouTube video in seconds using yt-dlp.
    """
    import yt_dlp
    from typing import Any
    from core.config import config
    
    ydl_opts: dict[str, Any] = {
        'skip_download': True,
        'no_warnings': True,
        'remote_components': ['ejs:github'],
        'extract_flat': True,
        'logger': create_yt_dlp_logger('[yt-dlp:duration]'),
    }
    
    if config.youtube.session and os.path.exists(config.youtube.session):
        ydl_opts['cookiefile'] = config.youtube.session
        
    url = f"https://youtu.be/{video_id}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
            data: Any = ydl.extract_info(url, download=False)
        duration = data.get("duration")
        if duration:
            return int(duration)
    except Exception as e:
        log.warning(f"Failed to get video duration: {e}")

    return 3600
