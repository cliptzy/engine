import os
import subprocess
from typing import Callable, Any, Optional
from core.logger import log

def format_ass_time(seconds: float) -> str:
    """Converts seconds to ASS timestamp format (H:MM:SS.cs)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds % 1) * 100))
    # Handle rounding overflow
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

def generate_subtitle(video_file: str, subtitle_file: str, whisper_model: str, event_hook: Optional[Callable[[str, Any], None]] = None) -> tuple[bool, str]:
    """
    Generates an ASS subtitle file using Faster-Whisper for the given video.
    Returns (True, transcript_text) if successful, (False, "") otherwise.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log.error("faster_whisper module not found. Please install it.")
        return False, ""
        
    from core.config import config

    def load_and_transcribe():
        audio_wav = video_file + ".wav"
        if callable(event_hook):
            try:
                event_hook("log", "[ffmpeg] Mengekstrak audio PCM murni (.wav) untuk memastikan subtitle sinkron 100%...")
            except Exception: pass
            
        cmd_extract = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_file,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_wav
        ]
        
        try:
            subprocess.run(cmd_extract, check=True)
        except Exception as e:
            log.warning(f"Gagal mengekstrak .wav, fallback ke original video: {e}")
            audio_wav = video_file
            
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "subtitle_model_load"})
            except Exception as e:
                log.debug(f"Event hook error: {e}")
                
        log.info(f"Loading Faster-Whisper model '{whisper_model}'...")
        model = WhisperModel(whisper_model, device="cpu", compute_type="int8")
        
        log.info("Model loaded. Transcribing audio...")
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "subtitle_transcribe"})
            except Exception as e:
                log.debug(f"Event hook error: {e}")
                
        segments_gen, info = model.transcribe(
            audio_wav, 
            language="id",
            initial_prompt="Berikut adalah cuplikan video dengan ucapan bahasa Indonesia santai dan gaul yang diucapkan dengan cepat:",
            condition_on_previous_text=False,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        segments = []
        for s in segments_gen:
            if callable(event_hook):
                try:
                    event_hook("log", f"[whisper-segment] {s.start:.2f}s - {s.end:.2f}s : {s.text}")
                except Exception:
                    pass
            segments.append(s)
            
        if audio_wav != video_file and os.path.exists(audio_wav):
            try:
                os.remove(audio_wav)
            except Exception:
                pass
                
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
                return False, ""
        else:
            log.error(f"Failed to generate subtitle: {msg}")
            return False, ""

    if callable(event_hook):
        try:
            event_hook("stage", {"stage": "subtitle_write"})
        except Exception as e:
            log.debug(f"Event hook error: {e}")
            
    log.info("Generating ASS subtitle file...")
    try:
        alignment = "2" if config.subtitle_location == "bottom" else "5"
        margin_v = "200" if config.subtitle_location == "bottom" else "0"
        
        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{config.subtitle_font},{config.subtitle_font_size},{config.subtitle_color},&H000000FF,&H00000000,{config.subtitle_bg_color},-1,0,0,0,100,100,0,0,{config.subtitle_border_style},3,0,{alignment},10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        with open(subtitle_file, "w", encoding="utf-8") as f:
            f.write(ass_header)
            for segment in segments:
                if not segment.words:
                    continue
                words = segment.words
                chunks = []
                for i in range(0, len(words), max(1, config.subtitle_max_words)):
                    chunks.append(words[i:i + config.subtitle_max_words])
                
                for chunk in chunks:
                    word_start = max(0.0, chunk[0].start + config.subtitle_delay)
                    word_end = max(0.0, chunk[-1].end + config.subtitle_delay)
                    
                    # Prevent stuck subtitle if Whisper fails to detect proper end boundary
                    if word_end - word_start > 2.0:
                        word_end = word_start + 2.0
                    start_time = format_ass_time(word_start)
                    end_time = format_ass_time(word_end)
                    text = " ".join([w.word.strip() for w in chunk if w.word.strip()])
                    if not text:
                        continue
                    
                    if callable(event_hook):
                        try:
                            event_hook("log", f"[whisper] {start_time} --> {end_time} : {text}")
                        except Exception:
                            pass

                    if config.subtitle_animation == "scale":
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\fscx50\\fscy50\\t(0,150,\\fscx100\\fscy100)}}{text}\n"
                    else:
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
                    f.write(ass_line)
            
            # Combine all text for AI metadata generation
            full_transcript = " ".join([s.text.strip() for s in segments if s.text.strip()])
                    
    except Exception as e:
        log.error(f"Failed to write subtitle file: {e}")
        return False, ""

    return True, full_transcript

def transcribe_audio_file(audio_file: str, whisper_model: str = "small", event_hook: Optional[Callable[[str, Any], None]] = None) -> list:
    """
    Transcribes audio file using Faster-Whisper and returns timestamped segment list.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log.error("faster_whisper module not found.")
        return []

    if callable(event_hook):
        event_hook("stage", {"stage": "subtitle_model_load"})

    log.info(f"Loading Faster-Whisper model '{whisper_model}' for audio transcription...")
    model = WhisperModel(whisper_model, device="cpu", compute_type="int8")

    if callable(event_hook):
        event_hook("stage", {"stage": "subtitle_transcribe"})

    segments_gen, _ = model.transcribe(
        audio_file,
        language="id",
        condition_on_previous_text=False,
        word_timestamps=False,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    results = []
    for s in segments_gen:
        text_clean = s.text.strip()
        if text_clean:
            item = {"start": round(s.start, 2), "end": round(s.end, 2), "text": text_clean}
            results.append(item)
            if callable(event_hook):
                event_hook("log", f"[transcribe] {s.start:.2f}s - {s.end:.2f}s : {text_clean}")

    return results

