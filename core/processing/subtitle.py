import os
import subprocess
from typing import Optional, Callable
from core.logger import log
from core.config import config
from core.processing.utils import get_video_codec_args, run_command_with_logging

def burn_subtitle_and_highlight(
    cropped_file: str,
    subbed_file: str,
    subtitle_file: str,
    metadata: dict,
    start: float,
    end: float,
    index: int,
    use_subtitle: bool,
    subtitle_generated: bool,
    event_hook: Optional[Callable] = None
) -> str:
    # --- Subtitle & Highlight Burning Logic ---
    has_highlight = config.ai.use_highlight and metadata and metadata.get("highlight")
    should_burn = (use_subtitle and subtitle_generated) or has_highlight
    
    current_clip = cropped_file

    if should_burn and os.path.exists(subtitle_file):
        if has_highlight:
            if callable(event_hook):
                try:
                    event_hook("log", f"Adding Highlight text to subtitle file for clip {index}...")
                except Exception: pass
            try:
                from core.subtitle import format_ass_time
                highlight_val = metadata.get("highlight")
                highlight_text = highlight_val.upper() if highlight_val else None
                end_ass = format_ass_time(end - start)
                
                # If subtitle is disabled but highlight is enabled, we need to remove the regular dialogue events
                if not use_subtitle:
                    with open(subtitle_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    with open(subtitle_file, "w", encoding="utf-8") as f:
                        for line in lines:
                            if not line.startswith("Dialogue:"):
                                f.write(line)
                                
                # Append Highlight event
                highlight_event = f"Dialogue: 1,0:00:00.00,{end_ass},Default,,0,0,100,,{{\\an8\\fs90\\c&H00FFFF&\\b1\\3c&H000000&\\3a&H80&\\bord5}}{highlight_text}\n"
                with open(subtitle_file, "a", encoding="utf-8") as f:
                    f.write(highlight_event)
            except Exception as e:
                log.warning(f"Failed to append highlight to subtitle: {e}")

        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "burn_subtitle", "clip_index": index})
            except Exception as e:
                log.debug(f"Event hook error: {e}")
                
        log.info(f"Burning subtitle/highlight to video for clip {index}...")
        fontsdir_arg = ""
        if config.subtitle.fonts_dir and os.path.isdir(config.subtitle.fonts_dir):
            fontsdir_fwd = config.subtitle.fonts_dir.replace("\\", "/")
            fontsdir_arg = f":fontsdir='{fontsdir_fwd}'"
        
        subtitle_file_fwd = subtitle_file.replace("\\", "/")
        cmd_subtitle = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
            "-i", cropped_file,
            "-vf", f"subtitles=filename='{subtitle_file_fwd}'{fontsdir_arg}",
        ] + get_video_codec_args() + [
            "-c:a", "copy",
            subbed_file
        ]
        
        try:
            run_command_with_logging(cmd_subtitle, event_hook, prefix="[ffmpeg-subtitle]")
            current_clip = subbed_file
        except subprocess.CalledProcessError as e:
            log.warning("FFmpeg subtitle filter failed (likely missing libass). Falling back to non-subbed video.")
            if callable(event_hook):
                try:
                    event_hook("log", "[ffmpeg-subtitle] ERROR: FFmpeg pada sistem ini tidak memiliki filter 'subtitles' (missing libass). Menyimpan video tanpa subtitle.")
                except Exception:
                    pass

    return current_clip
