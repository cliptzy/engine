import json
import os

import requests

from core.config import config
from core.logger import log as logger


def check_youtube_auth() -> tuple[bool, str]:
    token_file = "cred/youtube_token.json"
    if not os.path.exists(token_file):
        return (
            False,
            "Token file tidak ditemukan. Silakan lakukan upload sekali untuk memicu login browser.",
        )

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        from core.utils import read_json

        creds_data = read_json(token_file)
        if creds_data:
            creds = Credentials.from_authorized_user_info(creds_data)
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        with open(token_file, "w", encoding="utf-8") as f:
                            f.write(creds.to_json())
                        return True, "Token berhasil diperbarui (direfresh) dan aktif."
                    except Exception as e:
                        return False, f"Gagal refresh token: {str(e)}"
                else:
                    return False, "Token kadaluarsa dan tidak bisa direfresh."
            return True, "Token valid dan aktif."
        return False, "Data token tidak ditemukan di file."
    except Exception as e:
        logger.error(f"Error check_youtube_auth: {e}")
        return False, f"Error validasi token: {str(e)}"


def check_tiktok_auth() -> tuple[bool, str]:
    if not config.tiktok.session or not os.path.exists(config.tiktok.session):
        return False, "File cookie TikTok belum diisi atau tidak ditemukan."

    try:
        session_id = ""
        with open(config.tiktok.session, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            cookies_json = json.loads(content)
            for cookie in cookies_json:
                if cookie.get("name") == "sessionid" and "tiktok" in cookie.get(
                    "domain", ""
                ):
                    session_id = cookie.get("value", "")
                    break
        except Exception:
            for line in content.splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split("\t")
                if (
                    len(parts) >= 7
                    and "tiktok.com" in parts[0]
                    and parts[5] == "sessionid"
                ):
                    session_id = parts[6].strip()
                    break

        if not session_id:
            return False, "Tidak ditemukan cookie sessionid di dalam file tersebut."

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        cookies = {"sessionid": session_id}

        resp = requests.get(
            "https://www.tiktok.com/passport/web/account/info/",
            cookies=cookies,
            headers=headers,
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("data", {}).get("user_id") or data.get("message") == "success":
                return True, "Session ID TikTok di dalam file valid dan aktif."
            else:
                return False, "Session ID tidak valid atau sudah expired."

        return False, f"Gagal mengecek session (HTTP {resp.status_code})."
    except Exception as e:
        logger.error(f"Error check_tiktok_auth: {e}")
        return False, f"Gagal menghubungi server TikTok: {str(e)}"


def check_instagram_auth() -> tuple[bool, str]:
    if not config.instagram.session or not os.path.exists(config.instagram.session):
        return False, "File cookie Instagram belum diisi atau tidak ditemukan."

    try:
        session_id = ""
        with open(config.instagram.session, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            cookies_json = json.loads(content)
            for cookie in cookies_json:
                if cookie.get("name") == "sessionid" and "instagram" in cookie.get(
                    "domain", ""
                ):
                    session_id = cookie.get("value", "")
                    break
        except Exception:
            for line in content.splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split("\t")
                if (
                    len(parts) >= 7
                    and "instagram.com" in parts[0]
                    and parts[5] == "sessionid"
                ):
                    session_id = parts[6].strip()
                    break

        if not session_id:
            return False, "Tidak ditemukan cookie sessionid di dalam file tersebut."

        from instagrapi import Client

        cl = Client()
        if cl.login_by_sessionid(session_id):
            return True, "Session ID Instagram valid dan aktif."
        return False, "Session ID tidak valid atau sudah expired."
    except Exception as e:
        logger.error(f"Error check_instagram_auth: {e}")
        return False, f"Gagal login ke Instagram via sessionid: {str(e)}"
