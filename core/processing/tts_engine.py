import os
import asyncio
import subprocess
import edge_tts
from typing import Tuple, Dict

from core.logger import log

# Voice maps available
VOICE_MAP = {
    "id": {"female": "id-ID-GadisNeural", "male": "id-ID-ArdiNeural"},
    "en": {"female": "en-US-JennyNeural", "male": "en-US-ChristopherNeural"},
    "es": {"female": "es-ES-ElviraNeural", "male": "es-MX-JorgeNeural"},
    "ja": {"female": "ja-JP-NanamiNeural", "male": "ja-JP-KeitaNeural"},
    "ko": {"female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"},
    "ms": {"female": "ms-MY-YasminNeural", "male": "ms-MY-OsmanNeural"},
}


async def generate_tts(text: str, voice: str, output_path: str, rate: str = "+0%") -> float:
    """
    Generate audio from text using edge_tts and return the duration of the generated audio.
    
    :param text: Text to synthesize.
    :param voice: Voice ID (e.g., 'en-US-ChristopherNeural').
    :param output_path: Path to save the audio file.
    :param rate: Speed rate (e.g., '+0%', '-25%').
    :return: Duration of the audio in seconds.
    """
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_path)
    except Exception as e:
        log.error(f"edge-tts failed for text '{text}': {e}")
        # Use gTTS fallback if necessary, though edge_tts is preferred
        from gtts import gTTS
        lang = voice.split("-")[0].lower() if "-" in voice else "en"
        tts = gTTS(text=text, lang=lang)
        tts.save(output_path)

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
