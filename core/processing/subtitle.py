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
        
        vf_chain = []
        af_chain = []
        
        # 1. Parse enriched_transcript to get effects
        enriched = metadata.get("enriched_transcript", [])
        if isinstance(enriched, list) and len(enriched) > 0:
            current_emotion = None
            start_t = 0.0
            end_t = 0.0
            blocks = []
            
            for w in enriched:
                emotion = str(w.get("emotion", "")).lower()
                if "sedih" in emotion or "sad" in emotion:
                    mapped = "sad"
                elif "kaget" in emotion or "shock" in emotion or "marah" in emotion or "angry" in emotion:
                    mapped = "shock"
                elif "heran" in emotion or "confused" in emotion or "janggal" in emotion:
                    mapped = "confused"
                else:
                    mapped = "neutral"
                    
                w_s = float(w.get("start", 0.0))
                w_e = float(w.get("end", 0.0))
                
                if mapped == current_emotion:
                    end_t = w_e
                else:
                    if current_emotion and current_emotion != "neutral":
                        blocks.append((current_emotion, start_t, end_t))
                    current_emotion = mapped
                    start_t = w_s
                    end_t = w_e
                    
            if current_emotion and current_emotion != "neutral":
                blocks.append((current_emotion, start_t, end_t))
                
            for emo, s, e in blocks:
                e = e + 0.3
                cond = f"between(t,{s},{e})"
                if emo == "sad":
                    vf_chain.append(f"hue=s=0:enable='{cond}'")
                    af_chain.append(f"lowpass=f=500:enable='{cond}'")
                elif emo == "shock":
                    vf_chain.append(f"geq=p(X+15*sin(T*50)\\,Y+15*cos(T*60)):enable='{cond}'")
                    vf_chain.append(f"eq=brightness=0.3:enable='{cond}'")
                    af_chain.append(f"bass=g=10:enable='{cond}'")
                    af_chain.append(f"vibrato=f=10:d=0.5:enable='{cond}'")
                elif emo == "confused":
                    vf_chain.append(f"geq=p(X/1.15+W/2*(1-1/1.15)\\,Y/1.15+H/2*(1-1/1.15)):enable='{cond}'")
                    vf_chain.append(f"vignette=PI/3:enable='{cond}'")
                    vf_chain.append(f"hue=s=0.5:enable='{cond}'")
                    af_chain.append(f"flanger=delay=10:enable='{cond}'")

        subtitle_file_fwd = subtitle_file.replace("\\", "/")
        vf_chain.append(f"subtitles=filename='{subtitle_file_fwd}'{fontsdir_arg}")
        
        cmd_subtitle = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
            "-i", cropped_file,
            "-vf", ",".join(vf_chain),
        ] + get_video_codec_args()
        
        if af_chain:
            cmd_subtitle.extend(["-af", ",".join(af_chain), "-c:a", "aac", "-b:a", "128k"])
        else:
            cmd_subtitle.extend(["-c:a", "copy"])
            
        cmd_subtitle.append(subbed_file)
        
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
