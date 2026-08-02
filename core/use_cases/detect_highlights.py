import os
import subprocess
import sys
from typing import Dict, Any, Optional

from core.config import config
from core.youtube import extract_video_id, get_video_duration
from core.utils import read_json, write_json
from core.interfaces import ProgressReporter

class DetectHighlightsUseCase:
    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter

    def execute(self, url: str, ai_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        1. Checks if transcript.json exists (loads from cache if available).
        2. Downloads audio track via yt-dlp if transcript.json is missing.
        3. Transcribes audio to timestamped segments via Faster-Whisper.
        4. Saves complete transcript.json.
        5. Sends transcript to AI Highlight Detector (Ollama / Gemini / OpenAI).
        6. Returns detected highlights.
        """
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("URL YouTube tidak valid")

        job_dir = os.path.join("clips", video_id)
        os.makedirs(job_dir, exist_ok=True)

        transcript_cache_file = os.path.join(job_dir, "transcript.json")
        transcript_segments = []

        if os.path.exists(transcript_cache_file):
            transcript_segments = read_json(transcript_cache_file, default=[])
            if transcript_segments and self.reporter:
                self.reporter.on_log(f"[AI] Menggunakan {len(transcript_segments)} klausa transkrip audio dari cache (skip download & Whisper transcribing).")

        if not transcript_segments:
            audio_file = os.path.join(job_dir, "audio_full.m4a")
            if not os.path.exists(audio_file):
                if self.reporter:
                    self.reporter.on_progress("download", 0, 0)
                    self.reporter.on_log("[AI] Mengunduh file audio video...")

                cmd_audio = [
                    sys.executable, "-m", "yt_dlp",
                    "--force-ipv4", "--quiet", "--no-warnings",
                    "-f", "ba[ext=m4a]/ba/b",
                    "-o", audio_file,
                    f"https://youtu.be/{video_id}"
                ]
                if config.youtube.session and os.path.exists(config.youtube.session):
                    cmd_audio.extend(["--cookies", config.youtube.session])

                res = subprocess.run(cmd_audio)
                if res.returncode != 0 or not os.path.exists(audio_file):
                    raise RuntimeError("Gagal mengunduh audio video untuk transkripsi AI.")

            if self.reporter:
                self.reporter.on_progress("subtitle_transcribe", 0, 0)
                self.reporter.on_log(f"[AI] Mengekstrak transkripsi audio dengan Whisper model ({config.subtitle.whisper_model})...")

            from core.subtitle import transcribe_audio_file
            def event_hook_wrapper(event, data=None):
                if self.reporter:
                    if event == "log":
                        self.reporter.on_log(str(data))
                    elif event == "stage" and data is not None:
                        self.reporter.on_progress(data.get("stage", ""), data.get("clip_index", 0), data.get("total", 0))
            
            transcript_segments = transcribe_audio_file(audio_file, whisper_model=config.subtitle.whisper_model, event_hook=event_hook_wrapper)

            if not transcript_segments:
                raise RuntimeError("Gagal mengekstrak transkripsi audio.")

            if write_json(transcript_cache_file, transcript_segments, indent=2):
                if self.reporter:
                    self.reporter.on_log(f"[AI] Transkrip audio lengkap ({len(transcript_segments)} klausa) berhasil disimpan ke cache.")

        if self.reporter:
            self.reporter.on_progress("ai_detect", 0, 0)
            self.reporter.on_log(f"[AI] Menganalisis {len(transcript_segments)} klausa ucapan dengan AI Model ({ai_config.get('provider', 'ollama').upper()})...")

        from core.ai.detector import ai_detector
        def ai_event_hook(event, data=None):
            if self.reporter:
                if event == "log":
                    self.reporter.on_log(str(data))
                elif event == "stage" and data is not None:
                    self.reporter.on_progress(data.get("stage", ""), data.get("clip_index", 0), data.get("total", 0))

        highlights = ai_detector.detect_highlights(transcript_segments, ai_config, event_hook=ai_event_hook, video_id=video_id)

        total_duration = get_video_duration(video_id)
        result = {
            "video_id": video_id,
            "duration": total_duration,
            "segments": highlights,
            "transcript_count": len(transcript_segments)
        }

        ai_cache_file = os.path.join(job_dir, "ai_segments.json")
        write_json(ai_cache_file, result, indent=2)

        return result
