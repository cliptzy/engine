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
_KANADE_MODEL = None
_VOCODER = None

def _get_pipeline(lang_code: str):
    import torch
    from kokoro import KPipeline
    if lang_code not in _KOKORO_PIPELINES:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        _KOKORO_PIPELINES[lang_code] = KPipeline(lang_code=lang_code, device=device)
    return _KOKORO_PIPELINES[lang_code]

def _get_kanade_model():
    global _KANADE_MODEL, _VOCODER
    import torch
    from kanade_tokenizer import KanadeModel, load_vocoder  # type: ignore
    if _KANADE_MODEL is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        _KANADE_MODEL = KanadeModel.from_pretrained("frothywater/kanade-12.5hz").to(device).eval()
        _VOCODER = load_vocoder(_KANADE_MODEL.config.vocoder_name).to(device)
    return _KANADE_MODEL, _VOCODER

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

async def generate_tts(text: str, voice: str, output_path: str, rate: str = "+0%", voice_clone_path: str = "", pitch: str = "+0Hz") -> float:
    """
    Generate audio from text using Kokoro-TTS and return the duration of the generated audio.
    
    :param text: Text to synthesize.
    :param voice: Voice ID (e.g., 'af_heart').
    :param output_path: Path to save the audio file.
    :param rate: Speed rate (e.g., '+0%', '-25%').
    :param voice_clone_path: Path to the reference audio for voice cloning.
    :param pitch: Pitch shift (e.g., '+0Hz', '+10Hz').
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
        
    if voice_clone_path and os.path.exists(voice_clone_path):
        try:
            import torch
            import soundfile as sf
            from kanade_tokenizer import load_audio  # type: ignore
            from core.processing.chunked_convert import chunked_voice_conversion
            
            def _run_voice_clone():
                kanade, vocoder = _get_kanade_model()
                device = next(kanade.parameters()).device
                sample_rate = kanade.config.sample_rate
                
                source_wav = load_audio(output_path, sample_rate=sample_rate).to(device)  # type: ignore
                ref_wav = load_audio(voice_clone_path, sample_rate=sample_rate).to(device)  # type: ignore
                
                with torch.inference_mode():
                    converted_wav = chunked_voice_conversion(
                        kanade=kanade,
                        vocoder_model=vocoder,
                        source_wav=source_wav,
                        ref_wav=ref_wav,
                        sample_rate=sample_rate
                    )
                
                sf.write(output_path, converted_wav.numpy(), sample_rate)
            
            log.info(f"Applying voice clone from {voice_clone_path}...")
            await asyncio.to_thread(_run_voice_clone)
        except Exception as e:
            log.error(f"Voice cloning failed: {e}")

    if pitch and pitch not in ("+0Hz", "0Hz", "0"):
        temp_path = ""
        try:
            pitch_val = float(pitch.replace("Hz", "").replace("+", ""))
            pitch_shift = 1.0 + (pitch_val / 100.0)
            if pitch_shift <= 0.1:
                pitch_shift = 0.1
            
            temp_path = output_path + ".temp.wav"
            if os.path.exists(output_path):
                os.rename(output_path, temp_path)
                
                def _run_pitch_shift():
                    subprocess.run([
                        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-i", temp_path,
                        "-filter:a", f"asetrate=24000*{pitch_shift},atempo=1/{pitch_shift}",
                        output_path
                    ], check=True)
                
                log.info(f"Applying pitch shift: {pitch_shift}")
                await asyncio.to_thread(_run_pitch_shift)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception as e:
            log.error(f"Failed to apply pitch shift: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path) and not os.path.exists(output_path):
                os.rename(temp_path, output_path)

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
