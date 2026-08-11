import json
import threading
import urllib.request
from typing import Optional, Tuple

from core import __version__
from core.logger import log


def check_for_updates() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Mengecek pembaruan dari GitHub releases.
    Mengembalikan tuple: (has_update, new_version, release_url)
    """
    try:
        url = "https://api.github.com/repos/dickymuliafiqri/cliptzy/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "Cliptzy-Updater"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        latest_version = data.get("tag_name", "")
        release_url = data.get("html_url", "")

        if not latest_version:
            return False, None, None

        # Perbandingan versi sederhana
        current = __version__.replace("v", "").strip()
        latest = latest_version.replace("v", "").strip()

        # Split menjadi array integer
        curr_parts = [int(x) for x in current.split(".") if x.isdigit()]
        lat_parts = [int(x) for x in latest.split(".") if x.isdigit()]

        # Jika format tidak sesuai, lewati
        if not curr_parts or not lat_parts:
            return False, None, None

        # Bandingkan parts
        for i in range(max(len(curr_parts), len(lat_parts))):
            c = curr_parts[i] if i < len(curr_parts) else 0
            l = lat_parts[i] if i < len(lat_parts) else 0
            if l > c:
                return True, latest_version, release_url
            elif c > l:
                return False, None, None

        return False, None, None

    except Exception as e:
        log.warning(f"Gagal mengecek pembaruan otomatis: {e}")
        return False, None, None
