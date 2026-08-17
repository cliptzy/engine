import asyncio
import os
import subprocess
from typing import Any, Callable, Dict, List, Optional

from core.logger import log
from core.processing.tts_engine import generate_tts
from core.processing.utils import get_video_codec_args, run_command_with_logging
from core.subtitle import format_ass_time


async def process_brainrot(
    job_dir: str,
    b_roll_path: str,
    script_data: List[Dict[str, Any]],
    output_path: str,
    event_hook: Optional[Callable] = None,
) -> str:
    """
    Process Brainrot video.
    script_data format:
    [
        {"speaker": "Spongebob", "text": "Hello", "voice": "en-US-JennyNeural", "image": "path/to/img1.png"},
        ...
    ]
    """
    if not script_data:
        raise ValueError("Script data is empty.")

    log.info("[Brainrot] Generating TTS audio for each dialogue line...")
    if event_hook:
        event_hook("status", "Menghasilkan suara AI (TTS)...")

    # 1. Generate audio for each line
    audio_segments = []
    total_duration = 0.0

    for idx, line in enumerate(script_data):
        import re

        raw_text = line.get("text", "")
        # Hapus tag aksi/emosi dalam kurung dari teks TTS
        text = re.sub(r"\[.*?\]", "", raw_text).strip()

        voice = line.get("voice", "id-ID-ArdiNeural")
        voice_clone = line.get("voice_clone", "")
        image = line.get("image")
        speaker = line.get("speaker", f"Speaker_{idx}")

        audio_path = os.path.join(job_dir, f"br_audio_{idx}.mp3")
        dur = await generate_tts(text, voice, audio_path, rate="+0%", voice_clone_path=voice_clone)

        start_time = total_duration
        end_time = total_duration + dur
        total_duration = end_time

        audio_segments.append(
            {
                "audio": audio_path,
                "text": text,
                "image": image,
                "start": start_time,
                "end": end_time,
                "speaker": speaker,
            }
        )

    # 2. Generate Master Audio
    log.info("[Brainrot] Concatenating audio segments...")
    if event_hook:
        event_hook("status", "Menggabungkan audio master...")

    master_audio_path = os.path.join(job_dir, "br_master_audio.m4a")

    # create a concat file for ffmpeg
    concat_txt_path = os.path.join(job_dir, "br_audio_concat.txt")
    with open(concat_txt_path, "w", encoding="utf-8") as f:
        for seg in audio_segments:
            f.write(f"file '{os.path.abspath(seg['audio']).replace(chr(92), '/')}'\n")

    def _run_concat():
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_txt_path,
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                master_audio_path,
            ],
            check=True,
        )

    await asyncio.to_thread(_run_concat)

    # 3. Generate ASS Subtitle
    log.info("[Brainrot] Generating ASS subtitles...")
    if event_hook:
        event_hook("status", "Membuat subtitle animasi...")

    ass_path = os.path.join(job_dir, "br_subtitles.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n\n")
        f.write(
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        )

        # Style Brainrot (Brutalist: Putih, Highlight Kuning, Outline Hitam Tebal, Drop Shadow Hitam)
        f.write(
            "Style: BRStyle,Arial Black,45,&H0000FFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,5,5,20,20,20,1\n\n"
        )
        f.write(
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

        for seg in audio_segments:
            # 1. Bersihkan teks
            clean_text = seg["text"].strip()
            if not clean_text:
                continue

            # 2. Pisahkan menjadi maksimal 3 kata per baris
            words = clean_text.split()
            chunks = []
            for i in range(0, len(words), 3):
                chunks.append(words[i : i + 3])  # Simpan sebagai list kata

            seg_dur = seg["end"] - seg["start"]
            chunk_duration = seg_dur / len(chunks) if chunks else 0

            for idx, chunk_words in enumerate(chunks):
                chunk_start = seg["start"] + (idx * chunk_duration)
                chunk_end = chunk_start + chunk_duration

                s_ass = format_ass_time(chunk_start)
                e_ass = format_ass_time(chunk_end)

                # Karaoke timing: durasi per kata dalam centiseconds (1 detik = 100 cs)
                word_dur_cs = int((chunk_duration / len(chunk_words)) * 100)

                karaoke_text = ""
                for w in chunk_words:
                    karaoke_text += f"{{\\k{word_dur_cs}}}{w.upper()} "
                karaoke_text = karaoke_text.strip()

                # Tanpa animasi, menggunakan karaoke fill (\k mengubah warna putih (Secondary) ke kuning (Primary))
                f.write(
                    f"Dialogue: 0,{s_ass},{e_ass},BRStyle,,0,0,0,,{{\\q2\\an5}}{karaoke_text}\n"
                )

    # 4. Assemble Final Video with FFmpeg
    log.info("[Brainrot] Assembling final video with FFmpeg...")
    if event_hook:
        event_hook("status", "Merender video akhir...")

    # Randomize B-Roll start time and check for audio
    broll_has_audio = False
    try:
        def _get_broll_info():
            dur_res = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    b_roll_path,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            dur = float(dur_res.stdout.strip())
            
            aud_res = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a",
                    "-show_entries",
                    "stream=codec_name",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    b_roll_path,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            has_aud = len(aud_res.stdout.strip()) > 0
            return dur, has_aud

        broll_dur, broll_has_audio = await asyncio.to_thread(_get_broll_info)
    except Exception as e:
        log.warning(f"Failed to get broll info: {e}")
        broll_dur = 0.0

    import random

    start_offset = 0.0
    if broll_dur > total_duration + 5:
        start_offset = random.uniform(0, broll_dur - total_duration)
    elif broll_dur > 5:
        start_offset = random.uniform(0, broll_dur / 2)

    # Inputs: [0] B-Roll, [1] Master Audio, [2..N] Character Images
    inputs = [
        "-stream_loop",
        "-1",
        "-ss",
        f"{start_offset:.2f}",
        "-i",
        b_roll_path,
        "-i",
        master_audio_path,
    ]
    image_paths = []
    for seg in audio_segments:
        if (
            seg["image"]
            and os.path.isfile(seg["image"])
            and seg["image"] not in image_paths
        ):
            image_paths.append(seg["image"])
            inputs.extend(["-i", seg["image"]])

    filter_complex = []

    # Scale background video to 720x1280 (Shorts format) and trim to audio duration
    out_w, out_h = 720, 1280
    filter_complex.append(
        f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},trim=0:{total_duration},setpts=PTS-STARTPTS[bg];"
    )

    last_v = "[bg]"

    # Overlay character images
    img_idx_map = {path: idx + 2 for idx, path in enumerate(image_paths)}

    overlay_idx = 0
    for seg in audio_segments:
        img_path = seg["image"]
        if not img_path or img_path not in img_idx_map:
            continue

        inp_idx = img_idx_map[img_path]
        s_t = seg["start"]
        e_t = seg["end"]

        # Tampilkan di bawah teks subtitle (misal Y = 800)
        img_w = 300
        img_h = 300
        next_v = f"[v_ov_{overlay_idx}]"

        # Scale image and overlay
        # Adding a jumping effect scale (pop in) if we want, but simple overlay is safer.
        filter_complex.append(
            f"[{inp_idx}:v]scale={img_w}:{img_h}:force_original_aspect_ratio=decrease[img{overlay_idx}];"
        )
        filter_complex.append(
            f"{last_v}[img{overlay_idx}]overlay=(W-w)/2:800:enable='between(t,{s_t},{e_t})'{next_v};"
        )

        last_v = next_v
        overlay_idx += 1

    # Burn subtitle
    ass_path_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
    final_v = "[v_final]"
    filter_complex.append(f"{last_v}subtitles=filename='{ass_path_escaped}'{final_v};")
    
    final_a = "1:a"
    if broll_has_audio:
        filter_complex.append("[0:a]volume=0.2[bg_aud];[bg_aud][1:a]amix=inputs=2:duration=shortest[a_final]")
        final_a = "[a_final]"

    filter_string = "".join(filter_complex).rstrip(";")

    cmd = (
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "info"]
        + inputs
        + ["-filter_complex", filter_string]
        + ["-map", final_v, "-map", final_a]
        + get_video_codec_args()
        + ["-c:a", "aac", "-b:a", "128k", "-shortest", output_path]
    )

    try:

        def _run_ff():
            run_command_with_logging(cmd, event_hook, prefix="[ffmpeg-brainrot]")

        await asyncio.to_thread(_run_ff)
        return output_path
    except Exception as e:
        log.error(f"Brainrot render failed: {e}")
        raise e
