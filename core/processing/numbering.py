import asyncio
import os
import subprocess
from typing import Callable, Optional

from core.config import config
from core.logger import log
from core.processing.utils import get_video_codec_args


def generate_numbering_card(
    number: int,
    moment_name: str,
    output_path: str,
    duration: float = 3.0,
    event_hook: Optional[Callable] = None,
) -> str:
    """
    Generates a short numbering card video for compilation mode.

    Creates a video with black background, large "NOMOR {N}" text,
    the moment name below it, and TTS narration.

    Adapted from generate_intro() in core/processing/stacker.py.

    :param number: The ranking number (e.g. 5, 4, 3, 2, 1).
    :param moment_name: The moment title text (e.g. "Momen Paling Ngakak").
    :param output_path: Path to save the output .mp4 file.
    :param duration: Base duration of the card in seconds (will extend if TTS is longer).
    :param event_hook: Optional event hook for progress reporting.
    :return: Path to the generated numbering card video.
    """
    from core.subtitle import format_ass_time

    out_w = config.out_width or 720
    out_h = config.out_height or 1280
    job_dir = os.path.dirname(output_path)

    tts_template = getattr(
        config.compilation, "tts_template", "Nomor {n}! {name}!"
    )
    use_tts = getattr(config.compilation, "use_tts", True)

    # --- TTS Generation ---
    audio_path: Optional[str] = None
    tts_duration = 0.0

    if use_tts:
        tts_text = tts_template.format(n=number, name=moment_name)

        tts_lang_config = getattr(config, "tts_language", "default")
        tts_gender = getattr(config, "tts_voice", "female")

        if tts_lang_config == "default":
            tts_lang = "id"
        else:
            tts_lang = tts_lang_config

        from core.processing.tts_engine import VOICE_MAP, generate_tts

        base_lang = tts_lang.split("-")[0].lower() if tts_lang else "id"
        if base_lang not in VOICE_MAP:
            base_lang = "en"

        voice = VOICE_MAP[base_lang].get(
            tts_gender.lower(), VOICE_MAP[base_lang]["female"]
        )

        audio_path = os.path.join(job_dir, f"numbering_audio_{number}.mp3")

        try:
            tts_duration = asyncio.run(
                generate_tts(tts_text, voice, audio_path, rate="-25%")
            )
            log.info(
                f"[numbering] TTS generated for card #{number}: {tts_duration:.1f}s"
            )
        except Exception as e:
            log.warning(f"[numbering] TTS failed for card #{number}: {e}")
            audio_path = None

    # Use TTS duration + padding, or fallback to config duration
    card_duration = max(duration, tts_duration + 0.5) if tts_duration > 0 else duration

    # --- ASS Subtitle for Card Text ---
    ass_path = os.path.join(job_dir, f"numbering_{number}.ass")
    end_ass = format_ass_time(card_duration)

    number_text = f"NOMOR {number}"
    # Escape ASS special characters in moment name
    safe_moment = moment_name.replace("\\", "\\\\")

    font_name = config.subtitle.font or "Arial"

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            f"PlayResX: {out_w}\n"
            f"PlayResY: {out_h}\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Number,{font_name},100,&H0000FFFF,&H000000FF,"
            f"&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,0,5,20,20,20,1\n"
            f"Style: Moment,{font_name},50,&H00FFFFFF,&H000000FF,"
            f"&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,5,20,20,20,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        # Number text — centered with scale-in animation
        f.write(
            f"Dialogue: 0,0:00:00.00,{end_ass},Number,,0,0,0,,"
            f"{{\\an5\\b1\\bord5\\3c&H000000&\\fad(300,300)}}{number_text}\n"
        )
        # Moment name — below number, slightly smaller
        f.write(
            f"Dialogue: 0,0:00:00.30,{end_ass},Moment,,0,0,100,,"
            f"{{\\an2\\b1\\bord3\\3c&H000000&\\fad(400,300)}}{safe_moment}\n"
        )

    # --- Generate Video: Black background + ASS + Audio ---
    fontsdir_arg = ""
    if config.subtitle.fonts_dir and os.path.isdir(config.subtitle.fonts_dir):
        fontsdir_fwd = (
            config.subtitle.fonts_dir.replace("\\", "/").replace(":", "\\:")
        )
        fontsdir_arg = f":fontsdir='{fontsdir_fwd}'"

    ass_path_fwd = ass_path.replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={out_w}x{out_h}:d={card_duration}",
    ]

    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])

    cmd.extend(
        [
            "-vf",
            f"subtitles=filename='{ass_path_fwd}'{fontsdir_arg}",
        ]
    )

    cmd.extend(get_video_codec_args())

    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-c:a", "aac", "-b:a", "128k", "-shortest"])
    else:
        # Generate silent audio track for concat compatibility
        cmd.extend(
            [
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo:d={card_duration}",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-shortest",
            ]
        )

    cmd.append(output_path)

    log.info(f"[numbering] Generating card #{number}: '{moment_name}'")
    subprocess.run(cmd, check=True)

    if not os.path.exists(output_path):
        raise RuntimeError(
            f"Failed to generate numbering card #{number}: output file not found"
        )

    log.info(f"[numbering] Card #{number} generated: {output_path}")

    # Cleanup temp files
    for tmp in [ass_path, audio_path]:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

    return output_path
