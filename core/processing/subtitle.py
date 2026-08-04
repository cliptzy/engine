import os
import random  # <-- Tambahkan import random
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
                
                if not use_subtitle:
                    with open(subtitle_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    with open(subtitle_file, "w", encoding="utf-8") as f:
                        for line in lines:
                            if not line.startswith("Dialogue:"):
                                f.write(line)
                                
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
                
        log.info(f"Burning subtitle/highlight and SFX to video for clip {index}...")
        fontsdir_arg = ""
        if config.subtitle.fonts_dir and os.path.isdir(config.subtitle.fonts_dir):
            fontsdir_fwd = config.subtitle.fonts_dir.replace("\\", "/")
            fontsdir_arg = f":fontsdir='{fontsdir_fwd}'"
        
        vf_chain = []
        af_chain = []
        
        from core.constant import SFX_MAP
        scheduled_sfx = []
        
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
                
                # Tambahkan efek visual dan filter audio utama
                if emo == "sad":
                    vf_chain.append(f"hue=s=0:enable='{cond}'")
                    af_chain.append(f"lowpass=f=500:enable='{cond}'")
                elif emo == "shock":
                    vf_chain.append(f"geq=p(X+15*sin(T*50)\\,Y+15*cos(T*60)):enable='{cond}'")
                    vf_chain.append(f"eq=brightness=0.3:enable='{cond}'")
                    af_chain.append(f"bass=g=5:enable='{cond}'")
                    af_chain.append(f"tremolo=f=10:d=0.5:enable='{cond}'")
                elif emo == "confused":
                    vf_chain.append(f"geq=p(X/1.15+W/2*(1-1/1.15)\\,Y/1.15+H/2*(1-1/1.15)):enable='{cond}'")
                    vf_chain.append(f"vignette=PI/3:enable='{cond}'")
                    vf_chain.append(f"hue=s=0.5:enable='{cond}'")
                    af_chain.append(f"flanger=delay=10:enable='{cond}'")
                
                if emo in SFX_MAP and len(SFX_MAP[emo]) > 0:
                    sfx_file = "assets/audio/" + random.choice(SFX_MAP[emo])
                    if os.path.exists(sfx_file):
                        scheduled_sfx.append((sfx_file, s))
                    else:
                        log.warning(f"SFX file not found for emotion '{emo}': {sfx_file}")

        subtitle_file_fwd = subtitle_file.replace("\\", "/")
        vf_chain.append(f"subtitles=filename='{subtitle_file_fwd}'{fontsdir_arg}")
        
        
        unique_sfx_files = list(dict.fromkeys([sfx for sfx, _ in scheduled_sfx]))
        
        if len(unique_sfx_files) > 0:
            cmd_subtitle = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", cropped_file
            ]
            
            for sfx in unique_sfx_files:
                cmd_subtitle.extend(["-i", sfx])
                
            fc_parts = []
            
            # Mapping Video
            fc_parts.append(f"[0:v]{','.join(vf_chain)}[vout]")
            
            # Mapping Audio Utama
            if af_chain:
                fc_parts.append(f"[0:a]{','.join(af_chain)}[main_a]")
                main_a = "[main_a]"
            else:
                main_a = "[0:a]"
                
            # Adelay untuk setiap SFX
            amix_inputs = main_a
            for i, (sfx_file, s_time) in enumerate(scheduled_sfx):
                input_idx = unique_sfx_files.index(sfx_file) + 1
                delay_ms = int(s_time * 1000)
                fc_parts.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[sfx{i}]")
                amix_inputs += f"[sfx{i}]"
                
            # Mix
            mix_count = len(scheduled_sfx) + 1
            fc_parts.append(f"{amix_inputs}amix=inputs={mix_count}:duration=first:dropout_transition=0[aout]")
            
            cmd_subtitle.extend(["-filter_complex", ";".join(fc_parts)])
            cmd_subtitle.extend(["-map", "[vout]", "-map", "[aout]"])
            
            cmd_subtitle.extend(get_video_codec_args())
            cmd_subtitle.extend(["-c:a", "aac", "-b:a", "128k"])
            cmd_subtitle.append(subbed_file)
            
        else:
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
        
        # Eksekusi
        try:
            run_command_with_logging(cmd_subtitle, event_hook, prefix="[ffmpeg-subtitle]")
            current_clip = subbed_file
        except subprocess.CalledProcessError as e:
            log.warning("FFmpeg subtitle filter failed. Falling back to non-subbed video.")
            if callable(event_hook):
                try:
                    event_hook("log", "[ffmpeg-subtitle] ERROR: FFmpeg processing failed. Menyimpan video tanpa subtitle.")
                except Exception:
                    pass

    return current_clip