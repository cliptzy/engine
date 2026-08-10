import os
import subprocess
from typing import Dict, Any, Callable, Optional, cast

from core.yt_dlp_logger import create_yt_dlp_logger, create_yt_dlp_progress_hook
from core.logger import log
from core.config import config

from core.subtitle import generate_subtitle
from core.processing.utils import run_command_with_logging, cleanup_temp_files
from core.processing.cropper import build_crop_command
from core.processing.subtitle import burn_subtitle_and_highlight
from core.processing.stacker import generate_intro, stack_and_concat

def process_single_clip(
    video_id: str,
    item: Dict[str, Any],
    index: int,
    total_duration: int,
    crop_mode: str = "default",
    use_subtitle: bool = False,
    event_hook: Optional[Callable[[str, Any], None]] = None,
    source_url: Optional[str] = None,
    custom_prompt: str = "",
    phase1_only: bool = False
) -> bool:
    original_hook = event_hook
    def wrapped_event_hook(event_name: str, data: Any):
        if callable(original_hook):
            if isinstance(data, dict) and "clip_index" not in data:
                data["clip_index"] = index
            original_hook(event_name, data)
    event_hook = wrapped_event_hook
    """
    Downloads, crops, and exports a single vertical clip based on a heatmap segment.
    """
    start_original = item["start"]
    end_original = item["start"] + item["duration"]

    start = max(0, start_original - config.padding)
    end = min(end_original + config.padding, total_duration)

    if end - start < 3:
        log.warning(f"Clip {index} is too short after padding. Skipping.")
        return False

    start_str = str(int(start))
    end_str = str(int(end))
    base_name = f"clip_{index}_{start_str}_{end_str}_{crop_mode}"

    temp_file = os.path.join(config.job_dir, f"{base_name}_raw.mkv")
    cropped_file = os.path.join(config.job_dir, f"{base_name}_nosub.mp4")
    subtitle_file = os.path.join(config.job_dir, f"{base_name}.ass")
    subbed_file = os.path.join(config.job_dir, f"{base_name}_subbed.mp4")
    output_file = os.path.join(config.job_dir, f"clip_{index}.mp4")

    log.info(f"[Clip {index}] Processing segment ({int(start)}s - {int(end)}s, padding {config.padding}s)")
    
    if callable(event_hook):
        try:
            event_hook("stage", {"stage": "download", "clip_index": index})
        except Exception as e:
            log.debug(f"Event hook error: {e}")

    import yt_dlp
    from yt_dlp.utils import download_range_func
    from core.utils import apply_fast_download_opts

    ydl_opts: dict[str, Any] = {
        'force_ipv4': True,
        'remote_components': ['ejs:github'],
        'no_warnings': False,
        'merge_output_format': 'mkv',
        'format': 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b',
        'outtmpl': temp_file,
        'download_ranges': download_range_func(cast(Any, None), [(start, end)]),
        'force_keyframes_at_cuts': True,
        'logger': create_yt_dlp_logger("[yt-dlp]"),
        'progress_hooks': [create_yt_dlp_progress_hook(event_hook, "[yt-dlp]")],
    }
    
    ydl_opts_fallback: dict[str, Any] = {
        'force_ipv4': True,
        'remote_components': ['ejs:github'],
        'no_warnings': False,
        'merge_output_format': 'mkv',
        'format': 'bv*+ba/b',
        'outtmpl': temp_file,
        'download_ranges': download_range_func(cast(Any, None), [(start, end)]),
        'force_keyframes_at_cuts': True,
        'logger': create_yt_dlp_logger("[yt-dlp-fallback]"),
        'progress_hooks': [create_yt_dlp_progress_hook(event_hook, "[yt-dlp-fallback]")],
    }
    
    if config.youtube.session and os.path.exists(config.youtube.session):
        ydl_opts['cookiefile'] = config.youtube.session
        ydl_opts_fallback['cookiefile'] = config.youtube.session

    apply_fast_download_opts(ydl_opts)
    apply_fast_download_opts(ydl_opts_fallback)

    try:
        if not os.path.exists(cropped_file):
            if source_url and os.path.isfile(source_url):
                log.info( f"[ffmpeg] Memotong video lokal: {start}s - {end}s\n")
                cmd_cut = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", str(start),
                    "-t", str(end - start),
                    "-i", source_url,
                    "-c", "copy",
                    "-avoid_negative_ts", "make_non_negative",
                    temp_file
                ]
                res = subprocess.run(cmd_cut, capture_output=True, text=True)
                if res.returncode != 0:
                    log.warning(f"Copy stream gagal, mencoba re-encode untuk memotong: {res.stderr}")
                    cmd_cut_enc = [
                        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-ss", str(start),
                        "-t", str(end - start),
                        "-i", source_url,
                        "-c:v", "libx264", "-c:a", "aac",
                        temp_file
                    ]
                    res_enc = subprocess.run(cmd_cut_enc, capture_output=True, text=True)
                    if res_enc.returncode != 0:
                        log.error(f"Gagal memotong video lokal: {res_enc.stderr}")
                        return False
            else:
                try:
                    log.info( f"[yt-dlp] Downloading segment: {start}s - {end}s\n")
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl: # type: ignore
                        ydl.download([f"https://youtu.be/{video_id}"])
                except Exception as e:
                    log.info(f"Retrying download with fallback format for clip {index}: {e}")
                    with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl: # type: ignore
                        ydl.download([f"https://youtu.be/{video_id}"])

            if not os.path.exists(temp_file):
                log.error(f"Failed to download video segment for clip {index}.")
                return False

            out_w, out_h = config.out_width, config.out_height
            
            cx_norm, cy_norm = 0.5, 0.5
            face_keyframes: list[tuple[float, float, float]] = []

            if crop_mode == "center_face":
                # Dynamic face tracking: deteksi wajah per interval waktu
                log.info(f"Detecting face keyframes for dynamic center crop in clip {index}...")
                try:
                    from core.face_tracker import get_face_keyframes
                    face_keyframes = get_face_keyframes(temp_file, interval_sec=3.0)
                    if not face_keyframes:
                        log.info(f"Clip {index}: Tidak ada keyframe wajah terdeteksi, fallback ke default.")
                        crop_mode = "default"
                    else:
                        # Gunakan posisi pertama sebagai cx_norm/cy_norm fallback
                        cx_norm, cy_norm = face_keyframes[0][1], face_keyframes[0][2]
                except Exception as e:
                    log.warning(f"Face keyframes module error: {e}")
                    crop_mode = "default"

            elif crop_mode in ["split_face", "full_face"]:
                log.info( f"Detecting face position for dynamic crop in clip {index}...")
                try:
                    from core.face_tracker import get_dominant_face_normalized_center
                    res_cx, res_cy, error_msg = get_dominant_face_normalized_center(temp_file)
                    if res_cx is None or res_cy is None:
                        log.info(f"Clip {index}: No face detected ({error_msg}), falling back to full mode.")
                        log.info( f"Wajah tidak terdeteksi pada klip {index} ({error_msg}). Beralih ke mode Full (fallback).")
                        crop_mode = "full"
                    else:
                        cx_norm, cy_norm = res_cx, res_cy
                except Exception as e:
                    log.warning(f"Face tracking module error: {e}")
                    crop_mode = "full"
                    
            cmd_crop = build_crop_command(temp_file, cropped_file, crop_mode, out_w, out_h, cx_norm, cy_norm, face_keyframes=face_keyframes)

            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "crop", "clip_index": index})
                except Exception as e:
                    log.debug(f"Event hook error: {e}")
                    
            log.info(f"Cropping video for clip {index}...")
            run_command_with_logging(cmd_crop, event_hook, prefix="[ffmpeg-crop]")
            
            # --- DeepFace Emotion Analysis ---
            # Kita menggunakan temp_file (raw clip) sebelum dihapus, dan memotong (crop) murni di koordinat wajah
            # sesuai dengan hasil deteksi face_tracker (cx_norm, cy_norm) di memori Python.
            # Bounding box akan dipetakan ke koordinat output akhir di dalam emotion_analyzer.py.
            visual_emotions = []
            if config.ai.use_emotion_detection:
                from core.processing.emotion_analyzer import analyze_video_emotions
                visual_emotions = analyze_video_emotions(temp_file, cx_norm, cy_norm, interval_sec=1.0, crop_mode=crop_mode)
            else:
                log.info("Deteksi emosi visual dinonaktifkan di pengaturan. Melewati DeepFace.")
            
            import json
            emotion_file = os.path.join(config.job_dir, f"emotion_{index}.json")
            try:
                with open(emotion_file, "w", encoding="utf-8") as f:
                    json.dump(visual_emotions, f)
            except Exception as e:
                log.warning(f"Gagal menyimpan data emosi visual: {e}")
            
            if os.path.exists(temp_file):
                os.remove(temp_file)
        else:
            log.info(f"Found existing cached nosub clip for {index}")

        current_clip = cropped_file

        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "subtitle", "clip_index": index})
            except Exception as e:
                log.debug(f"Event hook error: {e}")
                
        log.info(f"Generating subtitle for clip {index} (for metadata/burn)...")
        subtitle_generated, transcript_text, words_data = generate_subtitle(cropped_file, subtitle_file, config.subtitle.whisper_model, event_hook=event_hook)
        if not subtitle_generated:
            log.warning("Subtitle generation failed, continuing without subtitle...")

        # --- AI Metadata Generation ---
        metadata = {}
        if transcript_text:
            log.info( f"Generating metadata (Title, Desc, Highlight) via AI for clip {index}...")
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "ai_metadata", "clip_index": index})
                except Exception: pass
                
            from core.utils import get_preview_data
            preview_data = get_preview_data()
            youtube_title = preview_data.get("title", "Unknown")
            channel_name = preview_data.get("uploader", "Unknown")
            youtube_url = preview_data.get("webpage_url", f"https://youtu.be/{video_id}")

            # --- DeepFace Emotion Analysis ---
            visual_emotions = []
            emotion_file = os.path.join(config.job_dir, f"emotion_{index}.json")
            if os.path.exists(emotion_file):
                try:
                    import json
                    with open(emotion_file, "r", encoding="utf-8") as f:
                        visual_emotions = json.load(f)
                except Exception:
                    pass
            
            ai_config = config.to_dict()
            from core.ai.detector import ai_detector
            metadata = ai_detector.generate_metadata(
                clip_text=transcript_text,
                youtube_title=youtube_title,
                channel_name=channel_name,
                youtube_url=youtube_url,
                ai_config=ai_config,
                user_context=custom_prompt,
                event_hook=event_hook,
                language=preview_data.get("language", "Indonesia"),
                words_data=words_data,
                visual_emotions=visual_emotions
            )
            
            if metadata:
                metadata["visual_emotions"] = visual_emotions
                enriched_transcript = metadata.get("enriched_transcript")
                if enriched_transcript and isinstance(enriched_transcript, list):
                    from core.subtitle import write_enriched_ass_file
                    write_enriched_ass_file(enriched_transcript, subtitle_file, event_hook=event_hook)
                    
                metadata_file = os.path.join(config.job_dir, f"metadata_{index}.json")
                try:
                    from core.utils import write_json
                    write_json(metadata_file, metadata, indent=2)
                    log.info( f"Metadata saved to {metadata_file}")
                except Exception as e:
                    log.warning(f"Failed to save metadata for clip {index}: {e}")

        # --- Subtitle & Highlight Burning Logic ---
        if phase1_only:
            log.info(f"Phase 1 complete for clip {index}. Skipping rendering (Phase 2).")
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "done_clip", "clip_index": index})
                except Exception as e:
                    log.debug(f"Event hook error: {e}")
            return True

        current_clip = burn_subtitle_and_highlight(
            cropped_file, subbed_file, subtitle_file, metadata,
            start, end, index, use_subtitle, subtitle_generated, event_hook
        )

        # Process Intro / Outro Concatenation
        intro_to_use = generate_intro(index, metadata, event_hook)
        
        stack_and_concat(current_clip, output_file, intro_to_use, index, event_hook)

        log.info(f"Clip {index} successfully generated.")
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "done_clip", "clip_index": index})
            except Exception as e:
                log.debug(f"Event hook error: {e}")
        return True

    except subprocess.CalledProcessError as e:
        cleanup_temp_files([temp_file])
        log.error(f"Failed to generate clip {index}. Subprocess error.")
        return False
    except Exception as e:
        cleanup_temp_files([temp_file])
        log.error(f"Failed to generate clip {index}.")
        log.exception(f"Exception: {str(e)}")
        return False

def render_single_clip(
    job_dir: str,
    index: int,
    item: dict,
    use_subtitle: bool = True,
    event_hook: Optional[Callable] = None
) -> bool:
    """
    Executes Phase 2: Reads metadata, regenerates ASS, and renders the final clip.
    """
    import os
    import json
    from core.config import config
    from core.logger import log
    
    import glob
    start = float(item.get("start", 0))
    end = start + float(item.get("duration", 0))
    
    nosub_matches = glob.glob(os.path.join(job_dir, f"clip_{index}_*_nosub.mp4"))
    cropped_file = nosub_matches[0] if nosub_matches else os.path.join(job_dir, f"clip_{index}_nosub.mp4")
    
    subbed_file = os.path.join(job_dir, f"clip_{index}_sub.mp4")
    output_file = os.path.join(job_dir, f"clip_{index}.mp4")
    subtitle_file = os.path.join(job_dir, f"subtitle_{index}.ass")
    metadata_file = os.path.join(job_dir, f"metadata_{index}.json")
    
    if not os.path.exists(cropped_file):
        log.error(f"File video mentah (nosub) tidak ditemukan untuk klip {index}")
        return False
        
    metadata = {}
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            log.warning(f"Gagal membaca metadata untuk klip {index}: {e}")
            
    # Regenerate ASS from current metadata
    enriched_transcript = metadata.get("enriched_transcript")
    subtitle_generated = False
    if enriched_transcript and isinstance(enriched_transcript, list):
        from core.subtitle import write_enriched_ass_file
        write_enriched_ass_file(enriched_transcript, subtitle_file, event_hook=event_hook)
        subtitle_generated = True
        
    if callable(event_hook):
        event_hook("stage", {"stage": "rendering", "clip_index": index})
        
    current_clip = burn_subtitle_and_highlight(
        cropped_file, subbed_file, subtitle_file, metadata,
        start, end, index, use_subtitle, subtitle_generated, event_hook
    )
    
    intro_to_use = generate_intro(index, metadata, event_hook)
    
    stack_and_concat(current_clip, output_file, intro_to_use, index, event_hook)
    
    log.info(f"Render klip {index} berhasil.")
    if callable(event_hook):
        event_hook("stage", {"stage": "done_clip", "clip_index": index})
        
    return True
