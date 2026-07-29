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

    temp_file = os.path.join(config.output_dir, f"{base_name}_raw.mkv")
    cropped_file = os.path.join(config.output_dir, f"{base_name}_nosub.mp4")
    subtitle_file = os.path.join(config.output_dir, f"{base_name}.ass")
    subbed_file = os.path.join(config.output_dir, f"{base_name}_subbed.mp4")
    output_file = os.path.join(config.output_dir, f"clip_{index}.mp4")

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
        "--downloader", "ffmpeg",
        "--downloader-args", f"ffmpeg_i:-ss {start} -to {end} -hide_banner",
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
        "--downloader", "ffmpeg",
        "--downloader-args", f"ffmpeg_i:-ss {start} -to {end} -hide_banner",
        "--merge-output-format", "mkv",
        "-f", "bv*+ba/b",
    ]
    
    if config.cookies_file and os.path.exists(config.cookies_file):
        cmd_download.extend(["--cookies", config.cookies_file])
        cmd_download_fallback.extend(["--cookies", config.cookies_file])
        
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
        subtitle_generated = generate_subtitle(cropped_file, subtitle_file, config.whisper_model, event_hook=event_hook)
        if not subtitle_generated:
            log.warning("Subtitle generation failed, continuing without subtitle...")

        if use_subtitle and subtitle_generated:
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "burn_subtitle", "clip_index": index})
                except Exception as e:
                    log.debug(f"Event hook error: {e}")
                    
            log.info(f"Burning subtitle to video for clip {index}...")
            fontsdir_arg = ""
            if config.subtitle_fonts_dir and os.path.isdir(config.subtitle_fonts_dir):
                fontsdir_arg = f":fontsdir='{config.subtitle_fonts_dir}'"
            
            cmd_subtitle = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", cropped_file,
                "-vf", f"subtitles=filename='{subtitle_file}'{fontsdir_arg}",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
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
        has_intro = config.intro_video and os.path.isfile(config.intro_video)
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
                inputs.extend(["-i", config.intro_video])
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
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
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
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]
        else:
            vf = build_cover_scale_crop_vf(out_w, out_h)
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
                "-vf", vf,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
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
            cmd.extend([
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
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
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]
            
    raise ValueError(f"Unknown crop mode: {crop_mode}")


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
