import json
import os
from typing import Any, Dict

from core.uploaders.base import BaseUploader, UploadResult


class InstagramUploader:
    def __init__(self):
        self.platform_name = "Instagram Reels"

    def upload(
        self, file_path: str, metadata: Dict[str, Any], event_hook=None
    ) -> UploadResult:
        from core.config import config
        from core.logger import log as logger

        try:
            from instagrapi import Client
        except ImportError:
            return UploadResult(
                False,
                self.platform_name,
                error_msg="Modul instagrapi belum diinstal. Jalankan: pip install instagrapi",
            )

        if not config.instagram.session or not os.path.exists(config.instagram.session):
            return UploadResult(
                False,
                self.platform_name,
                error_msg="File cookie Instagram belum diisi atau tidak ditemukan.",
            )

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
                return UploadResult(
                    False,
                    self.platform_name,
                    error_msg="Tidak ditemukan cookie sessionid di dalam file tersebut.",
                )

            title = metadata.get("title", "")
            description = metadata.get("description", "")
            tags_raw = metadata.get("tags", "")
            if isinstance(tags_raw, list):
                tags_str = " ".join(
                    [f"#{t.strip().replace('#', '')}" for t in tags_raw if t.strip()]
                )
            else:
                tags_str = " ".join(
                    [
                        f"#{t.strip().replace('#', '')}"
                        for t in tags_raw.split()
                        if t.strip()
                    ]
                )

            parts = []
            if title and title not in description:
                parts.append(title)
            if description:
                parts.append(description)
            if tags_str and tags_str not in description:
                parts.append(tags_str)

            caption = "\n\n".join(parts).strip()

            logger.info(f"[Instagram] Memulai login via sessionid...")

            cl = Client()
            cl.login_by_sessionid(session_id)

            logger.info(f"[Instagram] Berhasil login. Memulai upload Reels...")
            logger.info(f"Mengunggah ke Instagram: {file_path}, caption: {caption}")

            thumb_path = metadata.get("thumbnail_path", f"{file_path}.jpg")
            if not os.path.exists(thumb_path):
                import subprocess

                try:
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-y",
                            "-hide_banner",
                            "-loglevel",
                            "error",
                            "-ss",
                            "00:00:01",
                            "-i",
                            file_path,
                            "-vframes",
                            "1",
                            "-q:v",
                            "2",
                            thumb_path,
                        ],
                        check=True,
                    )
                except Exception as e:
                    logger.warning(f"Gagal generate thumbnail dengan ffmpeg: {e}")

            from pathlib import Path

            kwargs = {}
            if os.path.exists(thumb_path):
                kwargs["thumbnail"] = Path(thumb_path)

            media = cl.clip_upload(Path(file_path), caption=caption, **kwargs)

            if not media:
                err_msg = f"Gagal upload video ke Instagram Reels."
                logger.error(f"[Instagram] ❌ {err_msg}")
                logger.error(err_msg)
                return UploadResult(False, self.platform_name, error_msg=err_msg)

            # Save updated cookies using instagrapi format
            try:
                new_cookies = []
                for name, value in cl.get_settings().get("cookies", {}).items():
                    new_cookies.append(
                        {
                            "name": name,
                            "value": value,
                            "domain": ".instagram.com",
                            "path": "/",
                        }
                    )
                from core.utils import write_json

                if write_json(config.instagram.session, new_cookies, indent=2):
                    logger.info(
                        "[Instagram] Cookie berhasil diperbarui secara otomatis."
                    )
            except Exception as e:
                logger.warning(f"Gagal memperbarui cookie Instagram: {e}")

            media_url = f"https://www.instagram.com/reel/{media.code}/"
            logger.info(f"[Instagram] ✅ Upload berhasil! {media_url}")
            return UploadResult(True, self.platform_name, url=media_url)

        except Exception as e:
            logger.error(f"Instagram Upload error: {str(e)}", exc_info=True)
            return UploadResult(
                False,
                self.platform_name,
                error_msg=f"Gagal upload ke Instagram: {str(e)}",
            )

    def close(self):
        pass
