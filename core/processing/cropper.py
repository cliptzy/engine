from typing import Optional
from core.config import config
from core.ffmpeg import build_cover_scale_crop_vf, build_cover_scale_vf, get_split_heights
from core.processing.utils import get_video_codec_args

def build_crop_command(temp_file: str, cropped_file: str, crop_mode: str, out_w: Optional[int], out_h: Optional[int], cx_norm: float = 0.5, cy_norm: float = 0.5, cx2_norm: float = 0.5, cy2_norm: float = 0.5) -> list:
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
                    f"[0:v]split=3[orig1][orig2][orig_bg];"
                    f"[orig_bg]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=20:20[bg];"
                    # Scale the top video to fit the output width while maintaining aspect ratio
                    f"[orig1]scale={out_w}:-2[top_vid];"
                    # Crop the facecam from the cover-scaled video for the bottom part
                    f"[orig2]{scaled}[scaled];"
                    f"[scaled]crop={out_w}:{bottom_h}:{x_offset_bottom}:{y_offset_bottom}[bottom_vid];"
                    # Stack them vertically so they touch each other directly (no gap)
                    f"[top_vid][bottom_vid]vstack[stacked];"
                    # Overlay the stacked result onto the blurred background
                    f"[bg][stacked]overlay=(W-w)/2:(H-h)/2[out]"
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

    elif crop_mode == "multi_face":
        # Multi Face Tracker (Podcast Mode)
        # Layout vstack: Face1 crop (atas) → Full video scaled (tengah) → Face2 crop (bawah)
        if config.output_ratio == "original" or not out_w or not out_h or out_h < out_w:
            # Fallback: jika rasio output tidak portrait, lakukan full mode saja
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
            # Bagi tinggi output menjadi 3 bagian: face1 (atas), full (tengah), face2 (bawah)
            # Proporsi: face1=25%, full=50%, face2=25%  — terasa balanced untuk podcast
            face_h = out_h // 4
            mid_h = out_h - (face_h * 2)
            # Pastikan ketinggian selalu genap agar encoder tidak error
            face_h = face_h if face_h % 2 == 0 else face_h - 1
            mid_h = mid_h if mid_h % 2 == 0 else mid_h + 1

            scaled = build_cover_scale_vf(out_w, out_h)

            # Face 1 crop offsets (top section)
            x_off_f1 = f"max(0\\,min(iw*{cx_norm}-({out_w}/2)\\,iw-{out_w}))"
            y_off_f1 = f"max(0\\,min(ih*{cy_norm}-({face_h}/2)\\,ih-{face_h}))"

            # Face 2 crop offsets (bottom section)
            x_off_f2 = f"max(0\\,min(iw*{cx2_norm}-({out_w}/2)\\,iw-{out_w}))"
            y_off_f2 = f"max(0\\,min(ih*{cy2_norm}-({face_h}/2)\\,ih-{face_h}))"

            vf = (
                # Split sumber menjadi 4 stream: bg blur, face1, full center, face2
                f"[0:v]split=4[orig_bg][orig_f1][orig_mid][orig_f2];"
                # Blurred background canvas
                f"[orig_bg]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=20:20[bg];"
                # Face 1 crop: scale ke cover lalu crop area wajah pertama
                f"[orig_f1]{scaled}[s_f1];"
                f"[s_f1]crop={out_w}:{face_h}:{x_off_f1}:{y_off_f1}[face1];"
                # Middle section: full video scaled to fit width
                f"[orig_mid]scale={out_w}:-2[mid_vid];"
                # Face 2 crop: scale ke cover lalu crop area wajah kedua
                f"[orig_f2]{scaled}[s_f2];"
                f"[s_f2]crop={out_w}:{face_h}:{x_off_f2}:{y_off_f2}[face2];"
                # Vstack: face1 → full → face2
                f"[face1][mid_vid][face2]vstack=inputs=3[stacked];"
                # Overlay stacked result onto blurred background for padding
                f"[bg][stacked]overlay=(W-w)/2:(H-h)/2[out]"
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
