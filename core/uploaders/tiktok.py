import os
import time
from typing import Any, Dict

from core.uploaders.base import BaseUploader, UploadResult


class TikTokUploader:
    def __init__(self):
        self.platform_name = "TikTok"

    def upload(
        self, file_path: str, metadata: Dict[str, Any], event_hook=None
    ) -> UploadResult:
        from core.config import config
        from core.logger import log as logger

        try:
            from tiktok_uploader.upload import TikTokUploader as TTUploader
        except ImportError:
            return UploadResult(
                False,
                self.platform_name,
                error_msg="Modul tiktok-uploader belum diinstal. Jalankan: pip install tiktok-uploader",
            )

        cookie_path = config.tiktok.session
        if not cookie_path or not os.path.exists(cookie_path):
            return UploadResult(
                False,
                self.platform_name,
                error_msg="File cookie TikTok tidak ditemukan atau path belum diatur.",
            )

        try:
            title = metadata.get("title", "")
            description = metadata.get("description", "")
            tags_raw = metadata.get("tags", "")
            if isinstance(tags_raw, list):
                tags_str = " ".join(
                    [
                        f"#{t.strip().replace('#', '')}"
                        for t in tags_raw
                        if t.strip() and not t.strip().startswith("@")
                    ]
                )
            else:
                tags_str = tags_raw.strip()

            parts = []
            if title and title not in description:
                parts.append(title)
            if description:
                parts.append(description)
            if tags_str and tags_str not in description:
                parts.append(tags_str)

            caption = "\n\n".join(parts).strip()

            logger.info(
                f"[TikTok] Memulai upload menggunakan tiktok-uploader dari file {cookie_path}..."
            )
            logger.info(f"Mengunggah ke TikTok: {file_path}, caption: {caption}")

            import threading

            result_container = {}

            def run_upload():
                try:
                    # Instansiasi uploader di dalam raw thread terisolasi agar Playwright tidak crash
                    # mendeteksi asyncio loop melalui contextvars
                    uploader = TTUploader(cookies=cookie_path, headless=True)

                    import datetime

                    schedule = None
                    if "publish_at" in metadata:
                        try:
                            # metadata["publish_at"] format: "YYYY-MM-DDTHH:MM:SS.000Z" (UTC)
                            # tiktok_uploader expects a naive datetime representing the user's LOCAL timezone
                            time_str = (
                                metadata["publish_at"]
                                .replace(".000Z", "+00:00")
                                .replace("Z", "+00:00")
                            )
                            utc_time = datetime.datetime.fromisoformat(time_str)
                            local_time = utc_time.astimezone()
                            schedule = local_time.replace(tzinfo=None)

                            logger.info(
                                f"[TikTok] Menjadwalkan upload untuk {schedule} (Waktu Lokal)"
                            )
                        except Exception as e:
                            logger.warning(f"Gagal memparsing jadwal: {e}")

                    if schedule:
                        # `tiktok_uploader` upload_video function with schedule
                        success = uploader.upload_video(
                            file_path, description=caption, schedule=schedule
                        )
                    else:
                        success = uploader.upload_video(file_path, description=caption)

                    time.sleep(3)

                    if not success:
                        err_msg = f"Gagal upload video ke TikTok."
                        logger.error(f"[TikTok] ❌ {err_msg}")
                        result_container["result"] = UploadResult(
                            False, self.platform_name, error_msg=err_msg
                        )
                        return

                    # Save updated cookies
                    if (
                        hasattr(uploader, "page")
                        and uploader.page
                        and hasattr(uploader.page, "context")
                    ):
                        try:
                            from tiktok_uploader.auth import save_cookies

                            save_cookies(cookie_path, uploader.page.context.cookies())  # type: ignore
                            logger.info(
                                "[TikTok] Cookie berhasil diperbarui secara otomatis."
                            )
                        except Exception as e:
                            logger.warning(f"Gagal memperbarui cookie TikTok: {e}")

                    uploader.close()
                    logger.info("[TikTok] ✅ Upload berhasil!")
                    result_container["result"] = UploadResult(
                        True, self.platform_name, url="https://www.tiktok.com/profile"
                    )

                except Exception as inner_e:
                    logger.error(
                        f"TikTok Upload inner error: {str(inner_e)}", exc_info=True
                    )
                    result_container["result"] = UploadResult(
                        False,
                        self.platform_name,
                        error_msg=f"Gagal upload ke TikTok: {str(inner_e)}",
                    )

            # Eksekusi fungsi di thread mentah murni tanpa contextvars
            t = threading.Thread(target=run_upload)
            t.start()
            t.join()

            if "result" in result_container:
                return result_container["result"]
            else:
                return UploadResult(
                    False,
                    self.platform_name,
                    error_msg="Unknown error in isolated thread",
                )

        except Exception as e:
            logger.error(f"TikTok Upload error: {str(e)}", exc_info=True)
            return UploadResult(
                False, self.platform_name, error_msg=f"Gagal upload ke TikTok: {str(e)}"
            )

    def close(self):
        # Sudah ditutup di dalam upload()
        pass
