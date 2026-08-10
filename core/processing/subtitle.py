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
    has_frame = config.video_frame and os.path.isfile(config.video_frame)
    should_burn_sub = (use_subtitle and subtitle_generated) or has_highlight
    should_process = should_burn_sub or has_frame

    current_clip = cropped_file

    if should_process:
        if should_burn_sub and os.path.exists(subtitle_file):
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

        log.info(f"Burning subtitle/highlight/frame and SFX to video for clip {index}...")
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

        enriched = metadata.get("enriched_transcript", []) if metadata else []
        visual_emotions = metadata.get("visual_emotions", []) if metadata else []
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

        if isinstance(enriched, list) and len(enriched) > 0 and config.subtitle.style != "plain":
            current_emotion = None
            current_vfx = "random"
            current_sfx = "random"
            current_ov = "random"
            start_t = 0.0
            end_t = 0.0

            for w in enriched:
                mapped = map_emotion(str(w.get("emotion", "")))
                w_vfx = str(w.get("vfx_override", "random"))
                w_sfx = str(w.get("sfx_override", "random"))
                w_ov = str(w.get("overlay_override", "random"))

                w_s = float(w.get("start", 0.0))
                w_e = float(w.get("end", 0.0))

                if (mapped == current_emotion and w_vfx == current_vfx and 
                    w_sfx == current_sfx and w_ov == current_ov and 
                    (w_s - end_t) <= 1.0):
                    end_t = w_e
                else:
                    if current_emotion and current_emotion != "neutral":
                        blocks.append((current_emotion, start_t, end_t, current_vfx, current_sfx, current_ov))
                    current_emotion = mapped
                    current_vfx = w_vfx
                    current_sfx = w_sfx
                    current_ov = w_ov
                    start_t = w_s
                    end_t = w_e

            if current_emotion and current_emotion != "neutral":
                blocks.append((current_emotion, start_t, end_t, current_vfx, current_sfx, current_ov))

        if len(blocks) > 0:
            last_effect_time = -999.0
            filtered_blocks = []

            for block in blocks:
                s = block[1]
                # NORMALISASI: Mencegah penumpukan (spam) SFX/VFX yang memekakkan telinga/sakit mata
                # (Warna teks subtitle tetap berubah karena diurus oleh file .ass terpisah)
                if s - last_effect_time < 5:
                    continue
                last_effect_time = s
                filtered_blocks.append(block)

            # Pilih secara acak maksimal efek sesuai konfigurasi agar tersebar secara natural
            max_eff = getattr(config, "max_effects_per_clip", 3)
            if len(filtered_blocks) > max_eff:
                selected_blocks = random.sample(filtered_blocks, max_eff)
                selected_blocks.sort(key=lambda x: x[1]) # Urutkan kembali berdasarkan waktu start
            else:
                selected_blocks = filtered_blocks

            for emo, s, e, vfx_idx_str, sfx_idx_str, ov_idx_str in selected_blocks:
                e = e + 0.3
                cond = f"between(t,{s},{e})"

                try:
                    from core.vfx import vfx_manager

                    if vfx_idx_str == "none":
                        effect = {"vf": [], "af": []}
                    elif vfx_idx_str != "random" and vfx_idx_str.isdigit():
                        idx = int(vfx_idx_str)
                        vfx_list = vfx_manager.vfx_map.get(emo, [])
                        effect = vfx_list[idx] if idx < len(vfx_list) else vfx_manager.get_random_effect(emo)
                    else:
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

                    if ov_idx_str == "none":
                        overlay_info = None
                    elif ov_idx_str != "random" and ov_idx_str.isdigit():
                        idx = int(ov_idx_str)
                        ov_list = overlay_manager.overlay_map.get(emo, [])
                        overlay_info = ov_list[idx] if idx < len(ov_list) else overlay_manager.get_random_overlay(emo)
                    else:
                        overlay_info = overlay_manager.get_random_overlay(emo)

                    if overlay_info and overlay_info.get("file"):
                        overlay_file = os.path.join("assets", "overlay", overlay_info["file"])
                        if os.path.exists(overlay_file):
                            scheduled_overlays.append({
                                "file": overlay_file,
                                "start": s,
                                "end": e,
                                "effect": overlay_info.get("effect", "transparent")
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
                    if sfx_idx_str == "none":
                        chosen_sfx = {"type": "empty", "data": None}
                    elif sfx_idx_str != "random" and sfx_idx_str.isdigit():
                        idx = int(sfx_idx_str)
                        chosen_sfx = available_sfx_pool[idx] if idx < len(available_sfx_pool) else random.choice(available_sfx_pool)
                    else:
                        chosen_sfx = random.choice(available_sfx_pool)

                    if chosen_sfx["type"] == "external":
                        scheduled_external_sfx.append((chosen_sfx["data"], s))

        if should_burn_sub and os.path.exists(subtitle_file):
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

        if total_sfx > 0 or total_overlays > 0 or has_frame:
            cmd_subtitle = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", cropped_file
            ]
            if has_frame and config.video_frame is not None:
                cmd_subtitle.extend(["-stream_loop", "-1", "-i", config.video_frame])

            sfx_input_offset = 2 if has_frame else 1
            for sfx in unique_sfx_files:
                cmd_subtitle.extend(["-i", sfx])

            overlay_input_offset = sfx_input_offset + len(unique_sfx_files)
            for ov in scheduled_overlays:
                ovf = ov["file"]
                if ovf.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    cmd_subtitle.extend(["-loop", "1", "-i", ovf])
                elif ovf.lower().endswith(".gif"):
                    cmd_subtitle.extend(["-ignore_loop", "0", "-i", ovf])
                else:
                    cmd_subtitle.extend(["-i", ovf])

            fc_parts = []
            out_w, out_h = config.out_width or 720, config.out_height or 1280

            # Scale and chromakey frame video, then overlay on top of [0:v]
            if has_frame and config.video_frame is not None:
                frame_input_idx = 1
                fc_parts.append(f"[{frame_input_idx}:v]scale={out_w}:{out_h},chromakey=0x00B140:0.1:0.1[frame_v]")
                fc_parts.append(f"[0:v][frame_v]overlay=shortest=1[video_with_frame]")

            start_v_stream = "[video_with_frame]" if has_frame else "[0:v]"

            if vf_chain:
                vf_filter = f"{start_v_stream}{','.join(vf_chain)}"
            else:
                vf_filter = start_v_stream

            # --- VIDEO FILTER CHAIN ---
            if total_overlays > 0:
                fc_parts.append(f"{vf_filter}[vout_0]")
                last_v = "[vout_0]"

                for i, ov in enumerate(scheduled_overlays):
                    ov_idx = overlay_input_offset + i
                    ov_start = ov["start"]
                    ov_end = ov["end"]
                    effect = ov["effect"]

                    ov_stream = f"[ov_processed_{i}]"
                    duration = ov_end - ov_start
                    if duration <= 0:
                        duration = 1.0
                        ov_end = ov_start + 1.0

                    # Pastikan GIF memiliki waktu tayang yang cukup (minimal 2 detik)
                    if ov["file"].lower().endswith(".gif") and duration < 2.0:
                        duration = 2.0
                        ov_end = ov_start + 2.0
                        
                    # Batasi durasi maksimum overlay agar tidak menutupi layar terlalu lama (maksimal 2.5 detik)
                    if duration > 2.5:
                        duration = 2.5
                        ov_end = ov_start + 2.5

                    from core.overlay import overlay_manager
                    ov_filter, overlay_cmd = overlay_manager.get_filter_strings(i, ov_idx, ov_start, ov_end, effect)

                    fc_parts.append(ov_filter)

                    next_v = f"[vout_{i+1}]"
                    cond = f"between(t,{ov_start},{ov_end})"
                    fc_parts.append(f"{last_v}{ov_stream}{overlay_cmd}:enable='{cond}'{next_v}")
                    last_v = next_v

                # Force yuv420p di dalam filter graph agar HW Encoder tidak bingung dan melakukan RGB/BGR swap
                fc_parts.append(f"{last_v}format=yuv420p[vout_final]")
                map_v = "[vout_final]"
            else:
                fc_parts.append(f"{vf_filter},format=yuv420p[vout_final]")
                map_v = "[vout_final]"

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
            vf_string = ",".join(vf_chain) + ",format=yuv420p" if vf_chain else "format=yuv420p"
            cmd_subtitle = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", cropped_file,
                "-vf", vf_string,
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
