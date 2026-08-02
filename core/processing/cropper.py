from typing import Optional
from core.config import config
from core.ffmpeg import build_cover_scale_crop_vf, build_cover_scale_vf, get_split_heights
from core.processing.utils import get_video_codec_args

def build_crop_command(temp_file: str, cropped_file: str, crop_mode: str, out_w: Optional[int], out_h: Optional[int], cx_norm: float = 0.5, cy_norm: float = 0.5) -> list:
    """Helper function to build FFmpeg crop/split command."""
    if crop_mode == "default":
        if config.output_ratio == "original":
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
            ] + get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]
        else:
            vf = build_cover_scale_crop_vf(out_w, out_h)
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
                "-vf", vf,
            ] + get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]
            
    elif crop_mode in ["split_left", "split_right", "split_face", "full_face"]:
        if config.output_ratio == "original" or not out_w or not out_h or out_h < out_w:
            vf = build_cover_scale_crop_vf(out_w or 720, out_h or 1280) if config.output_ratio != "original" else None
            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
            ]
            if vf:
                cmd.extend(["-vf", vf])
            cmd.extend(get_video_codec_args())
            cmd.extend([
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ])
            return cmd
        else:
            top_h, bottom_h = get_split_heights(out_h, config.bottom_height)
            scaled = build_cover_scale_vf(out_w, out_h)
            
            if crop_mode in ["split_face", "full_face"]:
                x_offset_bottom = f"max(0\\,min(iw*{cx_norm}-({out_w}/2)\\,iw-{out_w}))"
                y_offset_bottom = f"max(0\\,min(ih*{cy_norm}-({bottom_h}/2)\\,ih-{bottom_h}))"
            else:
                x_offset_bottom = "0" if crop_mode == "split_left" else f"iw-{out_w}"
                y_offset_bottom = f"ih-{bottom_h}"
            
            if crop_mode == "full_face":
                vf = (
                    f"[0:v]split=2[orig1][orig2];"
                    # Scale the top video to fit the output width while maintaining aspect ratio
                    f"[orig1]scale={out_w}:-2[top_vid];"
                    # Crop the facecam from the cover-scaled video for the bottom part
                    f"[orig2]{scaled}[scaled];"
                    f"[scaled]crop={out_w}:{bottom_h}:{x_offset_bottom}:{y_offset_bottom}[bottom_vid];"
                    # Stack them vertically so they touch each other directly (no gap)
                    f"[top_vid][bottom_vid]vstack[stacked];"
                    # Pad the stacked result to the full canvas size and center it vertically with black background
                    f"[stacked]pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black[out]"
                )
            else:
                vf = (
                    f"[0:v]{scaled}[scaled];"
                    f"[scaled]split=2[s1][s2];"
                    f"[s1]crop={out_w}:{top_h}:(iw-{out_w})/2:(ih-{out_h})/2[top];"
                    f"[s2]crop={out_w}:{bottom_h}:{x_offset_bottom}:{y_offset_bottom}[bottom];"
                    f"[top][bottom]vstack[out]"
                )
                
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
                "-filter_complex", vf,
                "-map", "[out]", "-map", "0:a?",
            ] + get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]
            
    elif crop_mode == "full":
        if config.output_ratio == "original" or not out_w or not out_h:
            return [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", temp_file,
            ] + get_video_codec_args() + [
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
            ] + get_video_codec_args() + [
                "-c:a", "aac", "-b:a", "128k",
                cropped_file
            ]

    raise ValueError(f"Unknown crop mode: {crop_mode}")
