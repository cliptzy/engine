import os
import subprocess
from typing import Callable, Any, Optional
from core.logger import log

_global_whisper_model = None

def get_whisper_model(whisper_model_name: str, event_hook: Optional[Callable[[str, Any], None]] = None):
    """Loads and caches the Whisper model globally to avoid repeated initializations and VAD state bugs."""
    global _global_whisper_model
    if _global_whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            log.error("faster_whisper module not found. Please install it.")
            return None

        if callable(event_hook):
            try: event_hook("stage", {"stage": "subtitle_model_load"})
            except Exception: pass
            
        from core.config import config
        device = "cuda" if getattr(config, "hw_accel", "cpu").lower() in ["nvidia", "nvenc"] else "cpu"
        
        log.info(f"Loading Faster-Whisper model '{whisper_model_name}' (Global) on {device}...")
        _global_whisper_model = WhisperModel(whisper_model_name, device=device, compute_type="int8")
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

def _transcribe_with_language_sync(model, audio_file: str, word_timestamps: bool, target_lang: Optional[str] = None):
    segments_gen, _ = model.transcribe(
        audio_file,
        language=target_lang,
        condition_on_previous_text=False,
        word_timestamps=word_timestamps,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )
        
    return segments_gen

def generate_subtitle(video_file: str, subtitle_file: str, whisper_model: str, event_hook: Optional[Callable[[str, Any], None]] = None) -> tuple[bool, str, list]:
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

    def load_and_transcribe():
        log.info("[ffmpeg] Mengekstrak audio PCM murni (.wav) untuk memastikan subtitle sinkron 100%...")
            
        cmd_extract = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_file,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_wav
        ]
        
        try:
            subprocess.run(cmd_extract, check=True)
            current_audio = audio_wav
        except Exception as e:
            log.warning(f"Gagal mengekstrak .wav, fallback ke original video: {e}")
            current_audio = video_file
            
        model = get_whisper_model(whisper_model, event_hook)
        if not model:
            return []
        
        log.info("Transcribing audio...")
        if callable(event_hook):
            try: event_hook("stage", {"stage": "subtitle_transcribe"})
            except Exception: pass
            
        segments_gen = _transcribe_with_language_sync(model, current_audio, word_timestamps=True, target_lang=target_lang)
        
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
                    chunks.append(words[i:i + config.subtitle.max_words])
                
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
                            words_data.append({
                                "word": w_text,
                                "start": max(0.0, w.start + config.subtitle.delay),
                                "end": max(0.0, w.end + config.subtitle.delay)
                            })
                    
                    log.info(f"[whisper] {start_time} --> {end_time} : {text}")

                    if config.subtitle.animation == "scale":
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\fscx50\\fscy50\\t(0,150,\\fscx100\\fscy100)}}{text}\n"
                    else:
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
                    f.write(ass_line)
            
            # Combine all text for AI metadata generation
            full_transcript = " ".join([s.text.strip() for s in segments if s.text.strip()])
            
            # Analyze voice levels
            def analyze_voice_levels(wav_path, words):
                import wave, struct, math
                if not os.path.exists(wav_path):
                    return
                try:
                    with wave.open(wav_path, 'r') as w:
                        rate = w.getframerate()
                        nframes = w.getnframes()
                        for word in words:
                            start_f = min(int(word['start'] * rate), nframes-1)
                            end_f = min(int(word['end'] * rate), nframes)
                            num_f = end_f - start_f
                            if num_f <= 0:
                                word['rms'] = 0
                                continue
                            w.setpos(start_f)
                            data = w.readframes(num_f)
                            # Only unpack if 16-bit
                            if w.getsampwidth() == 2:
                                samples = struct.unpack(f'<{num_f}h', data)
                                rms = math.sqrt(sum(s*s for s in samples)/num_f)
                                word['rms'] = rms
                            else:
                                word['rms'] = 0
                                
                    rmss = [w['rms'] for w in words if w['rms'] > 0]
                    if not rmss:
                        return
                    mean_rms = sum(rmss)/len(rmss)
                    
                    yelling_count = 0
                    whispering_count = 0
                    
                    for word in words:
                        r = word.get('rms', 0)
                        if r > mean_rms * 2.0 and r > 3000:
                            word['voice_level'] = 'yelling'
                            yelling_count += 1
                        elif r < mean_rms * 0.4 and r < 2000:
                            word['voice_level'] = 'whispering'
                            whispering_count += 1
                        else:
                            word['voice_level'] = 'normal'
                        
                        # Remove rms key as it's not needed anymore
                        if 'rms' in word:
                            del word['rms']
                            
                    log.info(f"[audio] Deteksi amplitudo selesai: {mean_rms:.1f} RMS rata-rata. Ditemukan {yelling_count} kata berteriak dan {whispering_count} kata berbisik.")
                            
                except Exception as ex:
                    log.warning(f"Voice level analysis failed: {ex}")
            
            analyze_voice_levels(audio_wav, words_data)
                    
    except Exception as e:
        log.error(f"Failed to write subtitle file: {e}")
        return False, "", []

    return True, full_transcript, words_data

def transcribe_audio_file(audio_file: str, whisper_model: str = "small", event_hook: Optional[Callable[[str, Any], None]] = None) -> list:
    """
    Transcribes audio file using Faster-Whisper and returns timestamped segment list.
    """
    model = get_whisper_model(whisper_model, event_hook)
    if not model:
        return []

    if callable(event_hook):
        event_hook("stage", {"stage": "subtitle_transcribe"})

    segments_gen = _transcribe_with_language_sync(model, audio_file, word_timestamps=False)

    results = []
    for s in segments_gen:
        text_clean = s.text.strip()
        if text_clean:
            item = {"start": round(s.start, 2), "end": round(s.end, 2), "text": text_clean}
            results.append(item)
            msg = f"[transcribe] {s.start:.2f}s - {s.end:.2f}s : {text_clean}"
            log.info(msg)

    return results


def write_enriched_ass_file(enriched_transcript: list, subtitle_file: str, event_hook: Optional[Callable[[str, Any], None]] = None):
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
            for i in range(0, len(enriched_transcript), max(1, config.subtitle.max_words)):
                chunks.append(enriched_transcript[i:i + config.subtitle.max_words])
            
            for chunk in chunks:
                if not chunk:
                    continue
                
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
                            
                        if idx == active_idx:
                            # Highlighted word
                            color_hex = w.get("color", "")
                            ass_c = hex_to_ass_color(color_hex)
                            
                            anim = ""
                            reset_anim = ""
                            if config.subtitle.animation == "scale":
                                anim = "\\fscx50\\fscy50\\t(0,150,\\fscx100\\fscy100)"
                                reset_anim = "\\fscx100\\fscy100"
                            
                            line_text += f"{{\\c{ass_c}{anim}}}{word_str}{{\\c{config.subtitle.color}{reset_anim}}} "
                        else:
                            # Normal word
                            line_text += f"{word_str} "
                            
                    line_text = line_text.strip()
                    if line_text:
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{line_text}\n"
                        f.write(ass_line)
                        
            log.info(f"[subtitle] Berhasil menulis ulang ASS subtitle dengan {len(enriched_transcript)} kata yang diperkaya.")
    except Exception as e:
        log.error(f"Failed to write enriched subtitle file: {e}")
