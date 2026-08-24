import concurrent.futures
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.config import config
from core.interfaces import ProgressReporter, create_reporter_hook
from core.logger import log
from core.processing.numbering import generate_numbering_card
from core.utils import check_dependencies


@dataclass
class CompilationItem:
    """A single item in the compilation."""

    file_path: str  # Path to local video file
    moment_name: str  # Title/TTS text for this moment
    number: int = 0  # Ranking number (assigned automatically from ordering)


class CompileVideoUseCase:
    """
    Orchestrates the full compilation pipeline:
    1. Process each local video file (crop, subtitle, effects)
    2. Generate a numbering card for each item
    3. Concatenate all segments: [card_N + clip_N] + ... + [card_1 + clip_1]
    4. Optionally prepend intro and append outro
    """

    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter

    def execute(
        self,
        items: List[CompilationItem],
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the compilation pipeline.

        :param items: List of CompilationItem (file_path + moment_name).
        :param is_cancelled: Callable that returns True if the user cancelled.
        :return: Dict with success count, output path, etc.
        """
        if not items:
            raise ValueError("Daftar video kompilasi tidak boleh kosong")

        for item in items:
            if not os.path.isfile(item.file_path):
                raise FileNotFoundError(
                    f"File video tidak ditemukan: {item.file_path}"
                )
            if not item.moment_name.strip():
                raise ValueError(
                    f"Nama momen tidak boleh kosong untuk: {item.file_path}"
                )

        event_hook = create_reporter_hook(self.reporter)

        # Check FFmpeg dependency
        ok = check_dependencies(
            install_whisper=config.compilation.use_subtitle,
            skip_update_ytdlp=True,
            fatal=False,
            whisper_model=config.subtitle.whisper_model,
        )
        if not ok:
            raise RuntimeError("FFmpeg tidak ditemukan di sistem")

        # Setup job directory
        job_id = f"compilation_{int(time.time())}"
        job_dir = os.path.join("clips", job_id)
        os.makedirs(job_dir, exist_ok=True)
        config.job_dir = job_dir

        # Assign numbers based on ordering
        ordering = config.compilation.ordering
        total = len(items)
        for idx, item in enumerate(items):
            if ordering == "countdown":
                item.number = total - idx
            else:  # countup
                item.number = idx + 1

        event_hook("total_targets", total)

        # --- Phase 1: Process each clip in parallel ---
        log.info(
            f"Memulai kompilasi {total} klip (ordering: {ordering})..."
        )

        success_count = 0
        success_lock = threading.Lock()
        clip_outputs: Dict[int, str] = {}  # number -> clip output path

        def process_item(item: CompilationItem) -> Optional[str]:
            nonlocal success_count
            if is_cancelled and is_cancelled():
                log.info("[CANCEL] Kompilasi dibatalkan oleh pengguna.")
                return None

            event_hook(
                "stage",
                {
                    "stage": "start_clip",
                    "clip_index": item.number,
                    "total": total,
                },
            )

            clip_output = self._process_single_item(
                item, job_dir, event_hook
            )

            if clip_output:
                with success_lock:
                    success_count += 1
                    clip_outputs[item.number] = clip_output

            event_hook(
                "stage",
                {
                    "stage": "done_clip",
                    "clip_index": item.number,
                    "success": success_count,
                },
            )
            return clip_output

        max_workers = getattr(config, "max_workers", 2)
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:
            futures = {
                executor.submit(process_item, item): item for item in items
            }
            for future in concurrent.futures.as_completed(futures):
                if is_cancelled and is_cancelled():
                    break
                try:
                    future.result()
                except Exception as e:
                    item = futures[future]
                    log.error(
                        f"Error processing clip #{item.number} "
                        f"({item.moment_name}): {e}"
                    )

        if is_cancelled and is_cancelled():
            return {"success": 0, "outputs": []}

        if success_count == 0:
            raise RuntimeError("Tidak ada klip yang berhasil diproses")

        # --- Phase 2: Generate numbering cards ---
        log.info("Generating numbering cards...")
        event_hook("stage", {"stage": "numbering_cards"})

        card_outputs: Dict[int, str] = {}  # number -> card path
        numbering_duration = config.compilation.numbering_duration

        for item in items:
            if is_cancelled and is_cancelled():
                break
            if item.number not in clip_outputs:
                continue

            card_path = os.path.join(
                job_dir, f"card_{item.number}.mp4"
            )
            try:
                generate_numbering_card(
                    number=item.number,
                    moment_name=item.moment_name,
                    output_path=card_path,
                    duration=numbering_duration,
                    event_hook=event_hook,
                )
                card_outputs[item.number] = card_path
            except Exception as e:
                log.error(
                    f"Failed to generate card #{item.number}: {e}"
                )

        # --- Phase 3: Concat all segments ---
        log.info("Menggabungkan semua segmen kompilasi...")
        event_hook("stage", {"stage": "merging"})

        # Build ordered list of files to concat
        if ordering == "countdown":
            ordered_numbers = sorted(clip_outputs.keys(), reverse=True)
        else:
            ordered_numbers = sorted(clip_outputs.keys())

        concat_list_path = os.path.join(job_dir, "compilation_concat.txt")
        concat_segments: List[str] = []

        # Add intro if configured
        if config.intro_video and os.path.isfile(config.intro_video):
            concat_segments.append(config.intro_video)

        for num in ordered_numbers:
            # Add numbering card
            if num in card_outputs and os.path.exists(card_outputs[num]):
                concat_segments.append(card_outputs[num])
            # Add clip
            if num in clip_outputs and os.path.exists(clip_outputs[num]):
                concat_segments.append(clip_outputs[num])

        # Add outro if configured
        if config.outro_video and os.path.isfile(config.outro_video):
            concat_segments.append(config.outro_video)

        if len(concat_segments) < 2:
            raise RuntimeError(
                "Tidak cukup segmen untuk membuat kompilasi"
            )

        compilation_output = os.path.join(job_dir, "compilation.mp4")

        # Use FFmpeg concat demuxer with re-encoding to handle
        # different codecs/resolutions across segments
        self._concat_with_reencode(
            concat_segments, compilation_output, event_hook
        )
        
        # --- Phase 3: AI Metadata & Thumbnail ---
        event_hook("stage", {"stage": "ai_metadata"})
        
        comp_metadata = {}
        if config.ai.provider and config.ai.provider != "none":
            from core.ai.detector import ai_detector
            
            # Gabungkan nama momen menjadi satu teks untuk context AI
            moment_texts = "\n".join([f"#{item.number} {item.moment_name}" for item in items])
            ai_prompt = f"Ini adalah video kompilasi momen lucu/menarik. Berikut adalah daftar momen yang ada di video:\n{moment_texts}\n\nBuat judul yang viral, deskripsi menarik, dan hashtag relevan untuk kompilasi ini."
            
            try:
                log.info("Generating AI metadata for compilation...")
                import dataclasses
                comp_metadata = ai_detector.generate_metadata(
                    clip_text=ai_prompt,
                    youtube_title="Video Kompilasi",
                    channel_name="",
                    youtube_url="",
                    ai_config=dataclasses.asdict(config.ai),
                    language=config.tts_language or "Indonesia",
                    event_hook=event_hook
                )
                
                # Save metadata to json
                from core.utils import write_json
                meta_path = os.path.join(job_dir, "metadata.json")
                write_json(meta_path, comp_metadata, indent=4)
                log.info(f"Metadata saved to {meta_path}")
            except Exception as e:
                log.error(f"Gagal generate AI metadata kompilasi: {e}")

        # Generate Thumbnail Collage
        event_hook("stage", {"stage": "thumbnail"})
        thumbnail_output = os.path.join(job_dir, "thumbnail.jpg")
        try:
            from core.processing.thumbnail import generate_compilation_thumbnail
            # Ambil semua file klip yang berhasil
            clip_paths = [clip_outputs[k] for k in ordered_numbers if k in clip_outputs]
            if clip_paths:
                log.info("Generating collage thumbnail for compilation...")
                generate_compilation_thumbnail(clip_paths, thumbnail_output, event_hook=event_hook)
        except Exception as e:
            log.error(f"Gagal generate thumbnail kompilasi: {e}")

        outputs = []
        if os.path.exists(compilation_output):
            out_info = {
                "name": "compilation.mp4",
                "path": os.path.abspath(compilation_output),
                "size": os.path.getsize(compilation_output),
            }
            if comp_metadata:
                out_info["metadata"] = comp_metadata
            if os.path.exists(thumbnail_output):
                out_info["thumbnail"] = os.path.abspath(thumbnail_output)
                
            outputs.append(out_info)
            log.info(
                f"Kompilasi berhasil: {os.path.abspath(compilation_output)}"
            )

        if self.reporter:
            self.reporter.on_finished(outputs)

        return {
            "total": total,
            "success": success_count,
            "output_dir": os.path.abspath(job_dir),
            "outputs": outputs,
        }

    def _process_single_item(
        self,
        item: CompilationItem,
        job_dir: str,
        event_hook: Callable[[str, Any], None],
    ) -> Optional[str]:
        """
        Processes a single compilation item: crop + subtitle + effects.
        Reuses process_single_clip() from core/processor.py.
        """
        from core.processor import process_single_clip

        # Get total duration of the local video
        total_duration = self._get_video_duration(item.file_path)
        if total_duration <= 0:
            log.error(
                f"Gagal mendapatkan durasi video: {item.file_path}"
            )
            return None

        # Process the entire video file as one segment
        segment = {
            "start": 0.0,
            "duration": float(total_duration),
            "score": 1.0,
        }

        crop_mode = config.compilation.crop_mode or config.crop_mode
        use_subtitle = config.compilation.use_subtitle

        # Use a unique video_id based on the item number to isolate files
        video_id = os.path.basename(job_dir)
        clip_index = item.number

        ok = process_single_clip(
            video_id=video_id,
            item=segment,
            index=clip_index,
            total_duration=int(total_duration),
            crop_mode=crop_mode,
            use_subtitle=use_subtitle,
            event_hook=event_hook,
            source_url=item.file_path,
        )

        if not ok:
            return None

        clip_path = os.path.join(job_dir, f"clip_{clip_index}.mp4")
        if os.path.exists(clip_path):
            return clip_path

        return None

    def _get_video_duration(self, file_path: str) -> float:
        """Gets the duration of a video file using ffprobe."""
        try:
            res = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    file_path,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return float(res.stdout.strip())
        except Exception as e:
            log.error(f"ffprobe failed for {file_path}: {e}")
            return 0.0

    def _concat_with_reencode(
        self,
        segments: List[str],
        output_path: str,
        event_hook: Callable[[str, Any], None],
    ) -> None:
        """
        Concatenates multiple video files with re-encoding to ensure
        consistent resolution and codec. Uses FFmpeg filter_complex concat.
        """
        from core.processing.utils import (
            get_video_codec_args,
            run_command_with_logging,
        )

        out_w = config.out_width or 720
        out_h = config.out_height or 1280
        scale_filter = (
            f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
            f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )

        inputs: List[str] = []
        filter_parts: List[str] = []
        concat_labels = ""

        for i, seg in enumerate(segments):
            inputs.extend(["-i", seg])
            filter_parts.append(
                f"[{i}:v:0]{scale_filter}[v{i}]; "
                f"[{i}:a:0]aresample=async=1[a{i}]"
            )
            concat_labels += f"[v{i}][a{i}]"

        n = len(segments)
        filter_complex = "; ".join(filter_parts)
        filter_complex += f"; {concat_labels}concat=n={n}:v=1:a=1[outv][outa]"

        cmd = (
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "info"]
            + inputs
            + [
                "-filter_complex",
                filter_complex,
                "-map",
                "[outv]",
                "-map",
                "[outa]",
            ]
            + get_video_codec_args()
            + ["-c:a", "aac", "-b:a", "128k", output_path]
        )

        run_command_with_logging(cmd, event_hook, prefix="[ffmpeg-compilation]")
