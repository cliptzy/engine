import os
import asyncio
import subprocess
from typing import Tuple, Dict
import numpy as np

from core.logger import log

# Voice maps available (using Kokoro voices)
VOICE_MAP = {
    "id": {"female": "af_heart", "male": "am_adam"},
    "en": {"female": "af_heart", "male": "am_adam"},
    "es": {"female": "ef_dora", "male": "em_alex"},
    "ja": {"female": "jf_alpha", "male": "jm_kumo"},
    "ko": {"female": "af_heart", "male": "am_adam"},
    "ms": {"female": "af_heart", "male": "am_adam"},
}

_KOKORO_PIPELINES = {}

def _get_pipeline(lang_code: str):
    import torch
    from kokoro import KPipeline
    if lang_code not in _KOKORO_PIPELINES:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        _KOKORO_PIPELINES[lang_code] = KPipeline(lang_code=lang_code, device=device)
    return _KOKORO_PIPELINES[lang_code]

def _run_kokoro_tts(text: str, voice: str, output_path: str, speed: float = 1.0):
    import soundfile as sf
    
    # Extract language code from voice (e.g. 'af_heart' -> 'a')
    lang_code = voice[0] if len(voice) > 0 else 'a'
    
    pipeline = _get_pipeline(lang_code)
    generator = pipeline(text, voice=voice, speed=speed)
    
    audio_chunks = []
    for i, (gs, ps, audio) in enumerate(generator):
        if audio is not None:
            if hasattr(audio, 'numpy'):
                audio = audio.cpu().numpy()
            audio_chunks.append(audio)
            
    if not audio_chunks:
        raise RuntimeError("Kokoro generated no audio chunks.")
        
    final_audio = np.concatenate(audio_chunks)
    sf.write(output_path, final_audio, 24000)


async def generate_tts(text: str, voice: str, output_path: str, rate: str = "+0%") -> float:
    """
    Generate audio from text using Kokoro-TTS and return the duration of the generated audio.
    
    :param text: Text to synthesize.
    :param voice: Voice ID (e.g., 'af_heart').
    :param output_path: Path to save the audio file.
    :param rate: Speed rate (e.g., '+0%', '-25%').
    :return: Duration of the audio in seconds.
    """
    try:
        # Parse rate to speed float. Default is 1.0
        speed = 1.0
        if rate.endswith('%'):
            try:
                rate_val = float(rate[:-1]) / 100.0
                speed = 1.0 + rate_val
            except ValueError:
                pass
                
        await asyncio.to_thread(_run_kokoro_tts, text, voice, output_path, speed)
    except Exception as e:
        log.error(f"Kokoro-TTS failed for text '{text}': {e}")
        # Use gTTS fallback if necessary
        from gtts import gTTS
        lang_map = {'a': 'en', 'b': 'en', 'e': 'es', 'f': 'fr', 'h': 'hi', 'i': 'it', 'j': 'ja', 'p': 'pt', 'z': 'zh'}
        lang = lang_map.get(voice[0], "en") if voice else "en"
        def _run_gtts():
            tts = gTTS(text=text, lang=lang)
            tts.save(output_path)
            
        await asyncio.to_thread(_run_gtts)

    # Get duration using ffprobe
    try:
        def _run_ffprobe():
            return subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    output_path,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True
            )
        res = await asyncio.to_thread(_run_ffprobe)
        duration_sec = float(res.stdout.strip())
        return duration_sec
    except Exception as e:
        log.warning(f"Failed to get audio duration via ffprobe: {e}")
        return 3.0  # Fallback duration
