import os
import json
import subprocess
import sys
import shutil
import threading
from typing import Dict, Any, List, Optional, Tuple, Callable

from core.config import config
from core.logger import log
from core.utils import check_dependencies, is_ffmpeg_available
from core.youtube import extract_video_id, fetch_most_replayed, get_video_duration
from core.processor import process_single_clip

_preview_lock = threading.Lock()
_preview_cache: Dict[str, Dict[str, Any]] = {}

def parse_time_to_seconds(value: Any) -> Optional[int]:
    """Parses time input (int, float, MM:SS, HH:MM:SS) into seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    parts = s.split(":")
    if len(parts) == 2:
        try:
            return int(parts[0]) * 60 + int(float(parts[1]))
        except ValueError:
            return None
    if len(parts) == 3:
        try:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
        except ValueError:
            return None
    return None

class ClipController:
    """
    Central Controller layer for Cliptzy.
    Decouples business logic, API processing, and job execution from Flask/HTTP web servers.
    """

    def __init__(self):
        config.load_from_file()

    def get_preview(self, url: str) -> Dict[str, Any]:
        """Fetches metadata (title, thumbnail, duration, uploader) for a YouTube URL."""
        url_clean = url.strip()
        if not url_clean:
            raise ValueError("URL YouTube tidak boleh kosong")

        with _preview_lock:
            cached = _preview_cache.get(url_clean)
            if cached:
                return cached

        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--skip-download",
            "-J",
        ]
        
        if config.cookies_file and os.path.exists(config.cookies_file):
            cmd.extend(["--cookies", config.cookies_file])
            
        cmd.append(url_clean)
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            err_msg = (res.stderr or res.stdout or "Gagal mengambil metadata video").strip()
            raise RuntimeError(err_msg)

        raw = json.loads(res.stdout)
        item = raw["entries"][0] if isinstance(raw, dict) and "entries" in raw and raw.get("entries") else raw

        preview = {
            "title": item.get("title", "Unknown Title"),
            "thumbnail": item.get("thumbnail"),
            "uploader": item.get("uploader", "Unknown Uploader"),
            "duration": item.get("duration", 0),
            "webpage_url": item.get("webpage_url") or url_clean,
            "id": item.get("id"),
        }

        with _preview_lock:
            _preview_cache[url_clean] = preview
            if len(_preview_cache) > 200:
                _preview_cache.clear()

        return preview

    def scan_segments(self, url: str) -> Dict[str, Any]:
        """Scans YouTube video for heatmap segments and returns total duration and heatmap segments."""
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("URL YouTube tidak valid")

        if not is_ffmpeg_available():
            ok = check_dependencies(install_whisper=False, skip_update_ytdlp=True, fatal=False)
            if not ok:
                raise RuntimeError("FFmpeg tidak ditemukan di sistem")

        job_dir = os.path.join("clips", video_id)
        os.makedirs(job_dir, exist_ok=True)
        cache_file = os.path.join(job_dir, "segments.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data_cache = json.load(f)
                    return {
                        "video_id": video_id,
                        "duration": data_cache.get("duration", 0),
                        "segments": data_cache.get("segments", [])
                    }
            except Exception:
                pass

        segments = fetch_most_replayed(video_id, config.min_score, config.max_duration)
        total_duration = get_video_duration(video_id)
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"duration": total_duration, "segments": segments}, f)
        except Exception as e:
            log.warning(f"Gagal menyimpan cache segments.json: {e}")
            
        return {"video_id": video_id, "duration": total_duration, "segments": segments}

    def get_cached_ai_highlights(self, url: str) -> Optional[Dict[str, Any]]:
        video_id = extract_video_id(url)
        if not video_id:
            return None
        job_dir = os.path.join("clips", video_id)
        ai_cache_file = os.path.join(job_dir, "ai_segments.json")
        if os.path.exists(ai_cache_file):
            try:
                with open(ai_cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def execute_clipping(
        self,
        payload: Dict[str, Any],
        event_hook: Optional[Callable[[str, Any], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes the clipping pipeline based on settings payload.
        """
        url = (payload.get("url") or "").strip()
        if not url:
            raise ValueError("URL YouTube tidak boleh kosong")

        crop = payload.get("crop") or "default"
        ratio = payload.get("ratio") or "9:16"
        subtitle = bool(payload.get("subtitle"))
        whisper_model = payload.get("whisper_model") or "small"
        subtitle_font = payload.get("subtitle_font") or "Arial"
        subtitle_location = payload.get("subtitle_location") or "bottom"
        subtitle_fontsdir = payload.get("subtitle_fontsdir") or None
        
        try:
            subtitle_delay = float(payload.get("subtitle_delay") or 0.0)
        except (ValueError, TypeError):
            subtitle_delay = 0.0
            
        subtitle_font_size = payload.get("subtitle_font_size") or 60
        subtitle_color = payload.get("subtitle_color") or "&H0000FFFF"
        subtitle_bg_color = payload.get("subtitle_bg_color") or "&H80000000"
        subtitle_border_style = payload.get("subtitle_border_style")
        if subtitle_border_style is None:
            subtitle_border_style = 3
        subtitle_animation = payload.get("subtitle_animation") or "none"
        subtitle_max_words = payload.get("subtitle_max_words") or 3
            
        if not subtitle_fontsdir and os.path.isdir("fonts"):
            subtitle_fontsdir = "fonts"
            
        padding = payload.get("padding") if payload.get("padding") is not None else 10
        max_clips = payload.get("max_clips") if payload.get("max_clips") is not None else 10
        mode = payload.get("mode") or "heatmap"
        
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("URL YouTube tidak valid")

        # Update application global configuration
        config.whisper_model = whisper_model
        config.subtitle_font = subtitle_font
        config.subtitle_fonts_dir = subtitle_fontsdir
        config.subtitle_location = subtitle_location
        config.subtitle_delay = subtitle_delay / 1000.0 if subtitle_delay > 10 else subtitle_delay # Convert ms to s if > 10
        
        config.subtitle_font_size = int(subtitle_font_size)
        config.subtitle_color = str(subtitle_color)
        config.subtitle_bg_color = str(subtitle_bg_color)
        config.subtitle_border_style = int(subtitle_border_style)
        config.subtitle_animation = str(subtitle_animation)
        config.subtitle_max_words = int(subtitle_max_words)
        
        config.padding = max(0, int(padding))
        config.set_ratio_preset(ratio)

        job_dir = os.path.join("clips", video_id)
        os.makedirs(job_dir, exist_ok=True)
        config.job_dir = job_dir
        
        try:
            url = payload.get("url")
            if url:
                preview = self.get_preview(url)
                with open(os.path.join(job_dir, "preview.json"), "w", encoding="utf-8") as f:
                    json.dump(preview, f)
        except Exception as e:
            if callable(event_hook):
                event_hook("log", f"Gagal menyimpan preview.json: {e}")

        ok = check_dependencies(install_whisper=True, skip_update_ytdlp=True, fatal=False, whisper_model=whisper_model)
        if not ok:
            raise RuntimeError("FFmpeg tidak ditemukan di sistem")

        total_duration = get_video_duration(video_id)

        targets = []
        picked = payload.get("segments")
        if isinstance(picked, list) and len(picked) > 0:
            if callable(event_hook):
                event_hook("log", f"Menggunakan {len(picked)} segmen yang dipilih pengguna...")
            for seg in picked:
                try:
                    start = float(seg.get("start"))
                    dur = float(seg.get("duration"))
                    score = float(seg.get("score", 1.0))
                except Exception:
                    continue
                if dur <= 0:
                    continue
                targets.append({"start": start, "duration": dur, "score": score})
            if not targets:
                raise ValueError("Segmen yang dipilih tidak valid")
        elif mode == "custom":
            start_s = parse_time_to_seconds(payload.get("start"))
            end_s = parse_time_to_seconds(payload.get("end"))
            if start_s is None or end_s is None:
                raise ValueError("Waktu Mulai dan Selesai harus diisi")
            if end_s <= start_s:
                raise ValueError("Waktu Selesai harus lebih besar dari Waktu Mulai")
            targets = [{"start": float(start_s), "duration": float(end_s - start_s), "score": 1.0}]
        else:
            if callable(event_hook):
                event_hook("log", "Memindai segmen most replayed...")
            segments = fetch_most_replayed(video_id, config.min_score, config.max_duration)
            if not segments:
                raise RuntimeError("Data Most Replayed / Heatmap tidak ditemukan untuk video ini")
            targets = segments[: max(1, int(max_clips) if max_clips else 10)]

        if callable(event_hook):
            event_hook("total_targets", len(targets))

        success_count = 0
        outputs = []
        for idx, item in enumerate(targets, start=1):
            if is_cancelled and is_cancelled():
                if callable(event_hook):
                    event_hook("log", "[CANCEL] Proses dibatalkan oleh pengguna.")
                break

            if callable(event_hook):
                event_hook("stage", {"stage": "start_clip", "clip_index": idx, "total": len(targets)})

            ok_clip = process_single_clip(
                video_id=video_id,
                item=item,
                index=idx,
                total_duration=total_duration,
                crop_mode=crop,
                use_subtitle=subtitle,
                event_hook=event_hook
            )

            if ok_clip:
                success_count += 1
                clip_path = os.path.join(job_dir, f"clip_{idx}.mp4")
                if os.path.exists(clip_path):
                    outputs.append({
                        "name": f"clip_{idx}.mp4",
                        "path": os.path.abspath(clip_path),
                        "size": os.path.getsize(clip_path)
                    })

            if callable(event_hook):
                event_hook("stage", {"stage": "done_clip", "clip_index": idx, "success": success_count, "outputs": outputs})

        return {
            "video_id": video_id,
            "total": len(targets),
            "success": success_count,
            "output_dir": os.path.abspath(job_dir),
            "outputs": outputs
        }

    def import_cookies(self, file_path: str) -> bool:
        """Imports Netscape cookies file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError("File cookies tidak ditemukan")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "# Netscape HTTP Cookie File" not in content and ".youtube.com" not in content:
            raise ValueError("Format file cookie tidak valid. Harus format Netscape HTTP Cookie File.")

        dest = "cookies.txt"
        shutil.copy2(file_path, dest)
        config.cookies_file = dest
        config.save_to_file()
        return True

    def set_intro_video(self, file_path: str) -> str:
        """Sets and copies intro video to assets folder."""
        if not os.path.exists(file_path):
            raise FileNotFoundError("File intro video tidak ditemukan")
        os.makedirs("assets", exist_ok=True)
        ext = os.path.splitext(file_path)[1]
        dest = os.path.join("assets", f"intro{ext}")
        shutil.copy2(file_path, dest)
        config.intro_video = dest
        config.save_to_file()
        return dest

    def set_outro_video(self, file_path: str) -> str:
        """Sets and copies outro video to assets folder."""
        if not os.path.exists(file_path):
            raise FileNotFoundError("File outro video tidak ditemukan")
        os.makedirs("assets", exist_ok=True)
        ext = os.path.splitext(file_path)[1]
        dest = os.path.join("assets", f"outro{ext}")
        shutil.copy2(file_path, dest)
        config.outro_video = dest
        config.save_to_file()
        return dest

    def get_available_fonts(self) -> List[str]:
        """Lists available fonts in fonts directory."""
        fonts = ["Arial", "Poppins", "Montserrat", "Impact", "Trebuchet MS"]
        if os.path.isdir("fonts"):
            for fname in os.listdir("fonts"):
                if fname.lower().endswith((".ttf", ".otf")):
                    name = os.path.splitext(fname)[0]
                    if name not in fonts:
                        fonts.append(name)
        return fonts

    def clear_cache_and_clips(self) -> Dict[str, Any]:
        """
        Clears cached segment JSON files, temporary MKV/MP4 files, and generated clips in clips/ directory.
        """
        with _preview_lock:
            _preview_cache.clear()

        deleted_files = 0
        deleted_bytes = 0
        clips_dir = "clips"

        if os.path.exists(clips_dir):
            for root, dirs, files in os.walk(clips_dir, topdown=False):
                for f in files:
                    file_path = os.path.join(root, f)
                    try:
                        size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_files += 1
                        deleted_bytes += size
                    except Exception as e:
                        log.warning(f"Gagal menghapus file cache {file_path}: {e}")
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    try:
                        os.rmdir(dir_path)
                    except Exception:
                        pass

        return {
            "deleted_files": deleted_files,
            "deleted_size_mb": round(deleted_bytes / (1024 * 1024), 2)
        }

    def generate_subtitle_preview_sample(
        self,
        payload: Dict[str, Any],
        event_hook: Optional[Callable[[str, Any], None]] = None
    ) -> str:
        """
        Generates a short 10-second preview clip with subtitles burned in for tuning subtitle delay.
        """
        url = (payload.get("url") or "").strip()
        if not url:
            raise ValueError("URL YouTube tidak boleh kosong")

        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("URL YouTube tidak valid")

        crop = payload.get("crop") or "default"
        ratio = payload.get("ratio") or "9:16"
        whisper_model = payload.get("whisper_model") or "small"
        subtitle_font = payload.get("subtitle_font") or "Arial"
        subtitle_location = payload.get("subtitle_location") or "bottom"
        subtitle_fontsdir = payload.get("subtitle_fontsdir") or None
        
        try:
            subtitle_delay = float(payload.get("subtitle_delay") or 0.0)
        except (ValueError, TypeError):
            subtitle_delay = 0.0

        subtitle_font_size = payload.get("subtitle_font_size") or 60
        subtitle_color = payload.get("subtitle_color") or "&H0000FFFF"
        subtitle_bg_color = payload.get("subtitle_bg_color") or "&H80000000"
        subtitle_border_style = payload.get("subtitle_border_style")
        if subtitle_border_style is None:
            subtitle_border_style = 3
        subtitle_animation = payload.get("subtitle_animation") or "none"
        subtitle_max_words = payload.get("subtitle_max_words") or 3

        if not subtitle_fontsdir and os.path.isdir("fonts"):
            subtitle_fontsdir = "fonts"

        config.whisper_model = whisper_model
        config.subtitle_font = subtitle_font
        config.subtitle_fonts_dir = subtitle_fontsdir
        config.subtitle_location = subtitle_location
        config.subtitle_delay = subtitle_delay / 1000.0 if subtitle_delay > 10 or subtitle_delay < -10 else subtitle_delay
        
        config.subtitle_font_size = int(subtitle_font_size)
        config.subtitle_color = str(subtitle_color)
        config.subtitle_bg_color = str(subtitle_bg_color)
        config.subtitle_border_style = int(subtitle_border_style)
        config.subtitle_animation = str(subtitle_animation)
        config.subtitle_max_words = int(subtitle_max_words)
        
        config.set_ratio_preset(ratio)

        preview_dir = os.path.join("clips", video_id)
        os.makedirs(preview_dir, exist_ok=True)
        config.job_dir = preview_dir

        # Determine 10-second test segment start
        start = 30.0
        picked = payload.get("segments")
        if isinstance(picked, list) and len(picked) > 0:
            start = float(picked[0].get("start", 30.0))
        elif payload.get("mode") == "custom":
            start_s = parse_time_to_seconds(payload.get("start"))
            if start_s is not None:
                start = float(start_s)

        total_duration = get_video_duration(video_id)
        test_item = {"start": start, "duration": 10.0, "score": 1.0}

        if callable(event_hook):
            event_hook("log", f"[PREVIEW] Memproses sampel 10 detik ({int(start)}s - {int(start + 10)}s) dengan Subtitle Delay: {subtitle_delay}ms...")

        ok = process_single_clip(
            video_id=video_id,
            item=test_item,
            index=999,
            total_duration=total_duration,
            crop_mode=crop,
            use_subtitle=True,
            event_hook=event_hook
        )

        if not ok:
            raise RuntimeError("Gagal menghasilkan sampel preview subtitle")

        sample_file = os.path.join(preview_dir, "clip_999.mp4")
        if not os.path.exists(sample_file):
            raise FileNotFoundError("File sampel preview tidak ditemukan")

        return os.path.abspath(sample_file)

    def scan_ai_highlights(
        self,
        url: str,
        ai_config: Dict[str, Any],
        event_hook: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
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
            try:
                with open(transcript_cache_file, "r", encoding="utf-8") as f:
                    transcript_segments = json.load(f)
                    if callable(event_hook):
                        event_hook("log", f"[AI] Menggunakan {len(transcript_segments)} klausa transkrip audio dari cache (skip download & Whisper transcribing).")
            except Exception as e:
                log.warning(f"Gagal membaca cache transkrip {transcript_cache_file}: {e}")

        if not transcript_segments:
            audio_file = os.path.join(job_dir, "audio_full.m4a")
            if not os.path.exists(audio_file):
                if callable(event_hook):
                    event_hook("stage", {"stage": "download", "clip_index": 0})
                    event_hook("log", "[AI] Mengunduh file audio video...")

                cmd_audio = [
                    sys.executable, "-m", "yt_dlp",
                    "--force-ipv4", "--quiet", "--no-warnings",
                    "-f", "ba[ext=m4a]/ba/b",
                    "-o", audio_file,
                    f"https://youtu.be/{video_id}"
                ]
                if config.cookies_file and os.path.exists(config.cookies_file):
                    cmd_audio.extend(["--cookies", config.cookies_file])

                res = subprocess.run(cmd_audio)
                if res.returncode != 0 or not os.path.exists(audio_file):
                    raise RuntimeError("Gagal mengunduh audio video untuk transkripsi AI.")

            if callable(event_hook):
                event_hook("stage", {"stage": "subtitle_transcribe", "clip_index": 0})
                event_hook("log", f"[AI] Mengekstrak transkripsi audio dengan Whisper model ({config.whisper_model})...")

            from core.subtitle import transcribe_audio_file
            transcript_segments = transcribe_audio_file(audio_file, whisper_model=config.whisper_model, event_hook=event_hook)

            if not transcript_segments:
                raise RuntimeError("Gagal mengekstrak transkripsi audio.")

            # Save complete transcript to disk so future AI calls don't need re-transcribing!
            try:
                with open(transcript_cache_file, "w", encoding="utf-8") as f:
                    json.dump(transcript_segments, f, indent=2)
                if callable(event_hook):
                    event_hook("log", f"[AI] Transkrip audio lengkap ({len(transcript_segments)} klausa) berhasil disimpan ke cache.")
            except Exception as e:
                log.warning(f"Gagal menyimpan cache transkrip: {e}")

        if callable(event_hook):
            event_hook("stage", {"stage": "ai_detect", "clip_index": 0})
            event_hook("log", f"[AI] Menganalisis {len(transcript_segments)} klausa ucapan dengan AI Model ({ai_config.get('provider', 'ollama').upper()})...")

        from core.ai_detector import ai_detector
        highlights = ai_detector.detect_highlights(transcript_segments, ai_config, event_hook=event_hook)

        total_duration = get_video_duration(video_id)
        result = {
            "video_id": video_id,
            "duration": total_duration,
            "segments": highlights,
            "transcript_count": len(transcript_segments)
        }

        ai_cache_file = os.path.join(job_dir, "ai_segments.json")
        try:
            with open(ai_cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except Exception:
            pass

        return result

# Global controller instance
controller = ClipController()




