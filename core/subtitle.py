import os
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

def generate_subtitle(video_file: str, subtitle_file: str, whisper_model: str, event_hook: Optional[Callable[[str, Any], None]] = None) -> bool:
    """
    Generates an ASS subtitle file using Faster-Whisper for the given video.
    Returns True if successful, False otherwise.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log.error("faster_whisper module not found. Please install it.")
        return False
        
    from core.config import config

    def load_and_transcribe():
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
            video_file, 
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
                return False
        else:
            log.error(f"Failed to generate subtitle: {msg}")
            return False

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
Style: Default,{config.subtitle_font},60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,{alignment},10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        with open(subtitle_file, "w", encoding="utf-8") as f:
            f.write(ass_header)
            for segment in segments:
                if not segment.words:
                    continue
                for word_obj in segment.words:
                    word_start = max(0.0, word_obj.start + config.subtitle_delay)
                    word_end = max(0.0, word_obj.end + config.subtitle_delay)
                    start_time = format_ass_time(word_start)
                    end_time = format_ass_time(word_end)
                    text = word_obj.word.strip()
                    if not text:
                        continue
                    
                    if callable(event_hook):
                        try:
                            event_hook("log", f"[whisper] {start_time} --> {end_time} : {text}")
                        except Exception:
                            pass

                    # \fscx50\fscy50 starts size at 50%, \t(0,150,\fscx100\fscy100) animates to 100% over 150ms
                    ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\fscx50\\fscy50\\t(0,150,\\fscx100\\fscy100)}}{text}\n"
                    f.write(ass_line)
                    
    except Exception as e:
        log.error(f"Failed to write subtitle file: {e}")
        return False

    return True
