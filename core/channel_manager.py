"""
Channel & Video Repository Manager for Cliptzy Desktop Application.
Extracts authentic channel metadata (avatar, subscribers, title) and videos catalog via yt-dlp.
"""

import os
import json
import subprocess
import sys
import urllib.request
from typing import List, Dict, Any, Optional
from core.logger import log

CHANNELS_DIR = "channels"
CHANNELS_INDEX_FILE = os.path.join(CHANNELS_DIR, "channels.json")

def format_subscriber_count(count: Optional[int]) -> str:
    """Formats raw subscriber number to human readable string (e.g. 1.2M subscribers)."""
    if not count or count <= 0:
        return "Subscribers N/A"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M subscriber"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K subscriber"
    return f"{count} subscriber"

class ChannelManager:
    def __init__(self):
        os.makedirs(CHANNELS_DIR, exist_ok=True)

    def get_all_channels(self) -> List[Dict[str, Any]]:
        """Returns list of all saved YouTuber channels."""
        if not os.path.exists(CHANNELS_INDEX_FILE):
            return self._get_default_channels()
        try:
            with open(CHANNELS_INDEX_FILE, "r", encoding="utf-8") as f:
                channels = json.load(f)
                return channels if isinstance(channels, list) else []
        except Exception as e:
            log.warning(f"Gagal membaca channels index: {e}")
            return self._get_default_channels()

    def _get_default_channels(self) -> List[Dict[str, Any]]:
        """Returns default preset channels with authentic fallback data."""
        return []

    def save_channels(self, channels: List[Dict[str, Any]]):
        """Saves channels list to index file."""
        try:
            with open(CHANNELS_INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(channels, f, indent=2)
        except Exception as e:
            log.error(f"Gagal menyimpan file channels.json: {e}")

    def add_channel_by_url_or_handle(self, query: str) -> Dict[str, Any]:
        """
        Extracts authentic channel metadata (avatar, subscribers, title) and video catalog via yt-dlp.
        """
        query = query.strip()
        if not query:
            raise ValueError("Username / URL channel tidak boleh kosong")

        if not query.startswith("http"):
            if not query.startswith("@"):
                query = f"@{query}"
            url = f"https://www.youtube.com/{query}"
        else:
            url = query

        log.info(f"Extracting authentic channel info for {url} via yt-dlp...")

        cmd_meta = [
            sys.executable, "-m", "yt_dlp",
            "--force-ipv4", "--quiet", "--no-warnings",
            "-J", "--flat-playlist",
            "--playlist-end", "60",
            f"{url}/videos"
        ]

        res = subprocess.run(cmd_meta, capture_output=True, text=True)
        if res.returncode != 0 or not res.stdout.strip():
            cmd_meta[-1] = url
            res = subprocess.run(cmd_meta, capture_output=True, text=True)

        if res.returncode != 0 or not res.stdout.strip():
            raise RuntimeError(f"Gagal mengambil data channel dari YouTube: {url}")

        try:
            info = json.loads(res.stdout)
        except Exception as e:
            raise RuntimeError(f"Gagal memproses data JSON channel: {e}")

        channel_title = info.get("title") or info.get("uploader") or query
        channel_id = info.get("uploader_id") or info.get("id") or query.replace("@", "").lower()
        handle = info.get("uploader_url") or f"@{channel_id}"
        if "/" in handle:
            handle = "@" + handle.rstrip("/").split("/")[-1]

        subs_count = info.get("channel_follower_count") or info.get("subscriber_count")
        subs_str = format_subscriber_count(subs_count)

        # Extract authentic channel avatar / profile picture URL
        avatar_url = ""
        thumbnails = info.get("thumbnails") or []
        if isinstance(thumbnails, list) and thumbnails:
            avatar_url = thumbnails[-1].get("url", "")

        entries = info.get("entries", [])
        videos = []

        for entry in entries:
            v_id = entry.get("id")
            v_title = entry.get("title", "Untitled Video")
            if not v_id or not v_title:
                continue

            view_count = entry.get("view_count") or 0
            dur = entry.get("duration") or 0
            is_live = bool(entry.get("is_live") or entry.get("was_live") or "live" in v_title.lower())

            videos.append({
                "id": v_id,
                "title": v_title,
                "url": f"https://www.youtube.com/watch?v={v_id}",
                "views": view_count,
                "duration": dur,
                "type": "live" if is_live else "upload",
                "thumbnail": f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
            })

        channel_data = {
            "id": channel_id,
            "name": channel_title,
            "handle": handle,
            "avatar": avatar_url,
            "subscribers_str": subs_str,
            "video_count": len(videos),
            "channel_url": url
        }

        # Save channel catalog JSON file
        channel_file = os.path.join(CHANNELS_DIR, f"{channel_id}.json")
        try:
            with open(channel_file, "w", encoding="utf-8") as f:
                json.dump({"channel": channel_data, "videos": videos}, f, indent=2)
        except Exception as e:
            log.warning(f"Gagal menyimpan katalog video channel {channel_id}: {e}")

        # Update channels list
        all_channels = self.get_all_channels()
        all_channels = [c for c in all_channels if c.get("id") != channel_id]
        all_channels.insert(0, channel_data)
        self.save_channels(all_channels)

        return channel_data

    def get_channel_videos_catalog(
        self,
        channel_id: str,
        tab: str = "upload",
        search: str = "",
        sort_by: str = "views",
        page: int = 1,
        per_page: int = 12
    ) -> Dict[str, Any]:
        """
        Returns paginated, filtered, and sorted videos for a channel.
        """
        channel_file = os.path.join(CHANNELS_DIR, f"{channel_id}.json")
        videos = []
        channel_meta = {}

        if os.path.exists(channel_file):
            try:
                with open(channel_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    videos = data.get("videos", [])
                    channel_meta = data.get("channel", {})
            except Exception:
                pass

        # Filter by Tab (Upload vs Live)
        if tab == "live":
            filtered = [v for v in videos if v.get("type") == "live"]
        else:
            filtered = [v for v in videos if v.get("type") != "live"]

        if not filtered and videos:
            filtered = videos

        # Filter by Search Query
        if search:
            q = search.lower().strip()
            filtered = [v for v in filtered if q in v.get("title", "").lower()]

        # Sort
        if sort_by == "views":
            filtered.sort(key=lambda x: x.get("views", 0), reverse=True)
        elif sort_by == "duration":
            filtered.sort(key=lambda x: x.get("duration", 0), reverse=True)

        total_items = len(filtered)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        page = min(max(1, page), total_pages)

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_videos = filtered[start_idx:end_idx]

        return {
            "channel": channel_meta,
            "videos": page_videos,
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": page
        }

channel_manager = ChannelManager()
