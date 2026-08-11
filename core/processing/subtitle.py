import os
import random
import subprocess
import sys
from typing import Callable, Optional

from core.config import config
from core.logger import log
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
    event_hook: Optional[Callable] = None,
) -> str:
    has_highlight = config.ai.use_highlight and metadata and metadata.get("highlight")
    has_frame = config.video_frame and os.path.isfile(config.video_frame)
    should_burn_sub = (use_subtitle and subtitle_generated) or has_highlight
    should_process = should_burn_sub or has_frame

    current_clip = cropped_file

    if should_process:
        if should_burn_sub and os.path.exists(subtitle_file):
            if has_highlight:
                log.info(f"Adding Highlight text to subtitle file for clip {index}...")
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

        log.info(
            f"Burning subtitle/highlight/frame and Video Effects to video for clip {index}..."
        )
        fontsdir_arg = ""
        if config.subtitle.fonts_dir and os.path.isdir(config.subtitle.fonts_dir):
            fontsdir_fwd = config.subtitle.fonts_dir.replace("\\", "/")
            fontsdir_arg = f":fontsdir='{fontsdir_fwd}'"

        vf_chain = []
        af_chain = ["loudnorm=I=-14:LRA=11:TP=-1.5"]
        scheduled_video_effects = []
        selected_effects = []

        try:
            from core.video_effects import video_effect_manager

            EFFECTS_MAP = video_effect_manager.effects_map
        except ImportError:
            EFFECTS_MAP = {}

        enriched = metadata.get("enriched_transcript", []) if metadata else []
        visual_emotions = metadata.get("visual_emotions", []) if metadata else []
        blocks = []

        def map_emotion(emotion_str: str) -> str:
            emotion_str = emotion_str.lower().strip()
            if not emotion_str:
                return "neutral"
            if emotion_str in EFFECTS_MAP:
                return emotion_str
            for key in EFFECTS_MAP:
                if key in emotion_str:
                    return key
            return "neutral"

        if (
            isinstance(enriched, list)
            and len(enriched) > 0
            and config.subtitle.style != "plain"
        ):
            current_emotion = None
            current_ve = "random"
            current_score = 0.0
            start_t = 0.0
            end_t = 0.0

            for w in enriched:
                mapped = map_emotion(str(w.get("emotion", "")))
                w_ve = str(w.get("video_effect_override", "random"))

                w_s = float(w.get("start", 0.0))
                w_e = float(w.get("end", 0.0))

                try:
                    w_score = float(w.get("score", 0.0))
                except Exception:
                    w_score = 0.0

                if (
                    mapped == current_emotion
                    and w_ve == current_ve
                    and (w_s - end_t) <= 1.0
                ):
                    end_t = w_e
                    current_score = max(current_score, w_score)
                else:
                    if current_emotion and current_emotion != "neutral":
                        blocks.append(
                            (current_emotion, start_t, end_t, current_ve, current_score)
                        )
                    current_emotion = mapped
                    current_ve = w_ve
                    current_score = w_score
                    start_t = w_s
                    end_t = w_e

            if current_emotion and current_emotion != "neutral":
                blocks.append(
                    (current_emotion, start_t, end_t, current_ve, current_score)
                )

        if len(blocks) > 0:
            last_effect_time = -999.0
            filtered_blocks = []

            for block in blocks:
                s = block[1]
                if s - last_effect_time < 5:
                    continue
                last_effect_time = s
                filtered_blocks.append(block)

            max_eff = getattr(config, "max_effects_per_clip", 3)
            if len(filtered_blocks) > max_eff:
                selected_blocks = sorted(
                    filtered_blocks, key=lambda x: x[4], reverse=True
                )[:max_eff]
                selected_blocks.sort(key=lambda x: x[1])
            else:
                selected_blocks = filtered_blocks

            for emo, s, e, ve_idx_str, _score in selected_blocks:
                e = e + 0.3
                effect = None

                if ve_idx_str != "none":
                    try:
                        from core.video_effects import video_effect_manager

                        if ve_idx_str != "random":
                            effect = video_effect_manager.get_effect_by_name(ve_idx_str)
                            if not effect:
                                effect = video_effect_manager.get_effect(
                                    emo, selected_effects
                                )
                        else:
                            effect = video_effect_manager.get_effect(
                                emo, selected_effects
                            )
                    except Exception as ex:
                        log.warning(f"Gagal memuat video effect untuk {emo}: {ex}")

                if effect and effect.get("file"):
                    eff_file = os.path.join("assets", "video_effects", effect["file"])
                    if os.path.exists(eff_file):
                        selected_effects.append(effect.get("name"))
                        scheduled_video_effects.append(
                            {
                                "file": eff_file,
                                "type": effect.get("type", "greenscreen"),
                                "key_color": effect.get("key_color", "0x00FF00"),
                                "start": s,
                                "end": e,
                                "position": effect.get("position", "center"),
                                "audio_filter": effect.get(
                                    "audio_filter",
                                    "volume=0.8,afade=t=out:st=1.5:d=0.5",
                                ),
                            }
                        )
                    else:
                        log.debug(
                            f"Video effect dilewati karena file tidak ditemukan: {eff_file}"
                        )

        # --- NON-VERBAL / STANDALONE EFFECTS ---
        standalone_effects = (
            metadata.get("standalone_video_effects", []) if metadata else []
        )
        standalone_effects = sorted(standalone_effects, key=lambda x: float(x.get("time", 0.0)))
        for se in standalone_effects:
            ve_name = se.get("video_effect_override")
            s = float(se.get("time", 0.0))
            
            # Prevent overlap with other scheduled effects
            overlap = False
            for scheduled in scheduled_video_effects:
                if abs(scheduled["start"] - s) < 5.0:
                    overlap = True
                    break
            if overlap:
                continue

            if ve_name and ve_name not in ["none", "random"]:
                try:
                    from core.video_effects import video_effect_manager

                    effect = video_effect_manager.get_effect_by_name(ve_name)
                    
                    # Anti-spam: If effect was already used, try to pick an alternative with the same emotion
                    if effect and effect.get("name") in selected_effects:
                        emos = effect.get("emotions", [])
                        if emos:
                            alt_effect = video_effect_manager.get_effect(emos[0], exclude=selected_effects)
                            if alt_effect:
                                effect = alt_effect

                    if effect and effect.get("file"):
                        eff_file = os.path.join(
                            "assets", "video_effects", effect["file"]
                        )
                        if os.path.exists(eff_file):
                            selected_effects.append(effect.get("name"))
                            scheduled_video_effects.append(
                                {
                                    "file": eff_file,
                                    "type": effect.get("type", "greenscreen"),
                                    "key_color": effect.get("key_color", "0x00FF00"),
                                    "start": s,
                                    "end": s + 3.0,  # default 3s untuk standalone
                                    "position": effect.get("position", "center"),
                                    "audio_filter": effect.get(
                                        "audio_filter",
                                        "volume=0.8,afade=t=out:st=1.5:d=0.5",
                                    ),
                                }
                            )
                except Exception as ex:
                    log.warning(f"Gagal memuat standalone video effect {ve_name}: {ex}")

        if should_burn_sub and os.path.exists(subtitle_file):
            subtitle_file_fwd = subtitle_file.replace("\\", "/")
            vf_chain.append(f"subtitles=filename='{subtitle_file_fwd}'{fontsdir_arg}")

        if getattr(config, "debug_mode", False):
            from core.subtitle import write_debug_ass_file

            debug_file = subtitle_file.replace(".ass", "_debug.ass")
            if write_debug_ass_file(metadata, debug_file):
                debug_file_fwd = debug_file.replace("\\", "/")
                vf_chain.append(f"subtitles=filename='{debug_file_fwd}'")

            if isinstance(visual_emotions, list) and len(visual_emotions) > 0:
                font_arg = ""
                font_paths = []
                if sys.platform == "win32":
                    font_paths = [
                        "C:/Windows/Fonts/arial.ttf",
                        "C:/Windows/Fonts/consola.ttf",
                    ]
                elif sys.platform == "darwin":
                    font_paths = [
                        "/System/Library/Fonts/Helvetica.ttc",
                        "/Library/Fonts/Arial.ttf",
                    ]
                else:
                    font_paths = [
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
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
                        bx, by, bw, bh = (
                            box.get("x", 0),
                            box.get("y", 0),
                            box.get("w", 0),
                            box.get("h", 0),
                        )
                        next_t = (
                            float(visual_emotions[i + 1].get("time", t + 1.0))
                            if i + 1 < len(visual_emotions)
                            else t + 1.0
                        )
                        emo_text = f"{ve.get('emotion')} ({ve.get('score')})"
                        cond = f"between(t,{t},{next_t})"
                        vf_chain.append(
                            f"drawbox=x={bx}:y={by}:w={bw}:h={bh}:color=red@0.8:thickness=4:enable='{cond}'"
                        )
                        vf_chain.append(
                            f"drawtext={font_arg}text='{emo_text}':x={bx}:y={by}-30:fontcolor=white:fontsize=24:box=1:boxcolor=black@0.6:boxborderw=5:enable='{cond}'"
                        )

        total_ve = len(scheduled_video_effects)

        if total_ve > 0 or has_frame:
            cmd_subtitle = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "info",
                "-i",
                cropped_file,
            ]
            if has_frame and config.video_frame is not None:
                cmd_subtitle.extend(["-stream_loop", "-1", "-i", config.video_frame])

            ve_input_offset = 2 if has_frame else 1
            for ve in scheduled_video_effects:
                cmd_subtitle.extend(["-i", ve["file"]])

            fc_parts = []
            out_w, out_h = config.out_width or 720, config.out_height or 1280

            if has_frame and config.video_frame is not None:
                frame_input_idx = 1
                fc_parts.append(
                    f"[{frame_input_idx}:v]scale={out_w}:{out_h},chromakey=0x00B140:0.1:0.1[frame_v]"
                )
                fc_parts.append(f"[0:v][frame_v]overlay=shortest=1[video_with_frame]")

            start_v_stream = "[video_with_frame]" if has_frame else "[0:v]"

            if vf_chain:
                vf_filter = f"{start_v_stream}{','.join(vf_chain)}"
            else:
                vf_filter = start_v_stream

            if total_ve > 0:
                fc_parts.append(f"{vf_filter}[vout_0]")
                last_v = "[vout_0]"
                a_mix_inputs = "[0:a]"
                a_mix_count = 1

                for i, ve in enumerate(scheduled_video_effects):
                    ve_idx = ve_input_offset + i
                    ve_start = ve["start"]

                    processed_v = f"[ve_v_{i}]"
                    if ve["type"] == "greenscreen":
                        key_col = ve.get("key_color", "0x00FF00")
                        fc_parts.append(
                            f"[{ve_idx}:v]scale={out_w}:-1,chromakey={key_col}:0.3:0.1,setpts=PTS-STARTPTS+{ve_start}/TB{processed_v}"
                        )
                    elif ve["type"] == "alpha":
                        fc_parts.append(
                            f"[{ve_idx}:v]scale={out_w}:-1,setpts=PTS-STARTPTS+{ve_start}/TB{processed_v}"
                        )
                    else:  # fullscreen
                        fc_parts.append(
                            f"[{ve_idx}:v]scale={out_w}:{out_h},setpts=PTS-STARTPTS+{ve_start}/TB{processed_v}"
                        )

                    pos_y = "(H-h)/2"
                    if ve.get("position") == "bottom":
                        pos_y = "H-h-50"
                    elif ve.get("position") == "top":
                        pos_y = "50"

                    next_v = f"[vout_{i + 1}]"
                    fc_parts.append(
                        f"{last_v}{processed_v}overlay=x=(W-w)/2:y={pos_y}:enable='gte(t,{ve_start})':eof_action=pass{next_v}"
                    )
                    last_v = next_v

                    delay_ms = int(ve_start * 1000)
                    ve_a = f"[ve_a_{i}]"
                    audio_filter = ve.get("audio_filter", "volume=1.0")
                    if audio_filter == "" or not audio_filter:
                        audio_filter = "volume=1.0"
                    fc_parts.append(
                        f"[{ve_idx}:a]{audio_filter},adelay={delay_ms}|{delay_ms}{ve_a}"
                    )
                    a_mix_inputs += ve_a
                    a_mix_count += 1

                fc_parts.append(f"{last_v}format=yuv420p[vout_final]")
                map_v = "[vout_final]"

                if af_chain:
                    fc_parts.append(
                        f"{a_mix_inputs}amix=inputs={a_mix_count}:duration=first:dropout_transition=0:normalize=0,{','.join(af_chain)}[aout]"
                    )
                else:
                    fc_parts.append(
                        f"{a_mix_inputs}amix=inputs={a_mix_count}:duration=first:dropout_transition=0:normalize=0[aout]"
                    )
                map_a = "[aout]"
            else:
                fc_parts.append(f"{vf_filter},format=yuv420p[vout_final]")
                map_v = "[vout_final]"
                if af_chain:
                    fc_parts.append(f"[0:a]{','.join(af_chain)}[aout]")
                    map_a = "[aout]"
                else:
                    map_a = "[0:a]"

            cmd_subtitle.extend(["-filter_complex", ";".join(fc_parts)])
            cmd_subtitle.extend(["-map", map_v, "-map", map_a])

            cmd_subtitle.extend(get_video_codec_args())
            cmd_subtitle.extend(["-c:a", "aac", "-b:a", "128k"])
            cmd_subtitle.append(subbed_file)

        else:
            vf_string = (
                ",".join(vf_chain) + ",format=yuv420p" if vf_chain else "format=yuv420p"
            )
            cmd_subtitle = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "info",
                "-i",
                cropped_file,
                "-vf",
                vf_string,
            ] + get_video_codec_args()

            if af_chain:
                cmd_subtitle.extend(
                    ["-af", ",".join(af_chain), "-c:a", "aac", "-b:a", "128k"]
                )
            else:
                cmd_subtitle.extend(["-c:a", "copy"])

            cmd_subtitle.append(subbed_file)

        try:
            run_command_with_logging(
                cmd_subtitle, event_hook, prefix="[ffmpeg-subtitle]"
            )
            current_clip = subbed_file
        except subprocess.CalledProcessError as e:
            log.warning(
                "FFmpeg subtitle/video effect filter failed. Falling back to non-subbed video."
            )

    return current_clip
