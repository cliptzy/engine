import datetime
import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional

from core.config import config
from core.interfaces import ProgressReporter
from core.logger import log
from core.uploaders.factory import UploaderFactory


class BatchUploadUseCase:
    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter

    def _adjust_for_quiet_hours(self, dt: datetime.datetime) -> tuple[datetime.datetime, bool]:
        # Jam sepi: 00:00 s/d 05:59 (WIB / UTC+7)
        if dt.hour < 6:
            adjusted_dt = dt.replace(hour=6, minute=0, second=0, microsecond=0)
            return adjusted_dt, True
        return dt, False

    def execute(
        self,
        current_project_dir: str,
        selected_clips: List[Dict[str, Any]],
        platforms: List[str],
        interval_hours: float,
        schedule_date: Optional[datetime.date] = None,
        schedule_time: Optional[datetime.time] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> bool:
        if not selected_clips or not platforms:
            return False

        # Load metadata for selected clips
        metadata_dict = {}
        for clip_item in selected_clips:
            clip_path = clip_item["path"]
            bname = os.path.basename(clip_path)
            m = re.match(r"^clip_(\d+)\.mp4$", bname)
            if m:
                idx = m.group(1)
            elif bname == "merged.mp4":
                idx = "merge"
            elif bname == "final_brainrot.mp4":
                idx = "brainrot"
            else:
                idx = ""

            meta = {"title": bname, "tags": ""}
            if idx:
                meta_path = os.path.join(current_project_dir, f"metadata_{idx}.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f_meta:
                            saved_meta = json.load(f_meta)
                            if saved_meta:
                                tags_raw = saved_meta.get("tags", "")
                                if isinstance(tags_raw, list):
                                    saved_meta["tags"] = " ".join(tags_raw)
                                meta.update(saved_meta)
                    except Exception as e:
                        log.error(f"Failed to load metadata {meta_path}: {e}")

            default_tags = (config.default_hashtags or "").split()
            meta_tags = meta.get("tags", "").split()
            for dt in default_tags:
                if dt not in meta_tags:
                    meta_tags.append(dt)
            meta["tags"] = " ".join(meta_tags)
            metadata_dict[clip_path] = meta

        total_tasks = len(selected_clips) * len(platforms)
        completed = 0

        # Instantiate uploaders
        uploaders = []
        for p in platforms:
            try:
                uploader = UploaderFactory.create(p)
                uploaders.append(uploader)
            except Exception as ex:
                if self.reporter:
                    self.reporter.on_log(f"[UPLOAD] Gagal memuat uploader {p}: {ex}")
                log.error(f"[UPLOAD] Gagal memuat uploader {p}: {ex}")

        if not uploaders:
            return False

        utc7_time = datetime.timezone(datetime.timedelta(hours=7))
        
        if schedule_date:
            s_time = schedule_time or datetime.time(0, 0)
            dt_naive = datetime.datetime.combine(schedule_date, s_time)
            base_time = dt_naive.replace(tzinfo=utc7_time)
        else:
            base_time = datetime.datetime.now(utc7_time) + datetime.timedelta(minutes=30)

        last_publish_time = None

        def hook(kind, data):
            if self.reporter and kind == "log":
                self.reporter.on_log(str(data))

        try:
            for idx_clip, clip_item in enumerate(selected_clips):
                if is_cancelled and is_cancelled():
                    break

                clip = clip_item["path"]
                clip_meta = metadata_dict.get(clip, {})
                clip_name = os.path.basename(clip)

                title_val = clip_meta.get("title", "")
                tags_val = clip_meta.get("tags", "")
                clip_meta["description"] = f"{title_val}\n\n{tags_val}".strip()

                is_scheduled = interval_hours > 0 or schedule_date is not None
                if is_scheduled:
                    publish_time = base_time + datetime.timedelta(hours=interval_hours * idx_clip)
                else:
                    publish_time = base_time

                orig_publish_time = publish_time
                publish_time, adjusted = self._adjust_for_quiet_hours(publish_time)

                if last_publish_time is not None and interval_hours > 0:
                    min_publish_time = last_publish_time + datetime.timedelta(hours=interval_hours)
                    if publish_time < min_publish_time:
                        publish_time = min_publish_time

                if publish_time != orig_publish_time:
                    msg = f"[UPLOAD] ⚠️ Jadwal publikasi untuk {clip_name} digeser ke {publish_time.strftime('%d-%m-%Y %H:%M WIB')} (semula {orig_publish_time.strftime('%H:%M WIB')}) karena masuk jam sepi atau menyesuaikan antrean."
                    if self.reporter:
                        self.reporter.on_log(msg)
                    log.info(msg)

                last_publish_time = publish_time

                if is_scheduled or publish_time != orig_publish_time:
                    publish_time_utc = publish_time.astimezone(datetime.timezone.utc)
                    clip_meta["publish_at"] = publish_time_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

                for uploader in uploaders:
                    if is_cancelled and is_cancelled():
                        break

                    log_msg = f"[UPLOAD] Memulai upload {clip_name} ke {uploader.platform_name}..."
                    if self.reporter:
                        self.reporter.on_log(log_msg)
                        self.reporter.on_progress(f"Mengunggah {clip_name} ke {uploader.platform_name}...", completed, total_tasks)

                    # Generate dynamic thumbnail if not present
                    from core.processing.thumbnail import generate_thumbnail
                    thumbnail_path = os.path.splitext(clip)[0] + "_thumbnail.jpg"
                    if generate_thumbnail(clip, thumbnail_path, clip_meta):
                        clip_meta["thumbnail_path"] = thumbnail_path

                    try:
                        result = uploader.upload(clip, clip_meta, event_hook=hook)
                        if result.success:
                            if self.reporter:
                                self.reporter.on_log(f"[UPLOAD] ✅ Sukses upload ke {uploader.platform_name}: {result.url}")
                        else:
                            if self.reporter:
                                self.reporter.on_log(f"[UPLOAD] ❌ Gagal upload ke {uploader.platform_name}: {result.error_msg}")
                    except Exception as ex_upload:
                        log.error(f"Uploader exception: {ex_upload}")
                        if self.reporter:
                            self.reporter.on_log(f"[UPLOAD] ❌ Gagal upload ke {uploader.platform_name}: {ex_upload}")

                    completed += 1
                    if self.reporter:
                        self.reporter.on_progress("Mengunggah selesai", completed, total_tasks)

                    time.sleep(2.0)
        finally:
            for uploader in uploaders:
                if hasattr(uploader, "close"):
                    try:
                        uploader.close()
                    except Exception as e_close:
                        log.error(f"Gagal menutup uploader {uploader.platform_name}: {e_close}")

        return True
