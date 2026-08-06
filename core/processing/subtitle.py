import os
import random
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
        
        try:
            from core.sfx import sfx_manager
            SFX_MAP = sfx_manager.sfx_map
        except ImportError:
            SFX_MAP = {}
        
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
                except Exception as e:
                    log.warning(f"Gagal memuat efek visual untuk {emo}: {e}")
                
                available_sfx_pool = []
                
                if emo in SFX_MAP:
                    files = SFX_MAP[emo].get("files", []) if isinstance(SFX_MAP[emo], dict) else SFX_MAP[emo]
                    for filename in files:
                        sfx_file = os.path.join("assets", "audio", filename)
                        if os.path.exists(sfx_file):
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
                if os.path.exists("C:/Windows/Fonts/arial.ttf"):
                    font_arg = "fontfile='C\\:/Windows/Fonts/arial.ttf':"
                    
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
        
        if total_sfx > 0:
            cmd_subtitle = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", cropped_file
            ]
            
            for sfx in unique_sfx_files:
                cmd_subtitle.extend(["-i", sfx])
                
            fc_parts = []
            
            fc_parts.append(f"[0:v]{','.join(vf_chain)}[vout]")
            
            if af_chain:
                fc_parts.append(f"[0:a]{','.join(af_chain)}[main_a]")
                main_a = "[main_a]"
            else:
                main_a = "[0:a]"
                
            amix_inputs = main_a
            mix_count = 1
            
            for i, (sfx_file, s_time) in enumerate(scheduled_external_sfx):
                input_idx = unique_sfx_files.index(sfx_file) + 1
                delay_ms = int(s_time * 1000)
                fc_parts.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[ext_sfx{i}]")
                amix_inputs += f"[ext_sfx{i}]"
                mix_count += 1

            fc_parts.append(f"{amix_inputs}amix=inputs={mix_count}:duration=first:dropout_transition=0:normalize=0[aout]")
            
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

    return current_clip