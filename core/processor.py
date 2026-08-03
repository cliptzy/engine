import os
import sys
import subprocess
from typing import Dict, Any, Callable, Optional, cast

from core.logger import log
from core.config import config

from core.subtitle import generate_subtitle
from core.processing.utils import run_command_with_logging, cleanup_temp_files
from core.processing.cropper import build_crop_command
from core.processing.subtitle import burn_subtitle_and_highlight
from core.processing.stacker import generate_intro, stack_and_concat

def process_single_clip(
    video_id: str,
    item: Dict[str, Any],
    index: int,
    total_duration: int,
    crop_mode: str = "default",
    use_subtitle: bool = False,
    event_hook: Optional[Callable[[str, Any], None]] = None
) -> bool:
    """
    Downloads, crops, and exports a single vertical clip based on a heatmap segment.
    """
    start_original = item["start"]
    end_original = item["start"] + item["duration"]

    start = max(0, start_original - config.padding)
    end = min(end_original + config.padding, total_duration)

    if end - start < 3:
        log.warning(f"Clip {index} is too short after padding. Skipping.")
        return False

    start_str = str(int(start))
    end_str = str(int(end))
    base_name = f"clip_{index}_{start_str}_{end_str}_{crop_mode}"

    temp_file = os.path.join(config.job_dir, f"{base_name}_raw.mkv")
    cropped_file = os.path.join(config.job_dir, f"{base_name}_nosub.mp4")
    subtitle_file = os.path.join(config.job_dir, f"{base_name}.ass")
    subbed_file = os.path.join(config.job_dir, f"{base_name}_subbed.mp4")
    output_file = os.path.join(config.job_dir, f"clip_{index}.mp4")

    log.info(f"[Clip {index}] Processing segment ({int(start)}s - {int(end)}s, padding {config.padding}s)")
    
    if callable(event_hook):
        try:
            event_hook("stage", {"stage": "download", "clip_index": index})
        except Exception as e:
            log.debug(f"Event hook error: {e}")

    import yt_dlp
    from yt_dlp.utils import download_range_func

    class YtDlpLogger:
        def __init__(self, hook, prefix):
            self.hook = hook
            self.prefix = prefix
        def debug(self, msg):
            if self.hook and not msg.startswith('[download]'):
                self.hook("log", f"{self.prefix} {msg}")
        def info(self, msg):
            if self.hook:
                self.hook("log", f"{self.prefix} {msg}")
        def warning(self, msg):
            if self.hook:
                self.hook("log", f"{self.prefix} [WARNING] {msg}")
        def error(self, msg):
            if self.hook:
                self.hook("log", f"{self.prefix} [ERROR] {msg}")

    def yt_dlp_progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '').strip()
            speed = d.get('_speed_str', '').strip()
            eta = d.get('_eta_str', '').strip()
            total = d.get('_total_bytes_estimate_str', d.get('_total_bytes_str', ''))
            msg = f"[download] {percent} of {total} at {speed} ETA {eta}"
            if callable(event_hook):
                event_hook("log", f"[yt-dlp] {msg}")

    ydl_opts: dict[str, Any] = {
        'force_ipv4': True,
        'remote_components': ['ejs:github'],
        'no_warnings': False,
        'merge_output_format': 'mkv',
        'format': 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b',
        'outtmpl': temp_file,
        'download_ranges': download_range_func(cast(Any, None), [(start, end)]),
        'force_keyframes_at_cuts': True,
        'logger': YtDlpLogger(event_hook, "[yt-dlp]"),
        'progress_hooks': [yt_dlp_progress_hook],
    }
    
    ydl_opts_fallback: dict[str, Any] = {
        'force_ipv4': True,
        'remote_components': ['ejs:github'],
        'no_warnings': False,
        'merge_output_format': 'mkv',
        'format': 'bv*+ba/b',
        'outtmpl': temp_file,
        'download_ranges': download_range_func(cast(Any, None), [(start, end)]),
        'force_keyframes_at_cuts': True,
        'logger': YtDlpLogger(event_hook, "[yt-dlp-fallback]"),
        'progress_hooks': [yt_dlp_progress_hook],
    }
    
    if config.youtube.session and os.path.exists(config.youtube.session):
        ydl_opts['cookiefile'] = config.youtube.session
        ydl_opts_fallback['cookiefile'] = config.youtube.session

    try:
        if not os.path.exists(cropped_file):
            try:
                if callable(event_hook):
                    event_hook("log", f"[yt-dlp] Downloading segment: {start}s - {end}s\n")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
                    ydl.download([f"https://youtu.be/{video_id}"])
            except Exception as e:
                log.info(f"Retrying download with fallback format for clip {index}: {e}")
                if callable(event_hook):
                    event_hook("log", f"[yt-dlp] Retrying download with fallback format...\n")
                with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl: # type: ignore
                    ydl.download([f"https://youtu.be/{video_id}"])

            if not os.path.exists(temp_file):
                log.error(f"Failed to download video segment for clip {index}.")
                return False

            out_w, out_h = config.out_width, config.out_height
            
            cx_norm, cy_norm = 0.5, 0.5
            if crop_mode in ["split_face", "full_face"]:
                if callable(event_hook):
                    try:
                        event_hook("stage", {"stage": "face_track", "clip_index": index})
                        event_hook("log", f"Detecting face position for dynamic crop in clip {index}...")
                    except Exception as e:
                        pass
                try:
                    from core.face_tracker import get_dominant_face_normalized_center
                    res_cx, res_cy = get_dominant_face_normalized_center(temp_file)
                    if res_cx is None or res_cy is None:
                        log.info(f"Clip {index}: No face detected, falling back to full mode.")
                        if callable(event_hook):
                            try:
                                event_hook("log", f"Wajah tidak terdeteksi pada klip {index}, beralih ke mode Full (fallback).")
                            except Exception: pass
                        crop_mode = "full"
                    else:
                        cx_norm, cy_norm = res_cx, res_cy
                except Exception as e:
                    log.warning(f"Face tracking module error: {e}")
                    crop_mode = "full"
                    
            cmd_crop = build_crop_command(temp_file, cropped_file, crop_mode, out_w, out_h, cx_norm, cy_norm)

            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "crop", "clip_index": index})
                except Exception as e:
                    log.debug(f"Event hook error: {e}")
                    
            log.info(f"Cropping video for clip {index}...")
            run_command_with_logging(cmd_crop, event_hook, prefix="[ffmpeg-crop]")
            
            if os.path.exists(temp_file):
                os.remove(temp_file)
        else:
            log.info(f"Found existing cached nosub clip for {index}")

        current_clip = cropped_file

        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "subtitle", "clip_index": index})
            except Exception as e:
                log.debug(f"Event hook error: {e}")
                
        log.info(f"Generating subtitle for clip {index} (for metadata/burn)...")
        subtitle_generated, transcript_text = generate_subtitle(cropped_file, subtitle_file, config.subtitle.whisper_model, event_hook=event_hook)
        if not subtitle_generated:
            log.warning("Subtitle generation failed, continuing without subtitle...")

        # --- AI Metadata Generation ---
        metadata = {}
        if transcript_text:
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "ai_metadata", "clip_index": index})
                    event_hook("log", f"Generating metadata (Title, Desc, Highlight) via AI for clip {index}...")
                except Exception: pass
                
            from core.utils import get_preview_data
            preview_data = get_preview_data()
            youtube_title = preview_data.get("title", "Unknown")
            channel_name = preview_data.get("uploader", "Unknown")
            youtube_url = preview_data.get("webpage_url", f"https://youtu.be/{video_id}")
            
            ai_config = config.to_dict()
            from core.ai.detector import ai_detector
            metadata = ai_detector.generate_metadata(
                clip_text=transcript_text,
                youtube_title=youtube_title,
                channel_name=channel_name,
                youtube_url=youtube_url,
                ai_config=ai_config,
                event_hook=event_hook,
                language=preview_data.get("language", "Indonesia")
            )
            
            if metadata:
                metadata_file = os.path.join(config.job_dir, f"metadata_{index}.json")
                try:
                    from core.utils import write_json
                    write_json(metadata_file, metadata, indent=2)
                    if callable(event_hook):
                        event_hook("log", f"Metadata saved to {metadata_file}")
                except Exception as e:
                    log.warning(f"Failed to save metadata for clip {index}: {e}")

        # --- Subtitle & Highlight Burning Logic ---
        current_clip = burn_subtitle_and_highlight(
            cropped_file, subbed_file, subtitle_file, metadata,
            start, end, index, use_subtitle, subtitle_generated, event_hook
        )

        # Process Intro / Outro Concatenation
        intro_to_use = generate_intro(index, metadata, event_hook)
        
        stack_and_concat(current_clip, output_file, intro_to_use, index, event_hook)

        log.info(f"Clip {index} successfully generated.")
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "done_clip", "clip_index": index})
            except Exception as e:
                log.debug(f"Event hook error: {e}")
        return True

    except subprocess.CalledProcessError as e:
        cleanup_temp_files([temp_file])
        log.error(f"Failed to generate clip {index}. Subprocess error.")
        return False
    except Exception as e:
        cleanup_temp_files([temp_file])
        log.error(f"Failed to generate clip {index}.")
        log.exception(f"Exception: {str(e)}")
        return False
