import os
import sys
import subprocess
from typing import Dict, Any, Callable, Optional

from core.logger import log
from core.config import config
from core.ffmpeg import (
    build_cover_scale_crop_vf,
    build_cover_scale_vf,
    get_split_heights,
    escape_subtitles_filter_path,
    build_subtitle_force_style,
)
from core.subtitle import generate_subtitle

def process_single_clip(
    video_id: str,
    item: Dict[str, Any],
    index: int,
    total_duration: int,
    crop_mode: str = "default",
    use_subtitle: bool = False,
    event_hook: Optional[Callable[[str, Any], None]] = None
) -> bool:
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

    cmd_download = [
        sys.executable, "-m", "yt_dlp",
        "-v",
        "--force-ipv4",
        "--remote-components",
        "ejs:github",
        "--no-warnings",
        "--download-sections", f"*{start}-{end}",
        "--force-keyframes-at-cuts",
        "--merge-output-format", "mkv",
        "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b",
    ]
    
    cmd_download_fallback = [
        sys.executable, "-m", "yt_dlp",
        "-v",
        "--force-ipv4",
        "--remote-components",
        "ejs:github",
        "--no-warnings",
        "--download-sections", f"*{start}-{end}",
        "--force-keyframes-at-cuts",
        "--merge-output-format", "mkv",
        "-f", "bv*+ba/b",
    ]
    
    if config.yt_session and os.path.exists(config.yt_session):
        cmd_download.extend(["--cookies", config.yt_session])
        cmd_download_fallback.extend(["--cookies", config.yt_session])
        
    cmd_download.extend(["-o", temp_file, f"https://youtu.be/{video_id}"])
    cmd_download_fallback.extend(["-o", temp_file, f"https://youtu.be/{video_id}"])

    try:
        if not os.path.exists(cropped_file):
            try:
                _run_command_with_logging(cmd_download, event_hook, prefix="[yt-dlp]")
            except subprocess.CalledProcessError as e:
                log.info(f"Retrying download with fallback format for clip {index}...")
                _run_command_with_logging(cmd_download_fallback, event_hook, prefix="[yt-dlp-fallback]")

            if not os.path.exists(temp_file):
                log.error(f"Failed to download video segment for clip {index}.")
                return False

            out_w, out_h = config.out_width, config.out_height
            cmd_crop = _build_crop_command(temp_file, cropped_file, crop_mode, out_w, out_h)

            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "crop", "clip_index": index})
                except Exception as e:
                    log.debug(f"Event hook error: {e}")
                    
            log.info(f"Cropping video for clip {index}...")
            _run_command_with_logging(cmd_crop, event_hook, prefix="[ffmpeg-crop]")
            
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
        subtitle_generated, transcript_text = generate_subtitle(cropped_file, subtitle_file, config.whisper_model, event_hook=event_hook)
        if not subtitle_generated:
            log.warning("Subtitle generation failed, continuing without subtitle...")

        # --- AI Metadata Generation ---
        metadata = {}
        if transcript_text:
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "ai_metadata", "clip_index": index})
                    event_hook("log", f"Generating metadata (Title, Desc, Highlight) via AI for clip {index}...")
                except Exception: pass
                
            from core.utils import get_preview_data
            preview_data = get_preview_data()
            youtube_title = preview_data.get("title", "Unknown")
            channel_name = preview_data.get("uploader", "Unknown")
            youtube_url = preview_data.get("webpage_url", f"https://youtu.be/{video_id}")
            
            ai_config = config.to_dict()
            from core.ai_detector import ai_detector
            metadata = ai_detector.generate_metadata(
                clip_text=transcript_text,
                youtube_title=youtube_title,
                channel_name=channel_name,
                youtube_url=youtube_url,
                ai_config=ai_config,
                event_hook=event_hook,
                language=preview_data.get("language", "Indonesia")
            )
            
            if metadata:
                metadata_file = os.path.join(config.job_dir, f"metadata_{index}.json")
                try:
                    from core.utils import write_json
                    write_json(metadata_file, metadata, indent=2)
                    if callable(event_hook):
                        event_hook("log", f"Metadata saved to {metadata_file}")
                except Exception as e:
                    log.warning(f"Failed to save metadata for clip {index}: {e}")

        # --- Subtitle & Highlight Burning Logic ---
        has_highlight = config.use_highlight and metadata and metadata.get("highlight")
        should_burn = (use_subtitle and subtitle_generated) or has_highlight
        
        if should_burn and os.path.exists(subtitle_file):
            if has_highlight:
                if callable(event_hook):
                    try:
                        event_hook("log", f"Adding Highlight text to subtitle file for clip {index}...")
                    except Exception: pass
                try:
                    from core.subtitle import format_ass_time
                    highlight_text = metadata.get("highlight").upper()
                    end_ass = format_ass_time(end - start)
                    
                    # If subtitle is disabled but highlight is enabled, we need to remove the regular dialogue events
                    if not use_subtitle:
                        with open(subtitle_file, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        with open(subtitle_file, "w", encoding="utf-8") as f:
                            for line in lines:
                                if not line.startswith("Dialogue:"):
                                    f.write(line)
                                    
                    # Append Highlight event
                    # \an8 for top-center, \fs100 for large font, \c&H00FFFF& for yellow color, \b1 for bold
                    highlight_event = f"Dialogue: 1,0:00:00.00,{end_ass},Default,,0,0,100,,{{\\an8\\fs90\\c&H00FFFF&\\b1\\3c&H000000&\\3a&H80&\\bord5}}{highlight_text}\n"
                    with open(subtitle_file, "a", encoding="utf-8") as f:
                        f.write(highlight_event)
                except Exception as e:
                    log.warning(f"Failed to append highlight to subtitle: {e}")

            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "burn_subtitle", "clip_index": index})
                except Exception as e:
                    log.debug(f"Event hook error: {e}")
                    
            log.info(f"Burning subtitle/highlight to video for clip {index}...")
            fontsdir_arg = ""
            if config.subtitle_fonts_dir and os.path.isdir(config.subtitle_fonts_dir):
                fontsdir_arg = f":fontsdir='{config.subtitle_fonts_dir}'"
            
            cmd_subtitle = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", cropped_file,
                "-vf", f"subtitles=filename='{subtitle_file}'{fontsdir_arg}",
            ] + _get_video_codec_args() + [
                "-c:a", "copy",
                subbed_file
            ]
            
            try:
                _run_command_with_logging(cmd_subtitle, event_hook, prefix="[ffmpeg-subtitle]")
                current_clip = subbed_file
            except subprocess.CalledProcessError as e:
                log.warning("FFmpeg subtitle filter failed (likely missing libass). Falling back to non-subbed video.")
                if callable(event_hook):
                    try:
                        event_hook("log", "[ffmpeg-subtitle] ERROR: FFmpeg pada sistem ini tidak memiliki filter 'subtitles' (missing libass). Menyimpan video tanpa subtitle.")
                    except Exception:
                        pass

        # Process Intro / Outro Concatenation
        intro_to_use = config.intro_video if (config.intro_video and os.path.isfile(config.intro_video)) else None
        
        if config.use_generate_intro and metadata and metadata.get("highlight"):
            try:
                if callable(event_hook):
                    event_hook("log", f"[intro] Generating AI Intro with TTS for clip {index}...")
                
                highlight_text = metadata.get("highlight")
                
                # 1. Generate TTS
                from gtts import gTTS
                import json
                tts_lang = 'id'
                from core.utils import get_preview_data
                tts_lang = get_preview_data().get("language") or 'id'
                
                tts = gTTS(text=highlight_text, lang=tts_lang)
                audio_path = os.path.join(config.job_dir, f"intro_audio_{index}.mp3")
                tts.save(audio_path)
                
                # 2. Get duration
                try:
                    res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], capture_output=True, text=True)
                    duration_sec = float(res.stdout.strip())
                except:
                    duration_sec = 3.0
                
                # 3. Create ASS for centered highlight text
                intro_ass = os.path.join(config.job_dir, f"intro_{index}.ass")
                from core.subtitle import format_ass_time
                end_ass = format_ass_time(duration_sec + 0.5) # add little padding
                
                with open(intro_ass, "w", encoding="utf-8") as f:
                    f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n\n[V4+ Styles]\n")
                    f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
                    f.write(f"Style: Default,{config.subtitle_font},80,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,5,20,20,20,1\n\n")
                    f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
                    f.write(f"Dialogue: 0,0:00:00.00,{end_ass},Default,,0,0,0,,{{\\an5\\b1\\bord5\\3c&H000000&}}{highlight_text.upper()}\n")
                
                # 4. Generate black video with ASS and Audio
                intro_video_path = os.path.join(config.job_dir, f"intro_video_{index}.mp4")
                out_w, out_h = config.out_width or 720, config.out_height or 1280
                fontsdir_arg = ""
                if config.subtitle_fonts_dir and os.path.isdir(config.subtitle_fonts_dir):
                    fontsdir_arg = f":fontsdir='{config.subtitle_fonts_dir}'"
                    
                cmd_intro = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"color=c=black:s={out_w}x{out_h}:d={duration_sec + 0.5}",
                    "-i", audio_path,
                    "-vf", f"subtitles=filename='{intro_ass}'{fontsdir_arg}",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
                    "-c:a", "aac", "-b:a", "128k",
                    "-shortest",
                    intro_video_path
                ]
                subprocess.run(cmd_intro, check=True)
                intro_to_use = intro_video_path
                
            except Exception as e:
                log.error(f"Failed to generate intro video: {e}")
                if callable(event_hook):
                    event_hook("log", f"[intro] ❌ Failed to generate intro: {e}")

        has_intro = intro_to_use and os.path.isfile(intro_to_use)
        has_outro = config.outro_video and os.path.isfile(config.outro_video)
        
        if has_intro or has_outro:
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "finalize", "clip_index": index})
                    event_hook("log", f"[concat] Adding intro/outro to clip {index}...")
                except Exception:
                    pass
                    
            inputs = []
            filter_complex = ""
            input_idx = 0
            
            # Since videos might have different resolutions/codecs, we MUST re-encode and scale them to out_w x out_h
            out_w, out_h = config.out_width or 720, config.out_height or 1280
            scale_filter = f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
            
            if has_intro:
                inputs.extend(["-i", intro_to_use])
                filter_complex += f"[{input_idx}:v:0]{scale_filter}[v{input_idx}]; [{input_idx}:a:0]aresample=async=1[a{input_idx}]; "
                input_idx += 1
                
            inputs.extend(["-i", current_clip])
            filter_complex += f"[{input_idx}:v:0]{scale_filter}[v{input_idx}]; [{input_idx}:a:0]aresample=async=1[a{input_idx}]; "
            clip_input_idx = input_idx
            input_idx += 1
            
            if has_outro:
                inputs.extend(["-i", config.outro_video])
                filter_complex += f"[{input_idx}:v:0]{scale_filter}[v{input_idx}]; [{input_idx}:a:0]aresample=async=1[a{input_idx}]; "
                input_idx += 1
                
            concat_parts = ""
            for i in range(input_idx):
                concat_parts += f"[v{i}][a{i}]"
            
            filter_complex += f"{concat_parts}concat=n={input_idx}:v=1:a=1[outv][outa]"
            
            cmd_concat = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info"
            ] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "[outv]", "-map", "[outa]",
            ] + _get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                output_file
            ]
            
            _run_command_with_logging(cmd_concat, event_hook, prefix="[ffmpeg-concat]")
        else:
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "finalize", "clip_index": index})
                except Exception:
                    pass
            # Just copy the final result
            import shutil
            if current_clip != output_file:
                shutil.copy2(current_clip, output_file)

        log.info(f"Clip {index} successfully generated.")
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "done_clip", "clip_index": index})
            except Exception as e:
                log.debug(f"Event hook error: {e}")
        return True

    except subprocess.CalledProcessError as e:
        _cleanup_temp_files([temp_file])
        log.error(f"Failed to generate clip {index}. Subprocess error.")
        return False
    except Exception as e:
        _cleanup_temp_files([temp_file])
        log.error(f"Failed to generate clip {index}.")
        log.exception(f"Exception: {str(e)}")
        return False


def _build_crop_command(temp_file: str, cropped_file: str, crop_mode: str, out_w: Optional[int], out_h: Optional[int]) -> list:
    """Helper function to build FFmpeg crop/split command."""
    if crop_mode == "default":
        if config.output_ratio == "original":
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
            ] + _get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]
        else:
            vf = build_cover_scale_crop_vf(out_w, out_h)
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
                "-vf", vf,
            ] + _get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]
            
    elif crop_mode in ["split_left", "split_right"]:
        if config.output_ratio == "original" or not out_w or not out_h or out_h < out_w:
            vf = build_cover_scale_crop_vf(out_w or 720, out_h or 1280) if config.output_ratio != "original" else None
            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
            ]
            if vf:
                cmd.extend(["-vf", vf])
            cmd.extend(_get_video_codec_args())
            cmd.extend([
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ])
            return cmd
        else:
            top_h, bottom_h = get_split_heights(out_h, config.bottom_height)
            scaled = build_cover_scale_vf(out_w, out_h)
            
            x_offset_bottom = "0" if crop_mode == "split_left" else f"iw-{out_w}"
            
            vf = (
                f"{scaled}[scaled];"
                f"[scaled]split=2[s1][s2];"
                f"[s1]crop={out_w}:{top_h}:(iw-{out_w})/2:(ih-{out_h})/2[top];"
                f"[s2]crop={out_w}:{bottom_h}:{x_offset_bottom}:ih-{bottom_h}[bottom];"
                f"[top][bottom]vstack[out]"
            )
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
                "-filter_complex", vf,
                "-map", "[out]", "-map", "0:a?",
            ] + _get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]
            
    elif crop_mode == "full":
        if config.output_ratio == "original" or not out_w or not out_h:
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
            ] + _get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]
        else:
            vf = (
                f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=20:20[bg];"
                f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[out]"
            )
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
                "-filter_complex", vf,
                "-map", "[out]", "-map", "0:a?",
            ] + _get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]

    raise ValueError(f"Unknown crop mode: {crop_mode}")


def _get_video_codec_args() -> list:
    import sys
    hw = getattr(config, "hw_accel", "cpu").lower()
    
    # Auto-redirect all hardware acceleration to VideoToolbox on macOS
    if sys.platform == "darwin" and hw in ["mac", "videotoolbox", "amd", "amf", "intel", "qsv", "nvidia", "nvenc"]:
        return ["-c:v", "h264_videotoolbox", "-b:v", "5M"]

    if hw in ["mac", "videotoolbox"]:
        return ["-c:v", "h264_videotoolbox", "-b:v", "5M"]
    elif hw in ["nvidia", "nvenc"]:
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "26"]
    elif hw in ["amd", "amf"]:
        return ["-c:v", "h264_amf", "-rc", "cqp", "-qp_p", "26", "-qp_i", "26"]
    elif hw in ["intel", "qsv"]:
        return ["-c:v", "h264_qsv", "-global_quality", "26"]
    return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26"]

def _run_command_with_logging(cmd: list, event_hook: Optional[Callable], prefix: str = "") -> bool:
    """Helper to run a subprocess and stream its output line by line."""
    log.info(f"Running command: {' '.join(cmd)}")
    if callable(event_hook):
        event_hook("log", f"{prefix} Executing command: {' '.join(cmd)}\n")
        
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    for line in iter(process.stdout.readline, ''):
        if line:
            clean_line = line.strip()
            if callable(event_hook) and clean_line:
                event_hook("log", f"{prefix} {clean_line}")
                
    process.stdout.close()
    return_code = process.wait()
    
    if return_code != 0:
        msg = f"{prefix} Command failed with return code {return_code}"
        log.error(msg)
        if callable(event_hook):
            event_hook("log", msg)
        raise subprocess.CalledProcessError(return_code, cmd)
    return True

def _cleanup_temp_files(files: list) -> None:
    """Safely removes temporary files."""
    for f in files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception as e:
                log.debug(f"Failed to cleanup temp file {f}: {e}")
