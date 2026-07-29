import re
import json
import subprocess
import sys
import os
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs
import requests
from core.logger import log

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
    
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--dump-json",
        "--skip-download"
    ]
    
    from core.config import config
    if config.cookies_file and os.path.exists(config.cookies_file):
        cmd.extend(["--cookies", config.cookies_file])
        
    cmd.append(f"https://youtu.be/{video_id}")

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
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
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--get-duration"
    ]
    
    from core.config import config
    if config.cookies_file and os.path.exists(config.cookies_file):
        cmd.extend(["--cookies", config.cookies_file])
        
    cmd.append(f"https://youtu.be/{video_id}")

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        time_parts = res.stdout.strip().split(":")

        if len(time_parts) == 2:
            return int(time_parts[0]) * 60 + int(time_parts[1])
        if len(time_parts) == 3:
            return (
                int(time_parts[0]) * 3600 +
                int(time_parts[1]) * 60 +
                int(time_parts[2])
            )
    except Exception as e:
        log.warning(f"Failed to get video duration: {e}")

    return 3600
