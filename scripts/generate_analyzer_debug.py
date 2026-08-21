import csv
import os
import subprocess
from typing import Callable, Optional

from core.logger import log
from core.processing.utils import run_command_with_logging


def generate_analyzer_debug(
    input_file: str, output_file: str, event_hook: Optional[Callable] = None
) -> bool:
    if not os.path.exists(input_file):
        log.error("Input file not found.")
        return False

    try:
        from core.processing.emotion_analyzer import analyze_video_emotions
        from core.processing.text_analyzer import analyze_text_emotions
        from core.processing.voice_analyzer import analyze_voice_emotions
        from core.subtitle import (
            _transcribe_with_language_sync,
            format_ass_time,
            get_whisper_model,
        )

        # 1. Ekstrak audio
        audio_wav = input_file + ".debug.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                input_file,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                audio_wav,
            ],
            check=True,
        )

        # 2. Transcribe
        log.info("Mulai transkripsi Whisper untuk debug...")
        model = get_whisper_model("large-v3-turbo")
        segments_gen = _transcribe_with_language_sync(
            model, audio_wav, word_timestamps=True, target_lang="id"
        )

        segments = []
        words_data = []
        for s in segments_gen:
            segments.append(s)
            if s.words:
                for w in s.words:
                    if w.word.strip():
                        words_data.append(
                            {"word": w.word.strip(), "start": w.start, "end": w.end}
                        )

        # 3. Analyze Text
        log.info("Mulai analisis emosi teks...")
        analyze_text_emotions(segments, words_data, "id")

        # 4. Analyze Voice
        log.info("Mulai analisis emosi suara...")
        analyze_voice_emotions(audio_wav, words_data, "id")

        # 5. Analyze Visual
        log.info("Mulai analisis emosi visual...")
        visual_emotions = analyze_video_emotions(input_file, crop_mode="raw")

        # 6. Buat file ASS untuk overlay
        ass_events = []

        # Event Suara & Teks
        for w in words_data:
            s_ass = format_ass_time(w["start"])
            e_ass = format_ass_time(w["end"])
            txt_emo = w.get("text_emotion", "N/A")
            voi_emo = w.get("voice_emotion", "N/A")

            text = f"TEXT: {txt_emo.upper()} | VOICE: {voi_emo.upper()} [{w['word']}]"
            ass_events.append(
                f"Dialogue: 0,{s_ass},{e_ass},OverlayStyle,,0,0,0,,{text}\n"
            )

        # Event Visual
        for i, ve in enumerate(visual_emotions):
            t = float(ve.get("time", 0.0))
            next_t = (
                float(visual_emotions[i + 1].get("time", t + 1.0))
                if i + 1 < len(visual_emotions)
                else t + 1.0
            )

            s_ass = format_ass_time(t)
            e_ass = format_ass_time(next_t)

            emo = ve.get("emotion", "N/A")
            score = ve.get("score", 0.0)

            text = f"VISUAL: {emo.upper()} ({score}%)"
            ass_events.append(
                f"Dialogue: 1,{s_ass},{e_ass},VisualStyle,,0,0,0,,{text}\n"
            )

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: OverlayStyle,Consolas,35,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,3,0,7,20,20,20,1
Style: VisualStyle,Consolas,35,&H0000FF00,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,3,0,7,20,20,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        ass_file = input_file + ".debug.ass"
        with open(ass_file, "w", encoding="utf-8") as f:
            f.write(ass_header)
            for ev in ass_events:
                f.write(ev)

        # 7. Siapkan Filter FFmpeg untuk drawbox dan subtitles
        log.info("Merender video debug dengan overlay...")
        ass_file_fwd = ass_file.replace("\\", "/").replace(":", "\\:")

        vf_filters = [f"subtitles=filename='{ass_file_fwd}'"]
        for i, ve in enumerate(visual_emotions):
            if len(vf_filters) >= 85:  # Limit filters to avoid Command Line Too Long
                break
            box = ve.get("box", {})
            if box:
                x, y, w, h = (
                    box.get("x", 0),
                    box.get("y", 0),
                    box.get("w", 0),
                    box.get("h", 0),
                )
                if w > 0 and h > 0:
                    t = float(ve.get("time", 0.0))
                    next_t = (
                        float(visual_emotions[i + 1].get("time", t + 1.0))
                        if i + 1 < len(visual_emotions)
                        else t + 1.0
                    )
                    vf_filters.append(
                        f"drawbox=x={x}:y={y}:w={w}:h={h}:color=red@0.8:thickness=4:enable='between(t,{t},{next_t})'"
                    )

        vf_string = ",".join(vf_filters)

        # Pastikan tidak encode audio ulang agar cepat, cukup copy
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "info",
            "-i",
            input_file,
            "-vf",
            vf_string,
            "-c:a",
            "copy",
            output_file,
        ]
        run_command_with_logging(cmd, event_hook, prefix="[ffmpeg-debug]")

        # 8. Generate Grafik Alur Emosi
        try:
            from gui.views.debugger_view import generate_emotion_chart_png

            text_data = [
                {"time": w["start"], "emotion": w.get("text_emotion", "unknown")}
                for w in words_data
                if w.get("text_emotion")
            ]
            voice_data = [
                {"time": w["start"], "event": w.get("voice_emotion", "unknown")}
                for w in words_data
                if w.get("voice_emotion")
            ]

            chart_output = os.path.splitext(output_file)[0] + "_chart.png"
            log.info(f"Generating emotion chart at {chart_output}")
            generate_emotion_chart_png(
                visual_emotions, text_data, voice_data, chart_output
            )
        except Exception as e:
            log.error(f"Gagal memanggil generate_emotion_chart_png: {e}")

        # 9. Generate CSV Timeline
        try:
            csv_output = os.path.splitext(output_file)[0] + "_timeline.csv"
            events = []
            
            for w in words_data:
                events.append({
                    "time": w["start"],
                    "type": "word",
                    "content": w["word"],
                    "text_emotion": w.get("text_emotion", "N/A"),
                    "voice_emotion": w.get("voice_emotion", "N/A"),
                    "visual_emotion": "",
                    "visual_score": ""
                })
                
            for v in visual_emotions:
                events.append({
                    "time": v.get("time", 0.0),
                    "type": "visual",
                    "content": str(v.get("box", "")),
                    "text_emotion": "",
                    "voice_emotion": "",
                    "visual_emotion": v.get("emotion", "N/A"),
                    "visual_score": v.get("score", 0.0)
                })
                
            events.sort(key=lambda x: float(x["time"]))
            
            with open(csv_output, mode="w", newline="", encoding="utf-8") as f:
                fieldnames = ["time", "type", "content", "text_emotion", "voice_emotion", "visual_emotion", "visual_score"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for ev in events:
                    writer.writerow(ev)
            log.info(f"Berhasil mengekspor debug CSV ke {csv_output}")
        except Exception as e:
            log.error(f"Gagal mengekspor debug CSV: {e}")

        # Cleanup
        try:
            os.remove(audio_wav)
            os.remove(ass_file)
        except Exception:
            pass

        return True
    except Exception as e:
        log.error(f"Gagal generate analyzer debug: {e}")
        return False
