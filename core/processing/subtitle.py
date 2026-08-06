import os
import random
import subprocess
import sys
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
            log.info( f"Adding Highlight text to subtitle file for clip {index}...")
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
        af_chain = ["loudnorm=I=-14:LRA=11:TP=-1.5"]
        scheduled_external_sfx = []
        scheduled_overlays = []
        
        try:
            from core.sfx import sfx_manager
            SFX_MAP = sfx_manager.sfx_map
        except ImportError:
            SFX_MAP = {}
            
        try:
            from core.overlay import overlay_manager
            OVERLAY_MAP = overlay_manager.overlay_map
        except ImportError:
            OVERLAY_MAP = {}
        
        enriched = metadata.get("enriched_transcript", [])
        visual_emotions = metadata.get("visual_emotions", [])
        blocks = []
        
        def map_emotion(emotion_str: str) -> str:
            emotion_str = emotion_str.lower().strip()
            if not emotion_str:
                return "neutral"
                
            if emotion_str in SFX_MAP:
                return emotion_str
                
            for key in SFX_MAP:
                if key in emotion_str:
                    return key
                    
            for key, data in SFX_MAP.items():
                desc = data.get("desc", "").lower() if isinstance(data, dict) else ""
                desc_words = [w.strip(".,/()\"'") for w in desc.split()]
                for word in emotion_str.split():
                    word_clean = word.strip(".,/()\"'")
                    if word_clean and word_clean in desc_words:
                        return key
                        
            return "neutral"
            
        if isinstance(enriched, list) and len(enriched) > 0:
            current_emotion = None
            start_t = 0.0
            end_t = 0.0
            
            for w in enriched:
                mapped = map_emotion(str(w.get("emotion", "")))
                    
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
                
        if isinstance(visual_emotions, list) and len(visual_emotions) > 0:
            for ve in visual_emotions:
                mapped = map_emotion(str(ve.get("emotion", "")))
                    
                if mapped != "neutral":
                    t = float(ve.get("time", 0.0))
                    blocks.append((mapped, t, t + 2.0))
                    
        if len(blocks) > 0:
                
            for emo, s, e in blocks:
                e = e + 0.3
                cond = f"between(t,{s},{e})"
                
                try:
                    from core.vfx import vfx_manager
                    effect = vfx_manager.get_random_effect(emo)
                    for vf_filter in effect.get("vf", []):
                        vf_chain.append(f"{vf_filter}:enable='{cond}'")
                    for af_filter in effect.get("af", []):
                        af_chain.append(f"{af_filter}:enable='{cond}'")
                except Exception as ex_vfx:
                    log.warning(f"Gagal memuat efek visual untuk {emo}: {ex_vfx}")
                
                # --- LAYERING / OVERLAY LOGIC ---
                try:
                    from core.overlay import overlay_manager
                    overlay_info = overlay_manager.get_random_overlay(emo)
                    if overlay_info and overlay_info.get("file"):
                        overlay_file = os.path.join("assets", "overlay", overlay_info["file"])
                        if os.path.exists(overlay_file):
                            scheduled_overlays.append({
                                "file": overlay_file,
                                "start": s,
                                "end": e,
                                "effect": overlay_info.get("effect", "transparent"),
                                "opacity": overlay_info.get("opacity", 0.5)
                            })
                        else:
                            log.debug(f"File overlay dilewati karena tidak ditemukan: {overlay_file}")
                except Exception as ex:
                    log.warning(f"Gagal memuat overlay untuk {emo}: {ex}")

                available_sfx_pool = []
                
                if emo in SFX_MAP:
                    files = SFX_MAP[emo].get("files", []) if isinstance(SFX_MAP[emo], dict) else SFX_MAP[emo]
                    for filename in files:
                        if not filename or filename.lower() == "none":
                            available_sfx_pool.append({"type": "empty", "data": None})
                            continue
                        sfx_file = os.path.join("assets", "audio", filename)
                        if os.path.exists(sfx_file) and os.path.isfile(sfx_file):
                            available_sfx_pool.append({"type": "external", "data": sfx_file})
                        else:
                            log.debug(f"File MP3 dilewati karena tidak ditemukan: {sfx_file}")

                if available_sfx_pool:
                    chosen_sfx = random.choice(available_sfx_pool)
                    
                    if chosen_sfx["type"] == "external":
                        scheduled_external_sfx.append((chosen_sfx["data"], s))

        subtitle_file_fwd = subtitle_file.replace("\\", "/")
        vf_chain.append(f"subtitles=filename='{subtitle_file_fwd}'{fontsdir_arg}")
        
        if getattr(config, "debug_mode", False):
            from core.subtitle import write_debug_ass_file
            debug_file = subtitle_file.replace(".ass", "_debug.ass")
            if write_debug_ass_file(metadata, debug_file):
                debug_file_fwd = debug_file.replace("\\", "/")
                vf_chain.append(f"subtitles=filename='{debug_file_fwd}'")
                
            # Tambahkan visual bounding box dari DeepFace ke video
            if isinstance(visual_emotions, list) and len(visual_emotions) > 0:
                font_arg = ""
                font_paths = []
                if sys.platform == "win32":
                    font_paths = ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/consola.ttf"]
                elif sys.platform == "darwin":
                    font_paths = ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"]
                else:
                    font_paths = [
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                    ]
                for fp in font_paths:
                    if os.path.exists(fp):
                        fp_esc = fp.replace(":", "\\:")
                        font_arg = f"fontfile='{fp_esc}':"
                        break
                    
                for i, ve in enumerate(visual_emotions):
                    t = float(ve.get("time", 0.0))
                    box = ve.get("box")
                    if box and isinstance(box, dict):
                        bx, by, bw, bh = box.get('x', 0), box.get('y', 0), box.get('w', 0), box.get('h', 0)
                        next_t = float(visual_emotions[i+1].get("time", t + 1.0)) if i+1 < len(visual_emotions) else t + 1.0
                        emo_text = f"{ve.get('emotion')} ({ve.get('score')})"
                        cond = f"between(t,{t},{next_t})"
                        
                        vf_chain.append(f"drawbox=x={bx}:y={by}:w={bw}:h={bh}:color=red@0.8:thickness=4:enable='{cond}'")
                        vf_chain.append(f"drawtext={font_arg}text='{emo_text}':x={bx}:y={by}-30:fontcolor=white:fontsize=24:box=1:boxcolor=black@0.6:boxborderw=5:enable='{cond}'")
        
        unique_sfx_files = list(dict.fromkeys([sfx for sfx, _ in scheduled_external_sfx]))
        total_sfx = len(scheduled_external_sfx)
        
        total_overlays = len(scheduled_overlays)
        
        if total_sfx > 0 or total_overlays > 0:
            cmd_subtitle = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", cropped_file
            ]
            
            sfx_input_offset = 1
            for sfx in unique_sfx_files:
                cmd_subtitle.extend(["-i", sfx])
                
            overlay_input_offset = sfx_input_offset + len(unique_sfx_files)
            for ov in scheduled_overlays:
                ovf = ov["file"]
                if ovf.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    cmd_subtitle.extend(["-loop", "1", "-i", ovf])
                else:
                    cmd_subtitle.extend(["-i", ovf])
                
            fc_parts = []
            
            # --- VIDEO FILTER CHAIN ---
            if total_overlays > 0:
                fc_parts.append(f"[0:v]{','.join(vf_chain)}[vout_0]")
                last_v = "[vout_0]"
                
                for i, ov in enumerate(scheduled_overlays):
                    ov_idx = overlay_input_offset + i
                    ov_start = ov["start"]
                    ov_end = ov["end"]
                    effect = ov["effect"]
                    opacity = ov["opacity"]
                    
                    ov_stream = f"[ov_processed_{i}]"
                    duration = ov_end - ov_start
                    if duration <= 0:
                        duration = 1.0
                        ov_end = ov_start + 1.0
                        
                    base_filter = f"[{ov_idx}:v]setpts=PTS-STARTPTS+{ov_start}/TB,format=argb"
                    
                    if effect == "transparent":
                        fade_d = min(0.5, duration / 2)
                        fade_st = ov_end - fade_d
                        ov_filter = f"{base_filter},scale=720:-1,colorchannelmixer=aa={opacity},fade=t=out:st={fade_st}:d={fade_d}:alpha=1[ov_processed_{i}]"
                    else:
                        ov_filter = f"{base_filter},scale=720:-1[ov_processed_{i}]"
                        
                    fc_parts.append(ov_filter)
                    
                    next_v = f"[vout_{i+1}]"
                    cond = f"between(t,{ov_start},{ov_end})"
                    fc_parts.append(f"{last_v}{ov_stream}overlay=x=(W-w)/2:y=(H-h)/2:enable='{cond}'{next_v}")
                    last_v = next_v
                    
                map_v = last_v
            else:
                fc_parts.append(f"[0:v]{','.join(vf_chain)}[vout]")
                map_v = "[vout]"
                
            # --- AUDIO FILTER CHAIN ---
            if af_chain:
                fc_parts.append(f"[0:a]{','.join(af_chain)}[main_a]")
                main_a = "[main_a]"
            else:
                main_a = "[0:a]"
                
            if total_sfx > 0:
                amix_inputs = main_a
                mix_count = 1
                
                for i, (sfx_file, s_time) in enumerate(scheduled_external_sfx):
                    s_idx = unique_sfx_files.index(sfx_file) + sfx_input_offset
                    delay_ms = int(s_time * 1000)
                    fc_parts.append(f"[{s_idx}:a]adelay={delay_ms}|{delay_ms}[ext_sfx{i}]")
                    amix_inputs += f"[ext_sfx{i}]"
                    mix_count += 1
    
                fc_parts.append(f"{amix_inputs}amix=inputs={mix_count}:duration=first:dropout_transition=0:normalize=0[aout]")
                map_a = "[aout]"
            else:
                map_a = main_a
            
            cmd_subtitle.extend(["-filter_complex", ";".join(fc_parts)])
            cmd_subtitle.extend(["-map", map_v, "-map", map_a])
            
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

    return current_clip