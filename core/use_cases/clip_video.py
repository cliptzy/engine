import os
from typing import Dict, Any, Optional, Callable, List

from core.config import config
from core.logger import log
from core.youtube import extract_video_id, fetch_most_replayed, get_video_duration
from core.utils import check_dependencies
from core.processor import process_single_clip
from core.interfaces import ProgressReporter
from core.use_cases.preview_clip import PreviewClipUseCase

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

class ClipVideoUseCase:
    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter

    def execute(
        self,
        payload: Dict[str, Any],
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes the clipping pipeline based on settings payload.
        """
        url = (payload.get("url") or "").strip()
        if not url:
            raise ValueError("URL YouTube tidak boleh kosong")

        def event_hook(event: str, data: Any = None):
            if self.reporter:
                if event == "log":
                    self.reporter.on_log(str(data))
                elif event == "stage":
                    stage = data.get("stage", "")
                    idx = data.get("clip_index", 0)
                    tot = data.get("total", 0)
                    self.reporter.on_progress(stage, idx, tot)

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

        config.subtitle.whisper_model = whisper_model
        config.ai.use_highlight = bool(payload.get("use_highlight", False))
        config.subtitle.font = subtitle_font
        config.subtitle.fonts_dir = subtitle_fontsdir
        config.subtitle.location = subtitle_location
        config.subtitle.delay = subtitle_delay / 1000.0 if subtitle_delay > 10 else subtitle_delay
        
        config.subtitle.font_size = int(subtitle_font_size)
        config.subtitle.color = str(subtitle_color)
        config.subtitle.bg_color = str(subtitle_bg_color)
        config.subtitle.border_style = int(subtitle_border_style)
        config.subtitle.animation = str(subtitle_animation)
        config.subtitle.max_words = int(subtitle_max_words)
        
        config.padding = max(0, int(padding if padding is not None else 10))
        config.set_ratio_preset(ratio)

        job_dir = os.path.join("clips", video_id)
        os.makedirs(job_dir, exist_ok=True)
        config.job_dir = job_dir
        preview = None
        
        try:
            preview = PreviewClipUseCase().execute(url)
            from core.utils import write_json
            write_json(os.path.join(job_dir, "preview.json"), preview)
        except Exception as e:
            event_hook("log", f"Gagal menyimpan preview.json: {e}")

        ok = check_dependencies(install_whisper=True, skip_update_ytdlp=True, fatal=False, whisper_model=whisper_model)
        if not ok:
            raise RuntimeError("FFmpeg tidak ditemukan di sistem")

        if is_local and preview is not None:
            total_duration = preview.get("duration", 0)
        else:
            total_duration = get_video_duration(video_id)

        targets = []
        picked = payload.get("segments")
        if isinstance(picked, list) and len(picked) > 0:
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
            
            if start_s is None and end_s is None:
                start_s = 0
                end_s = int(total_duration)
                event_hook("log", f"Menggunakan rentang waktu kustom: memproses keseluruhan video (0s - {end_s}s)")

            if start_s is None or end_s is None:
                raise ValueError("Waktu Mulai dan Selesai harus diisi, atau kosongkan keduanya untuk memproses seluruh video")
            if end_s <= start_s:
                raise ValueError("Waktu Selesai harus lebih besar dari Waktu Mulai")
            targets = [{"start": float(start_s), "duration": float(end_s - start_s), "score": 1.0}]
        else:
            event_hook("log", "Memindai segmen most replayed...")
            segments = fetch_most_replayed(video_id, config.min_score, config.max_duration)
            if not segments:
                raise RuntimeError("Data Most Replayed / Heatmap tidak ditemukan untuk video ini")
            targets = segments[: max(1, int(max_clips) if max_clips else 10)]

        event_hook("total_targets", len(targets))

        success_count = 0
        outputs = []
        for idx, item in enumerate(targets, start=1):
            if is_cancelled and is_cancelled():
                event_hook("log", "[CANCEL] Proses dibatalkan oleh pengguna.")
                break

            event_hook("stage", {"stage": "start_clip", "clip_index": idx, "total": len(targets)})

            ok_clip = process_single_clip(
                video_id=video_id,
                item=item,
                index=idx,
                total_duration=total_duration,
                crop_mode=crop,
                use_subtitle=subtitle,
                event_hook=event_hook,
                source_url=url if is_local else None,
                custom_prompt=payload.get("custom_prompt", "")
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

            event_hook("stage", {"stage": "done_clip", "clip_index": idx, "success": success_count, "outputs": outputs})

        if config.merge_clips and len(outputs) > 1 and not (is_cancelled and is_cancelled()):
            event_hook("log", "Menggabungkan klip (Merge)...")
            event_hook("stage", {"stage": "merging"})
            
            merged_filename = "merged.mp4"
            merged_path = os.path.join(job_dir, merged_filename)
            list_path = os.path.join(job_dir, "concat_list.txt")
            
            try:
                with open(list_path, "w", encoding="utf-8") as f:
                    for out in outputs:
                        f.write(f"file '{out['name']}'\n")
                
                cmd = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0",
                    "-i", "concat_list.txt",
                    "-c", "copy",
                    merged_filename
                ]
                import subprocess
                res = subprocess.run(cmd, cwd=job_dir, capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(f"FFmpeg Error: {res.stderr}")
                
                outputs.append({
                    "name": merged_filename,
                    "path": os.path.abspath(merged_path),
                    "size": os.path.getsize(merged_path)
                })
                
                # --- Generate Metadata for Merged Video ---
                try:
                    from core.utils import read_json, get_preview_data, write_json
                    combined_texts = []
                    for out in outputs:
                        if out['name'] == merged_filename: continue
                        idx = out['name'].replace("clip_", "").replace(".mp4", "")
                        meta_path = os.path.join(job_dir, f"metadata_{idx}.json")
                        if os.path.exists(meta_path):
                            m_data = read_json(meta_path)
                            if m_data:
                                t = m_data.get("title", "")
                                d = m_data.get("description", "")
                                combined_texts.append(f"Klip {idx}: Judul: {t}\nDeskripsi: {d}")
                    
                    if combined_texts:
                        event_hook("log", "Generating metadata for merged video via AI...")
                        event_hook("stage", {"stage": "ai_metadata", "clip_index": success_count, "is_merge": True})
                        
                        preview_data = get_preview_data()
                        youtube_title = preview_data.get("title", "Unknown")
                        channel_name = preview_data.get("uploader", "Unknown")
                        youtube_url = preview_data.get("webpage_url", f"https://youtu.be/{video_id}")
                        
                        clip_text = "Ini adalah kompilasi video panjang dari beberapa momen. Berikut ringkasannya:\n" + "\n\n".join(combined_texts)
                        
                        from core.ai.detector import ai_detector
                        ai_config = config.to_dict()
                        merged_metadata = ai_detector.generate_metadata(
                            clip_text=clip_text,
                            youtube_title=youtube_title,
                            channel_name=channel_name,
                            youtube_url=youtube_url,
                            ai_config=ai_config,
                            event_hook=event_hook,
                            language=preview_data.get("language", "Indonesia")
                        )
                        
                        if merged_metadata:
                            meta_file = os.path.join(job_dir, "metadata_merge.json")
                            write_json(meta_file, merged_metadata, indent=2)
                            event_hook("log", f"Metadata kompilasi disimpan ke {meta_file}")
                except Exception as e:
                    log.warning(f"Gagal men-generate metadata kompilasi: {e}")
                
                event_hook("log", "Berhasil menggabungkan klip.")
                event_hook("stage", {"stage": "done_clip", "clip_index": success_count, "is_merge": True, "success": success_count, "outputs": outputs})
            except Exception as e:
                log.error(f"Gagal menggabungkan klip: {e}")
                event_hook("log", f"Gagal menggabungkan klip: {e}")
            finally:
                if os.path.exists(list_path):
                    os.remove(list_path)

        if self.reporter:
            self.reporter.on_finished(outputs)

        return {
            "video_id": video_id,
            "total": len(targets),
            "success": success_count,
            "output_dir": os.path.abspath(job_dir),
            "outputs": outputs
        }

    def generate_subtitle_preview_sample(self, payload: Dict[str, Any]) -> str:
        """
        Generates a short 10-second preview clip with subtitles burned in for tuning subtitle delay.
        """
        url = (payload.get("url") or "").strip()
        if not url:
            raise ValueError("URL YouTube tidak boleh kosong")

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

        def event_hook(event: str, data: Any = None):
            if self.reporter:
                if event == "log":
                    self.reporter.on_log(str(data))
                elif event == "stage":
                    stage = data.get("stage", "")
                    idx = data.get("clip_index", 0)
                    tot = data.get("total", 0)
                    self.reporter.on_progress(stage, idx, tot)

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

        config.subtitle.whisper_model = whisper_model
        config.subtitle.font = subtitle_font
        config.subtitle.fonts_dir = subtitle_fontsdir
        config.subtitle.location = subtitle_location
        config.subtitle.delay = subtitle_delay / 1000.0 if subtitle_delay > 10 or subtitle_delay < -10 else subtitle_delay
        
        config.subtitle.font_size = int(subtitle_font_size)
        config.subtitle.color = str(subtitle_color)
        config.subtitle.bg_color = str(subtitle_bg_color)
        config.subtitle.border_style = int(subtitle_border_style)
        config.subtitle.animation = str(subtitle_animation)
        config.subtitle.max_words = int(subtitle_max_words)
        
        config.set_ratio_preset(ratio)

        preview_dir = os.path.join("clips", video_id)
        os.makedirs(preview_dir, exist_ok=True)
        config.job_dir = preview_dir

        start = 30.0
        picked = payload.get("segments")
        if isinstance(picked, list) and len(picked) > 0:
            start = float(picked[0].get("start", 30.0))
        elif payload.get("mode") == "custom":
            start_s = parse_time_to_seconds(payload.get("start"))
            if start_s is not None:
                start = float(start_s)

        if is_local:
            from core.use_cases.preview_clip import PreviewClipUseCase
            total_duration = PreviewClipUseCase().execute(url).get("duration", 0)
        else:
            total_duration = get_video_duration(video_id)
        test_item = {"start": start, "duration": 10.0, "score": 1.0}

        event_hook("log", f"[PREVIEW] Memproses sampel 10 detik ({int(start)}s - {int(start + 10)}s) dengan Subtitle Delay: {subtitle_delay}ms...")

        ok = process_single_clip(
            video_id=video_id,
            item=test_item,
            index=999,
            total_duration=total_duration,
            crop_mode=crop,
            use_subtitle=True,
            event_hook=event_hook,
            source_url=url if is_local else None
        )

        if not ok:
            raise RuntimeError("Gagal menghasilkan sampel preview subtitle")

        sample_file = os.path.join(preview_dir, "clip_999.mp4")
        if not os.path.exists(sample_file):
            raise FileNotFoundError("File sampel preview tidak ditemukan")

        return os.path.abspath(sample_file)
