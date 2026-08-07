import os
from typing import Dict, Any, Optional, Callable

from core.logger import log
from core.processor import render_single_clip
from core.interfaces import ProgressReporter

class RenderClipUseCase:
    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter

    def execute(
        self,
        payload: Dict[str, Any],
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes the Phase 2 (Rendering) pipeline based on settings payload.
        """
        video_id = payload.get("video_id")
        if not video_id:
            raise ValueError("video_id tidak boleh kosong")

        def event_hook(event: str, data: Any = None):
            if self.reporter:
                if event == "log":
                    self.reporter.on_log(str(data))
                elif event == "stage":
                    stage = data.get("stage", "")
                    idx = data.get("clip_index", 0)
                    tot = data.get("total", 0)
                    self.reporter.on_progress(stage, idx, tot)
                elif event == "total_targets":
                    self.reporter.on_progress("total_targets", int(data), int(data))

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
        
        for idx, item in enumerate(targets, start=1):
            clip_idx = item.get("original_index")
            if clip_idx is None:
                clip_idx = idx
            else:
                clip_idx = int(clip_idx)

            if is_cancelled and is_cancelled():
                log.info( "[CANCEL] Proses render dibatalkan oleh pengguna.")
                break

            event_hook("stage", {"stage": "start_render", "clip_index": clip_idx, "total": len(targets)})

            ok_clip = render_single_clip(
                job_dir=job_dir,
                index=clip_idx,
                item=item,
                use_subtitle=use_subtitle,
                event_hook=event_hook
            )

            if ok_clip:
                success_count += 1
                clip_path = os.path.join(job_dir, f"clip_{clip_idx}.mp4")
                if os.path.exists(clip_path):
                    outputs.append({
                        "name": f"clip_{clip_idx}.mp4",
                        "path": os.path.abspath(clip_path),
                        "size": os.path.getsize(clip_path)
                    })

            event_hook("stage", {"stage": "done_render", "clip_index": clip_idx, "success": success_count, "outputs": outputs})

        if self.reporter:
            self.reporter.on_finished(outputs)

        return {
            "video_id": video_id,
            "total": len(targets),
            "success": success_count,
            "output_dir": os.path.abspath(job_dir),
            "outputs": outputs
        }
