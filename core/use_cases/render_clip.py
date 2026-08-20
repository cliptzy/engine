import os
from typing import Any, Callable, Dict, Optional

from core.config import config
from core.interfaces import ProgressReporter
from core.logger import log
from core.processor import render_single_clip


class RenderClipUseCase:
    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter

    def execute(
        self, payload: Dict[str, Any], is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes the Phase 2 (Rendering) pipeline based on settings payload.
        """
        video_id = payload.get("video_id")
        if not video_id:
            raise ValueError("video_id tidak boleh kosong")

        from core.interfaces import create_reporter_hook

        event_hook = create_reporter_hook(self.reporter)

        crop = payload.get("crop") or "default"

        job_dir = os.path.join("clips", video_id)
        if not os.path.exists(job_dir):
            raise ValueError(f"Project directory tidak ditemukan: {job_dir}")

        use_subtitle = bool(payload.get("subtitle", True))

        targets = payload.get("segments", [])
        if not targets:
            raise ValueError("Tidak ada segmen (klip) yang dipilih untuk dirender")

        event_hook("total_targets", len(targets))

        success_count = 0
        outputs = []

        import concurrent.futures
        import threading

        success_lock = threading.Lock()

        def process_target(idx, item):
            nonlocal success_count
            clip_idx = item.get("original_index")
            if clip_idx is None:
                clip_idx = idx
            else:
                clip_idx = int(clip_idx)

            if is_cancelled and is_cancelled():
                log.info("[CANCEL] Proses render dibatalkan oleh pengguna.")
                return None

            event_hook(
                "stage",
                {
                    "stage": "start_render",
                    "clip_index": clip_idx,
                    "total": len(targets),
                },
            )

            ok_clip = render_single_clip(
                job_dir=job_dir,
                index=clip_idx,
                item=item,
                use_subtitle=use_subtitle,
                event_hook=event_hook,
            )

            clip_output = None
            if ok_clip:
                with success_lock:
                    success_count += 1
                clip_path = os.path.join(job_dir, f"clip_{clip_idx}.mp4")
                if os.path.exists(clip_path):
                    from core.processing.thumbnail import generate_thumbnail
                    from core.utils import read_json
                    thumb_path = os.path.join(job_dir, f"clip_{clip_idx}_thumbnail.jpg")
                    meta_file = os.path.join(job_dir, f"metadata_{clip_idx}.json")
                    clip_meta = read_json(meta_file) if os.path.exists(meta_file) else {}
                    generate_thumbnail(clip_path, thumb_path, metadata=clip_meta)

                    clip_output = {
                        "name": f"clip_{clip_idx}.mp4",
                        "path": os.path.abspath(clip_path),
                        "size": os.path.getsize(clip_path),
                        "thumbnail": os.path.abspath(thumb_path) if os.path.exists(thumb_path) else None
                    }
                    with success_lock:
                        outputs.append(clip_output)

            event_hook(
                "stage",
                {
                    "stage": "done_render",
                    "clip_index": clip_idx,
                    "success": success_count,
                    "outputs": outputs,
                },
            )
            return clip_output

        max_workers = getattr(config, "max_workers", 2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_target, idx, item)
                for idx, item in enumerate(targets, start=1)
            ]
            for future in concurrent.futures.as_completed(futures):
                if is_cancelled and is_cancelled():
                    break
                try:
                    future.result()
                except Exception as e:
                    log.error(f"Error rendering clip: {e}")

        if self.reporter:
            self.reporter.on_finished(outputs)

        return {
            "video_id": video_id,
            "total": len(targets),
            "success": success_count,
            "output_dir": os.path.abspath(job_dir),
            "outputs": outputs,
        }
