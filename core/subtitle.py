import os
import subprocess
from typing import Any, Callable, Optional

from core.logger import log

_global_whisper_model = None


def get_whisper_model(
    whisper_model_name: str, event_hook: Optional[Callable[[str, Any], None]] = None
):
    """Loads and caches the Whisper model globally to avoid repeated initializations and VAD state bugs."""
    global _global_whisper_model
    if _global_whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            log.error("faster_whisper module not found. Please install it.")
            return None

        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "subtitle_model_load"})
            except Exception:
                pass

        from core.config import config

        device = (
            "cuda"
            if getattr(config, "hw_accel", "cpu").lower() in ["nvidia", "nvenc"]
            else "cpu"
        )

        log.info(
            f"Loading Faster-Whisper model '{whisper_model_name}' (Global) on {device}..."
        )
        _global_whisper_model = WhisperModel(
            whisper_model_name, device=device, compute_type="int8"
        )
        log.info("Model loaded successfully.")
    else:
        log.info(f"Using cached Faster-Whisper model '{whisper_model_name}'.")

    return _global_whisper_model


def format_ass_time(seconds: float) -> str:
    """Converts seconds to ASS timestamp format (H:MM:SS.cs)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds % 1) * 100))
    if centis == 100:
        centis = 0
        secs += 1
        if secs == 60:
            secs = 0
            minutes += 1
            if minutes == 60:
                minutes = 0
                hours += 1
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _transcribe_with_language_sync(
    model, audio_file: str, word_timestamps: bool, target_lang: Optional[str] = None
):
    segments_gen, _ = model.transcribe(
        audio_file,
        language=target_lang,
        condition_on_previous_text=False,
        word_timestamps=word_timestamps,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    return segments_gen


def generate_subtitle(
    video_file: str,
    subtitle_file: str,
    whisper_model: str,
    event_hook: Optional[Callable[[str, Any], None]] = None,
) -> tuple[bool, str, list]:
    """
    Generates an ASS subtitle file using Faster-Whisper for the given video.
    Returns (True, transcript_text, words_data) if successful, (False, "", []) otherwise.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log.error("faster_whisper module not found. Please install it.")
        return False, "", []

    from core.config import config
    from core.utils import get_preview_data

    preview_data = get_preview_data()
    target_lang = preview_data.get("language") if preview_data else None

    audio_wav = video_file + ".wav"

    # WAV extraction hanya diperlukan jika voice analysis (Librosa) aktif.
    # Faster-Whisper bisa membaca video/audio langsung via PyAV internal.
    needs_wav_extraction = (
        getattr(config.ai, "use_voice_analysis", True)
        and config.subtitle.style != "plain"
    )

    def load_and_transcribe():
        if needs_wav_extraction:
            log.info("[ffmpeg] Mengekstrak audio PCM (.wav) untuk Whisper + Voice Analysis...")

            cmd_extract = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                video_file,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                audio_wav,
            ]

            try:
                subprocess.run(cmd_extract, check=True)
                current_audio = audio_wav
            except Exception as e:
                log.warning(f"Gagal mengekstrak .wav, fallback ke original video: {e}")
                current_audio = video_file
        else:
            log.info(
                "Melewati ekstraksi WAV (voice analysis tidak aktif). "
                "Whisper membaca video langsung."
            )
            current_audio = video_file

        model = get_whisper_model(whisper_model, event_hook)
        if not model:
            return []

        log.info("Transcribing audio...")
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "subtitle_transcribe"})
            except Exception:
                pass

        segments_gen = _transcribe_with_language_sync(
            model, current_audio, word_timestamps=True, target_lang=target_lang
        )

        segments = []
        for s in segments_gen:
            msg = f"[whisper-segment] {s.start:.2f}s - {s.end:.2f}s : {s.text}"
            log.info(msg)
            segments.append(s)

        return segments

    try:
        segments = load_and_transcribe()
    except Exception as e:
        msg = str(e)
        if os.name == "nt" and "WinError 1314" in msg:
            log.warning(f"Symlink error detected: {msg}")
            log.info("Retrying transcription (cache fallback)...")
            try:
                segments = load_and_transcribe()
            except Exception as e2:
                log.error(f"Failed to generate subtitle after retry: {e2}")
                return False, "", []
        else:
            log.error(f"Failed to generate subtitle: {msg}")
            return False, "", []

    if callable(event_hook):
        try:
            event_hook("stage", {"stage": "subtitle_write"})
        except Exception as e:
            log.debug(f"Event hook error: {e}")

    log.info("Generating ASS subtitle file...")
    try:
        alignment = "2" if config.subtitle.location == "bottom" else "5"
        margin_v = "200" if config.subtitle.location == "bottom" else "0"

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{config.subtitle.font},{config.subtitle.font_size},{config.subtitle.color},&H000000FF,&H00000000,{config.subtitle.bg_color},-1,0,0,0,100,100,0,0,{config.subtitle.border_style},3,0,{alignment},10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        with open(subtitle_file, "w", encoding="utf-8") as f:
            f.write(ass_header)
            words_data = []
            for segment in segments:
                if not segment.words:
                    continue
                words = segment.words
                chunks = []
                for i in range(0, len(words), max(1, config.subtitle.max_words)):
                    chunks.append(words[i : i + config.subtitle.max_words])

                for chunk in chunks:
                    word_start = max(0.0, chunk[0].start + config.subtitle.delay)
                    word_end = max(0.0, chunk[-1].end + config.subtitle.delay)

                    # Prevent stuck subtitle if Whisper fails to detect proper end boundary
                    if word_end - word_start > 2.0:
                        word_end = word_start + 2.0
                    start_time = format_ass_time(word_start)
                    end_time = format_ass_time(word_end)
                    text = " ".join([w.word.strip() for w in chunk if w.word.strip()])
                    if not text:
                        continue

                    for w in chunk:
                        w_text = w.word.strip()
                        if w_text:
                            words_data.append(
                                {
                                    "word": w_text,
                                    "start": max(0.0, w.start + config.subtitle.delay),
                                    "end": max(0.0, w.end + config.subtitle.delay),
                                }
                            )

                    log.info(f"[whisper] {start_time} --> {end_time} : {text}")

                    if config.subtitle.animation in ["scale", "hormozi"]:
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\fscx50\\fscy50\\t(0,150,\\fscx100\\fscy100)}}{text}\n"
                    else:
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
                    f.write(ass_line)

            # Combine all text for AI metadata generation
            full_transcript = " ".join(
                [s.text.strip() for s in segments if s.text.strip()]
            )

            # Analyze text emotions per segment
            if getattr(config.ai, "use_text_analysis", True) and config.subtitle.style != "plain":
                from core.processing.text_analyzer import analyze_text_emotions

                analyze_text_emotions(
                    segments, words_data, language=target_lang if target_lang else "auto"
                )

            # Analyze voice levels
            if getattr(config.ai, "use_voice_analysis", True) and config.subtitle.style != "plain":
                from core.processing.voice_analyzer import analyze_voice_emotions

                analyze_voice_emotions(
                    audio_wav, words_data, language=target_lang if target_lang else "auto"
                )

    except Exception as e:
        log.error(f"Failed to write subtitle file: {e}")
        return False, "", []

    return True, full_transcript, words_data


def transcribe_audio_file(
    audio_file: str,
    whisper_model: str = "small",
    event_hook: Optional[Callable[[str, Any], None]] = None,
) -> list:
    """
    Transcribes audio file using Faster-Whisper and returns timestamped segment list.
    """
    model = get_whisper_model(whisper_model, event_hook)
    if not model:
        return []

    if callable(event_hook):
        event_hook("stage", {"stage": "subtitle_transcribe"})

    segments_gen = _transcribe_with_language_sync(
        model, audio_file, word_timestamps=False
    )

    results = []
    for s in segments_gen:
        text_clean = s.text.strip()
        if text_clean:
            item = {
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": text_clean,
            }
            results.append(item)
            msg = f"[transcribe] {s.start:.2f}s - {s.end:.2f}s : {text_clean}"
            log.info(msg)

    return results


def write_enriched_ass_file(
    enriched_transcript: list,
    subtitle_file: str,
    event_hook: Optional[Callable[[str, Any], None]] = None,
):
    from core.config import config

    alignment = "2" if config.subtitle.location == "bottom" else "5"
    margin_v = "200" if config.subtitle.location == "bottom" else "0"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{config.subtitle.font},{config.subtitle.font_size},{config.subtitle.color},&H000000FF,&H00000000,{config.subtitle.bg_color},-1,0,0,0,100,100,0,0,{config.subtitle.border_style},3,0,{alignment},10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def hex_to_ass_color(hex_color: str) -> str:
        if not hex_color or not hex_color.startswith("#"):
            return config.subtitle.color
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"&H00{b}{g}{r}&"
        return config.subtitle.color

    try:
        with open(subtitle_file, "w", encoding="utf-8") as f:
            f.write(ass_header)

            chunks = []
            for i in range(
                0, len(enriched_transcript), max(1, config.subtitle.max_words)
            ):
                chunks.append(enriched_transcript[i : i + config.subtitle.max_words])

            for chunk in chunks:
                if not chunk:
                    continue

                is_plain = config.subtitle.style == "plain"

                # Create multiple lines per chunk for active word highlighting
                for active_idx, active_word in enumerate(chunk):
                    start_s = float(active_word.get("start", 0))
                    end_s = float(active_word.get("end", 0))

                    if end_s < start_s:
                        end_s = start_s + 0.5

                    start_time = format_ass_time(start_s)
                    end_time = format_ass_time(end_s)

                    line_text = ""
                    for idx, w in enumerate(chunk):
                        word_str = w.get("word", "").strip()
                        if not word_str:
                            continue

                        is_hormozi = config.subtitle.animation == "hormozi"
                        is_plain = config.subtitle.style == "plain"

                        if is_plain and not is_hormozi:
                            # Plain style: no emotion color, no uppercase, no animation
                            line_text += f"{word_str} "
                            continue

                        # Full Color / Hormozi style: emotion-aware rendering
                        is_angry = str(w.get("emotion", "")).lower() == "angry"
                        if is_angry or is_hormozi:
                            word_str = word_str.upper()

                        if idx == active_idx:
                            # Highlighted word
                            color_hex = w.get("color", "")
                            ass_c = hex_to_ass_color(color_hex)
                            
                            if is_hormozi:
                                # Hormozi removes emotion color, always uses yellow
                                ass_c = "&H0000FFFF"
                                
                            anim = ""
                            reset_anim = "\\fscx100\\fscy100"
                            target_scale = 130 if is_angry else (115 if is_hormozi else 100)

                            if config.subtitle.animation == "scale" or is_hormozi:
                                anim = f"\\fscx50\\fscy50\\t(0,150,\\fscx{target_scale}\\fscy{target_scale})"
                            elif is_angry:
                                anim = f"\\fscx{target_scale}\\fscy{target_scale}"

                            line_text += f"{{\\c{ass_c}{anim}}}{word_str}{{\\c{config.subtitle.color}{reset_anim}}} "
                        else:
                            # Normal word
                            line_text += f"{word_str} "

                    line_text = line_text.strip()
                    if line_text:
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{line_text}\n"
                        f.write(ass_line)

            log.info(
                f"[subtitle] Berhasil menulis ulang ASS subtitle dengan {len(enriched_transcript)} kata yang diperkaya."
            )
    except Exception as e:
        log.error(f"Failed to write enriched subtitle file: {e}")


def write_debug_ass_file(metadata: dict, debug_file: str) -> bool:
    """Writes an ASS file containing debug information (emotion and voice level) per second."""
    from core.config import config

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DebugInfo,Consolas,35,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,3,0,8,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    try:
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(ass_header)

            enriched = metadata.get("enriched_transcript", [])
            visual_emotions = metadata.get("visual_emotions", [])

            timeline = {}

            def add_to_timeline(start_s, end_s, text):
                start_sec = int(start_s)
                end_sec = int(end_s)
                if end_sec < start_sec:
                    end_sec = start_sec
                for sec in range(start_sec, end_sec + 1):
                    if sec not in timeline:
                        timeline[sec] = []
                    if text not in timeline[sec]:
                        timeline[sec].append(text)

            for w in enriched:
                s = float(w.get("start", 0))
                e = float(w.get("end", 0))
                emo = w.get("emotion", "neutral")
                voice = w.get("voice_emotion", "neutral")
                info = f"TEKS: emo={emo}, suara={voice}"
                add_to_timeline(s, e, info)

            for ve in visual_emotions:
                s = float(ve.get("time", 0))
                emo = ve.get("emotion", "neutral")
                score = ve.get("score")
                if score is not None:
                    info = f"VISUAL: emo={emo} ({score}%)"
                else:
                    info = f"VISUAL: emo={emo}"
                add_to_timeline(s, s + 1.0, info)

            max_sec = max(timeline.keys()) if timeline else 0
            for sec in range(0, max_sec + 1):
                if sec not in timeline:
                    timeline[sec] = [
                        "VISUAL: emo=neutral | TEKS: emo=neutral, nada=normal"
                    ]

            for sec in sorted(timeline.keys()):
                infos = " | ".join(timeline[sec])
                text = f"Detik {sec:02d}: {infos}"

                start_time = format_ass_time(sec)
                end_time = format_ass_time(sec + 0.99)

                ass_line = (
                    f"Dialogue: 9,{start_time},{end_time},DebugInfo,,0,0,0,,{text}\n"
                )
                f.write(ass_line)

        return True
    except Exception as e:
        from core.logger import log

        log.error(f"Failed to write debug subtitle file: {e}")
        return False
