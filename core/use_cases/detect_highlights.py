import os
from typing import Any, Dict, Optional

from core.config import config
from core.interfaces import ProgressReporter
from core.utils import read_json, write_json
from core.youtube import extract_video_id, get_video_duration
from core.yt_dlp_logger import create_yt_dlp_logger


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
        import os

        is_local = os.path.isfile(url)
        if is_local:
            import hashlib

            base_name = os.path.basename(url)
            safe_name = "".join([c if c.isalnum() else "_" for c in base_name])
            video_id = f"local_{safe_name}_{hashlib.md5(url.encode()).hexdigest()[:6]}"
        else:
            video_id = extract_video_id(url)
            if not video_id:
                raise ValueError("URL YouTube / File lokal tidak valid")

        job_dir = os.path.join("clips", video_id)
        os.makedirs(job_dir, exist_ok=True)

        transcript_cache_file = os.path.join(job_dir, "transcript.json")
        ai_cache_file = os.path.join(job_dir, "ai_segments.json")
        transcript_segments = []

        force_rescan = ai_config.get("force_rescan", False)

        if not force_rescan and os.path.exists(ai_cache_file):
            if self.reporter:
                self.reporter.on_log(
                    f"[AI] Menggunakan hasil AI Scan sebelumnya dari cache."
                )
            return read_json(ai_cache_file)

        if os.path.exists(transcript_cache_file):
            transcript_segments = read_json(transcript_cache_file, default=[])
            if transcript_segments and self.reporter:
                self.reporter.on_log(
                    f"[AI] Menggunakan {len(transcript_segments)} klausa transkrip audio dari cache (skip download & Whisper transcribing)."
                )

        if not transcript_segments:
            if is_local:
                audio_file = url
            else:
                audio_file = os.path.join(job_dir, "audio_full.m4a")
                if not os.path.exists(audio_file):
                    if self.reporter:
                        self.reporter.on_progress("download", 0, 0)
                        self.reporter.on_log("[AI] Mengunduh file audio video...")

                    from typing import Any

                    import yt_dlp

                    ydl_opts: dict[str, Any] = {
                        "force_ipv4": True,
                        "no_warnings": True,
                        "format": "ba[ext=m4a]/ba/b",
                        "outtmpl": audio_file,
                        "logger": create_yt_dlp_logger("[yt-dlp:ai-audio]"),
                    }
                    if config.youtube.session and os.path.exists(
                        config.youtube.session
                    ):
                        ydl_opts["cookiefile"] = config.youtube.session

                    from core.utils import apply_fast_download_opts

                    apply_fast_download_opts(ydl_opts)

                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                            ydl.download([f"https://youtu.be/{video_id}"])
                    except Exception as e:
                        raise RuntimeError(
                            f"Gagal mengunduh audio video untuk transkripsi AI: {e}"
                        )

                    if not os.path.exists(audio_file):
                        raise RuntimeError(
                            "Gagal mengunduh audio video untuk transkripsi AI (file tidak ditemukan)."
                        )

            if self.reporter:
                self.reporter.on_progress("subtitle_transcribe", 0, 0)
                self.reporter.on_log(
                    f"[AI] Mengekstrak transkripsi audio dengan Whisper model ({config.subtitle.whisper_model})..."
                )

            from core.interfaces import create_reporter_hook
            from core.subtitle import transcribe_audio_file

            event_hook_wrapper = create_reporter_hook(self.reporter)

            transcript_segments = transcribe_audio_file(
                audio_file,
                whisper_model=config.subtitle.whisper_model,
                event_hook=event_hook_wrapper,
            )

            if not transcript_segments:
                raise RuntimeError("Gagal mengekstrak transkripsi audio.")

            if write_json(transcript_cache_file, transcript_segments, indent=2):
                if self.reporter:
                    self.reporter.on_log(
                        f"[AI] Transkrip audio lengkap ({len(transcript_segments)} klausa) berhasil disimpan ke cache."
                    )

        if self.reporter:
            self.reporter.on_progress("ai_detect", 0, 0)
            self.reporter.on_log(
                f"[AI] Menganalisis {len(transcript_segments)} klausa ucapan dengan AI Model ({ai_config.get('provider', 'ollama').upper()})..."
            )

        from core.ai.detector import ai_detector
        from core.interfaces import create_reporter_hook

        ai_event_hook = create_reporter_hook(self.reporter)

        highlights = ai_detector.detect_highlights(
            transcript_segments, ai_config, event_hook=ai_event_hook, video_id=video_id
        )

        if is_local:
            from core.use_cases.preview_clip import PreviewClipUseCase

            total_duration = PreviewClipUseCase().execute(url).get("duration", 0)
        else:
            total_duration = get_video_duration(video_id)

        result = {
            "video_id": video_id,
            "duration": total_duration,
            "segments": highlights,
            "transcript_count": len(transcript_segments),
        }

        ai_cache_file = os.path.join(job_dir, "ai_segments.json")
        write_json(ai_cache_file, result, indent=2)

        return result
