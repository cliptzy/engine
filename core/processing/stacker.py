import os
import shutil
import subprocess
from typing import Callable, Optional

from core.config import config
from core.logger import log
from core.processing.utils import get_video_codec_args, run_command_with_logging


def generate_intro(
    index: int, metadata: dict, event_hook: Optional[Callable] = None
) -> Optional[str]:
    intro_to_use = (
        config.intro_video
        if (config.intro_video and os.path.isfile(config.intro_video))
        else None
    )

    if config.ai.use_generate_intro and metadata and metadata.get("highlight"):
        try:
            log.info(f"[intro] Generating AI Intro with TTS for clip {index}...")

            highlight_text = str(metadata.get("highlight", ""))

            # 1. Generate TTS using edge-tts
            tts_lang_config = getattr(config, "tts_language", "default")
            tts_gender = getattr(config, "tts_voice", "female")

            from core.utils import get_preview_data

            if tts_lang_config == "default":
                tts_lang = get_preview_data().get("language") or "id"
            else:
                tts_lang = tts_lang_config

            from core.processing.tts_engine import generate_tts, VOICE_MAP

            base_lang = tts_lang.split("-")[0].lower() if tts_lang else "id"
            if base_lang not in VOICE_MAP:
                base_lang = "en"  # fallback

            voice = VOICE_MAP[base_lang].get(
                tts_gender.lower(), VOICE_MAP[base_lang]["female"]
            )
            audio_path = os.path.join(config.job_dir, f"intro_audio_{index}.mp3")

            import asyncio
            duration_sec = asyncio.run(generate_tts(highlight_text, voice, audio_path, rate="-25%"))

            # 3. Create ASS for centered highlight text
            intro_ass = os.path.join(config.job_dir, f"intro_{index}.ass")
            from core.subtitle import format_ass_time

            end_ass = format_ass_time(duration_sec + 0.5)  # add little padding

            with open(intro_ass, "w", encoding="utf-8") as f:
                f.write(
                    "[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n\n[V4+ Styles]\n"
                )
                f.write(
                    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                )
                f.write(
                    f"Style: Default,{config.subtitle.font},80,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,5,20,20,20,1\n\n"
                )
                f.write(
                    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                )
                f.write(
                    f"Dialogue: 0,0:00:00.00,{end_ass},Default,,0,0,0,,{{\\an5\\b1\\bord5\\3c&H000000&}}{highlight_text.upper()}\n"
                )

            # 4. Generate black video with ASS and Audio
            intro_video_path = os.path.join(config.job_dir, f"intro_video_{index}.mp4")
            out_w, out_h = config.out_width or 720, config.out_height or 1280
            fontsdir_arg = ""
            if config.subtitle.fonts_dir and os.path.isdir(config.subtitle.fonts_dir):
                fontsdir_fwd = config.subtitle.fonts_dir.replace("\\", "/")
                fontsdir_arg = f":fontsdir='{fontsdir_fwd}'"

            intro_ass_fwd = intro_ass.replace("\\", "/")
            cmd_intro = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s={out_w}x{out_h}:d={duration_sec + 0.5}",
                "-i",
                audio_path,
                "-vf",
                f"subtitles=filename='{intro_ass_fwd}'{fontsdir_arg}",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "26",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-shortest",
                intro_video_path,
            ]
            subprocess.run(cmd_intro, check=True)
            intro_to_use = intro_video_path

        except Exception as e:
            log.error(f"Failed to generate intro video: {e}")

    return intro_to_use


def _has_audio_stream(filepath: str) -> bool:
    try:
        res = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                filepath,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return "audio" in res.stdout.lower()
    except Exception:
        return False


def stack_and_concat(
    current_clip: str,
    output_file: str,
    intro_to_use: Optional[str],
    index: int,
    event_hook: Optional[Callable] = None,
    is_sequential: bool = False,
    is_last_in_queue: bool = False,
) -> None:
    has_intro = intro_to_use and os.path.isfile(intro_to_use)
    has_outro = config.outro_video and os.path.isfile(config.outro_video)
    has_watermark = config.watermark_image and os.path.isfile(config.watermark_image)
    has_seq_outro = is_sequential and not is_last_in_queue

    if has_intro and not _has_audio_stream(str(intro_to_use)):
        log.warning("Intro video lacks audio stream. Ignoring intro.")
        has_intro = False

    if has_outro and not _has_audio_stream(str(config.outro_video)):
        log.warning("Outro video lacks audio stream. Ignoring outro.")
        has_outro = False

    if has_intro or has_outro or has_watermark or has_seq_outro:
        if has_intro or has_outro or has_seq_outro:
            log.info(f"[concat] Adding intro/outro/watermark to clip {index}...")
        else:
            log.info(f"[concat] Adding watermark to clip {index}...")
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "finalize", "clip_index": index})
            except Exception:
                pass

        inputs = []
        filter_complex = ""
        input_idx = 0

        # Since videos might have different resolutions/codecs, we MUST re-encode and scale them to out_w x out_h
        out_w, out_h = config.out_width or 720, config.out_height or 1280
        scale_filter = f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1"

        def add_input(file_path: str, is_main: bool = False):
            nonlocal input_idx, filter_complex
            inputs.extend(["-i", file_path])
            
            if is_main and has_seq_outro:
                try:
                    res = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                        capture_output=True, text=True
                    )
                    dur = float(res.stdout.strip())
                    start_eff = max(0, dur - 5.0)
                    
                    from core.utils import get_app_root
                    font_path = os.path.join(get_app_root(), "assets", "fonts", "Montserrat-Bold.ttf").replace("\\", "/")
                    if not os.path.exists(font_path):
                        font_clause = ""
                    else:
                        font_clause = f"fontfile='{font_path}':"
                        
                    alpha_expr = f"if(lt(t,{start_eff}),0,min(1,(t-{start_eff})/2.0))"
                    
                    vid_filter = (
                        f"[{input_idx}:v:0]{scale_filter}[v_main{input_idx}]; "
                        f"[v_main{input_idx}]split=2[orig{input_idx}][to_blur{input_idx}]; "
                        f"[to_blur{input_idx}]boxblur=20:20,format=rgba,fade=t=in:st={start_eff}:d=2:alpha=1[blurred{input_idx}]; "
                        f"[orig{input_idx}][blurred{input_idx}]overlay=0:0:enable='gte(t,{start_eff})',"
                        f"drawtext={font_clause}text='Lanjut Part':fontcolor=white:fontsize=h/28:x=(w-text_w)/2:y=(h-text_h)/2-h/40:alpha='{alpha_expr}',"
                        f"drawtext={font_clause}text='Berikutnya':fontcolor=white:fontsize=h/28:x=(w-text_w)/2:y=(h-text_h)/2+h/40:alpha='{alpha_expr}'"
                    )
                except Exception as e:
                    log.warning(f"Failed to add sequential outro effect: {e}")
                    vid_filter = f"[{input_idx}:v:0]{scale_filter}"
            else:
                vid_filter = f"[{input_idx}:v:0]{scale_filter}"

            filter_complex += f"{vid_filter}[v{input_idx}]; [{input_idx}:a:0]aresample=async=1[a{input_idx}]; "
            input_idx += 1

        if has_intro and intro_to_use:
            add_input(intro_to_use)

        add_input(current_clip, is_main=True)

        if has_outro and config.outro_video:
            add_input(config.outro_video)

        concat_parts = ""
        for i in range(input_idx):
            concat_parts += f"[v{i}][a{i}]"

        filter_complex += f"{concat_parts}concat=n={input_idx}:v=1:a=1[outv][outa]"
        map_v = "[outv]"

        if has_watermark and config.watermark_image:
            inputs.extend(["-i", config.watermark_image])
            wm_idx = len(inputs) // 2 - 1
            pos = getattr(config, "watermark_position", "center")
            # Safe area constraints
            y_expr = "(H-h)/2"
            if pos == "top":
                y_expr = "H*0.15"
            elif pos == "bottom":
                y_expr = "H*0.75"

            # Scale watermark to max 50% width or original size
            filter_complex += f"; [{wm_idx}:v]scale='min(iw,{out_w}*0.5)':-1[wm_scaled]; [outv][wm_scaled]overlay=x=(W-w)/2:y={y_expr}[outv2]"
            map_v = "[outv2]"

        cmd_concat = (
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "info"]
            + inputs
            + [
                "-filter_complex",
                filter_complex,
                "-map",
                map_v,
                "-map",
                "[outa]",
            ]
            + get_video_codec_args()
            + ["-c:a", "aac", "-b:a", "128k", output_file]
        )

        run_command_with_logging(cmd_concat, event_hook, prefix="[ffmpeg-concat]")
    else:
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "finalize", "clip_index": index})
            except Exception:
                pass
        # Just copy the final result
        if current_clip != output_file:
            shutil.copy2(current_clip, output_file)
