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
        af_chain = ["loudnorm=I=-14:LRA=11:TP=-1.5"]
        scheduled_external_sfx = []
        scheduled_synth_sfx = []
        
        try:
            from core.constant import SFX_MAP, SYNTH_SFX_MAP
        except ImportError:
            SFX_MAP = {}
            SYNTH_SFX_MAP = {}
        
        enriched = metadata.get("enriched_transcript", [])
        if isinstance(enriched, list) and len(enriched) > 0:
            current_emotion = None
            start_t = 0.0
            end_t = 0.0
            blocks = []
            
            for w in enriched:
                emotion = str(w.get("emotion", "")).lower()
                
                if any(e in emotion for e in ["sedih", "sad", "nangis"]):
                    mapped = "sad"
                elif any(e in emotion for e in ["bosan", "bored", "capek", "lelah", "garing"]):
                    mapped = "bored"
                elif any(e in emotion for e in ["kaget", "shock", "terkejut"]):
                    mapped = "shock"
                elif any(e in emotion for e in ["takut", "fear", "panik", "seram"]):
                    mapped = "fear"
                elif any(e in emotion for e in ["marah", "angry", "kesal", "emosi", "frustrasi"]):
                    mapped = "angry"
                elif any(e in emotion for e in ["jijik", "disgust", "ew", "najis", "bau"]):
                    mapped = "disgust"
                elif any(e in emotion for e in ["heran", "confused", "janggal", "bingung"]):
                    mapped = "confused"
                elif any(e in emotion for e in ["senang", "happy", "joy", "excited", "keren", "mantap"]):
                    mapped = "happy"
                elif any(e in emotion for e in ["lucu", "amused", "haha", "wkwk", "ngakak"]):
                    mapped = "amused"
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
                elif emo == "bored":
                    vf_chain.append(f"hue=s=0.2:enable='{cond}'")
                elif emo == "shock":
                    vf_chain.append(f"geq=p(X+15*sin(T*50)\\,Y+15*cos(T*60)):enable='{cond}'")
                    vf_chain.append(f"eq=brightness=0.3:enable='{cond}'")
                    af_chain.append(f"bass=g=5:enable='{cond}'")
                    af_chain.append(f"tremolo=f=10:d=0.5:enable='{cond}'")
                elif emo == "fear":
                    vf_chain.append(f"geq=p(X+5*sin(T*100)\\,Y+5*cos(T*110)):enable='{cond}'")
                    vf_chain.append(f"vignette=PI/2:enable='{cond}'")
                elif emo == "angry":
                    vf_chain.append(f"eq=gamma_r=1.5:gamma_g=0.8:gamma_b=0.8:enable='{cond}'")
                elif emo == "disgust":
                    vf_chain.append(f"eq=gamma_g=1.5:gamma_r=0.8:gamma_b=0.8:enable='{cond}'")
                elif emo == "confused":
                    vf_chain.append(f"geq=p(X/1.15+W/2*(1-1/1.15)\\,Y/1.15+H/2*(1-1/1.15)):enable='{cond}'")
                    vf_chain.append(f"vignette=PI/3:enable='{cond}'")
                    vf_chain.append(f"hue=s=0.5:enable='{cond}'")
                elif emo == "happy":
                    vf_chain.append(f"eq=saturation=1.5:brightness=0.05:enable='{cond}'")
                elif emo == "amused":
                    vf_chain.append(f"eq=contrast=1.3:enable='{cond}'")
                
                available_sfx_pool = []
                
                if emo in SFX_MAP:
                    for filename in SFX_MAP[emo]:
                        sfx_file = "assets/audio/" + filename
                        if os.path.exists(sfx_file):
                            available_sfx_pool.append({"type": "external", "data": sfx_file})
                            pass
                        else:
                            log.debug(f"File MP3 dilewati karena tidak ditemukan: {sfx_file}")
                
                if emo in SYNTH_SFX_MAP:
                    # available_sfx_pool.append({"type": "synth", "data": SYNTH_SFX_MAP[emo]})
                    pass

                if available_sfx_pool:
                    chosen_sfx = random.choice(available_sfx_pool)
                    
                    if chosen_sfx["type"] == "external":
                        scheduled_external_sfx.append((chosen_sfx["data"], s))
                    elif chosen_sfx["type"] == "synth":
                        scheduled_synth_sfx.append((chosen_sfx["data"], s))

        subtitle_file_fwd = subtitle_file.replace("\\", "/")
        vf_chain.append(f"subtitles=filename='{subtitle_file_fwd}'{fontsdir_arg}")
        
        unique_sfx_files = list(dict.fromkeys([sfx for sfx, _ in scheduled_external_sfx]))
        total_sfx = len(scheduled_external_sfx) + len(scheduled_synth_sfx)
        
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
                
            for i, (recipe, s_time) in enumerate(scheduled_synth_sfx):
                delay_ms = int(s_time * 1000)
                fc_parts.append(f"{recipe}[raw_syn{i}];[raw_syn{i}]adelay={delay_ms}|{delay_ms}[syn_sfx{i}]")
                amix_inputs += f"[syn_sfx{i}]"
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
            if callable(event_hook):
                try:
                    event_hook("log", "[ffmpeg-subtitle] ERROR: FFmpeg processing failed. Menyimpan video tanpa subtitle.")
                except Exception:
                    pass

    return current_clip