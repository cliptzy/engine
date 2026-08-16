from typing import Optional

from core.config import config
from core.ffmpeg import (
    build_cover_scale_crop_vf,
    build_cover_scale_vf,
    get_split_heights,
)
from core.processing.utils import get_video_codec_args


def build_crop_command(
    temp_file: str,
    cropped_file: str,
    crop_mode: str,
    out_w: Optional[int],
    out_h: Optional[int],
    cx_norm: float = 0.5,
    cy_norm: float = 0.5,
    cx2_norm: float = 0.5,
    cy2_norm: float = 0.5,
    face_keyframes: Optional[list[tuple[float, float, float, str]]] = None,
) -> list:
    """Helper function to build FFmpeg crop/split command."""
    if crop_mode == "default":
        if config.output_ratio == "original":
            return (
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "info",
                    "-i",
                    temp_file,
                ]
                + get_video_codec_args()
                + ["-c:a", "aac", "-b:a", "128k", cropped_file]
            )
        else:
            vf = build_cover_scale_crop_vf(out_w, out_h)
            return (
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "info",
                    "-i",
                    temp_file,
                    "-vf",
                    vf,
                ]
                + get_video_codec_args()
                + ["-c:a", "aac", "-b:a", "128k", cropped_file]
            )

    elif crop_mode == "center_face":
        # Center Face Track: crop dinamis mengikuti posisi wajah per interval waktu
        if config.output_ratio == "original" or not out_w or not out_h:
            # Fallback ke default jika rasio original
            vf = (
                build_cover_scale_crop_vf(out_w, out_h)
                if config.output_ratio != "original"
                else None
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "info",
                "-i",
                temp_file,
            ]
            if vf:
                cmd.extend(["-vf", vf])
            cmd.extend(get_video_codec_args())
            cmd.extend(["-c:a", "aac", "-b:a", "128k", cropped_file])
            return cmd
        else:
            scaled = build_cover_scale_vf(out_w, out_h)

            if face_keyframes and len(face_keyframes) > 1:
                # Sederhanakan list keyframes untuk menghemat panjang argumen CLI
                # Kita bisa membuang keyframe di tengah jika nilainya sama dengan sebelumnya dan sesudahnya
                simplified = []
                for i in range(len(face_keyframes)):
                    if i == 0 or i == len(face_keyframes) - 1:
                        simplified.append(face_keyframes[i])
                    else:
                        prev_kf = face_keyframes[i - 1]
                        curr_kf = face_keyframes[i]
                        next_kf = face_keyframes[i + 1]
                        
                        # Jika prev, curr, dan next memiliki cx dan cy yang SAMA PERSIS, buang curr
                        if (curr_kf[1] == prev_kf[1] and curr_kf[2] == prev_kf[2] and
                            curr_kf[1] == next_kf[1] and curr_kf[2] == next_kf[2]):
                            pass
                        else:
                            simplified.append(curr_kf)
                
                face_keyframes = simplified
                
                # FFmpeg eval.c (AST parser) memiliki hard-limit untuk jumlah terms jumlahan (sekitar 95 terms).
                # Jika lebih dari 85 keyframes, lakukan simplifikasi agresif berdasarkan jarak (tolerance).
                MAX_KEYFRAMES = 85
                if len(face_keyframes) > MAX_KEYFRAMES:
                    for tol_idx in range(1, 100):
                        tolerance = tol_idx * 0.005 # 0.005 hingga 0.5 (max 50% jarak layar)
                        new_simplified = [face_keyframes[0]]
                        for i in range(1, len(face_keyframes) - 1):
                            prev_saved = new_simplified[-1]
                            curr_kf = face_keyframes[i]
                            
                            # Jika perubahan pada sumbu X dan Y sangat kecil dibandingkan titik terakhir yang disimpan, abaikan.
                            if abs(curr_kf[1] - prev_saved[1]) < tolerance and abs(curr_kf[2] - prev_saved[2]) < tolerance:
                                continue
                            
                            new_simplified.append(curr_kf)
                            
                        new_simplified.append(face_keyframes[-1])
                        
                        if len(new_simplified) <= MAX_KEYFRAMES:
                            face_keyframes = new_simplified
                            break


                # Dynamic mode: buat ekspresi crop x/y yang berubah berdasarkan waktu (t)
                def _make_offset_expr(
                    keyframes: list[tuple[float, float, float, str]], axis: str
                ) -> str:
                    """Buat nested if(lt(t,...)) expression untuk crop x atau y."""
                    idx = 1 if axis == "x" else 2
                    dim = out_w if axis == "x" else out_h
                    ivar = "iw" if axis == "x" else "ih"

                    def _offset(norm: float) -> str:
                        return f"max(0\\,min({ivar}*{norm:.4f}-({dim}/2)\\,{ivar}-{dim}))"

                    if len(keyframes) == 1:
                        return _offset(float(keyframes[0][idx]))

                    terms = []
                    for i in range(len(keyframes) - 1):
                        ts_prev = float(keyframes[i][0])
                        pos_prev = float(keyframes[i][idx])
                        
                        ts_curr = float(keyframes[i + 1][0])
                        pos_curr = float(keyframes[i + 1][idx])
                        mode = str(keyframes[i + 1][3])
                        
                        if mode == "glide" and ts_curr > ts_prev:
                            delta = pos_curr - pos_prev
                            if abs(delta) < 0.0001:
                                curr_expr = _offset(pos_prev)
                            else:
                                dur = ts_curr - ts_prev
                                rate = delta / dur
                                norm_t = f"({pos_prev:.4f}+{rate:.4f}*(t-{ts_prev:.3f}))"
                                curr_expr = f"max(0\\,min({ivar}*{norm_t}-({dim}/2)\\,{ivar}-{dim}))"
                        else:
                            curr_expr = _offset(pos_prev)
                            
                        if i == 0:
                            terms.append(f"({curr_expr})*lt(t\\,{ts_curr:.3f})")
                        else:
                            terms.append(f"({curr_expr})*gte(t\\,{ts_prev:.3f})*lt(t\\,{ts_curr:.3f})")
                            
                    last_ts = float(keyframes[-1][0])
                    last_pos = float(keyframes[-1][idx])
                    terms.append(f"({_offset(last_pos)})*gte(t\\,{last_ts:.3f})")
                    
                    return "+".join(terms)

                x_expr = _make_offset_expr(face_keyframes, "x")
                y_expr = _make_offset_expr(face_keyframes, "y")

                vf = f"{scaled},crop={out_w}:{out_h}:{x_expr}:{y_expr}"
            else:
                # Static fallback: hanya 1 keyframe atau tidak ada, gunakan posisi tunggal
                x_offset = f"max(0\\,min(iw*{cx_norm}-({out_w}/2)\\,iw-{out_w}))"
                y_offset = f"max(0\\,min(ih*{cy_norm}-({out_h}/2)\\,ih-{out_h}))"
                vf = f"{scaled},crop={out_w}:{out_h}:{x_offset}:{y_offset}"

            # Selalu tulis ke file .vf untuk keperluan debugging
            script_path = temp_file + ".vf"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(vf)

            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "info",
                "-i",
                temp_file,
                "-vf",
                vf,
            ]

            return cmd + get_video_codec_args() + ["-c:a", "aac", "-b:a", "128k", cropped_file]

    elif crop_mode in ["split_left", "split_right", "split_face", "full_face"]:
        if config.output_ratio == "original" or not out_w or not out_h or out_h < out_w:
            vf = (
                build_cover_scale_crop_vf(out_w or 720, out_h or 1280)
                if config.output_ratio != "original"
                else None
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "info",
                "-i",
                temp_file,
            ]
            if vf:
                cmd.extend(["-vf", vf])
            cmd.extend(get_video_codec_args())
            cmd.extend(["-c:a", "aac", "-b:a", "128k", cropped_file])
            return cmd
        else:
            top_h, bottom_h = get_split_heights(out_h, config.bottom_height)
            scaled = build_cover_scale_vf(out_w, out_h)

            if crop_mode in ["split_face", "full_face"]:
                x_offset_bottom = f"max(0\\,min(iw*{cx_norm}-({out_w}/2)\\,iw-{out_w}))"
                y_offset_bottom = (
                    f"max(0\\,min(ih*{cy_norm}-({bottom_h}/2)\\,ih-{bottom_h}))"
                )
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

            return (
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "info",
                    "-i",
                    temp_file,
                    "-filter_complex",
                    vf,
                    "-map",
                    "[out]",
                    "-map",
                    "0:a?",
                ]
                + get_video_codec_args()
                + ["-c:a", "aac", "-b:a", "128k", cropped_file]
            )

    elif crop_mode == "full":
        if config.output_ratio == "original" or not out_w or not out_h:
            return (
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "info",
                    "-i",
                    temp_file,
                ]
                + get_video_codec_args()
                + ["-c:a", "aac", "-b:a", "128k", cropped_file]
            )
        else:
            vf = (
                f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=20:20[bg];"
                f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[out]"
            )
            return (
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "info",
                    "-i",
                    temp_file,
                    "-filter_complex",
                    vf,
                    "-map",
                    "[out]",
                    "-map",
                    "0:a?",
                ]
                + get_video_codec_args()
                + ["-c:a", "aac", "-b:a", "128k", cropped_file]
            )

    elif crop_mode == "multi_face":
        # Multi Face Tracker (Podcast Mode)
        # Layout vstack: Face1 crop (atas) → Full video scaled (tengah) → Face2 crop (bawah)
        if abs(cx_norm - cx2_norm) < 0.05 and abs(cy_norm - cy2_norm) < 0.05:
            from core.logger import log

            log.warning(
                "[cropper] Deteksi wajah Face 1 dan Face 2 sama/sangat dekat, melakukan fallback ke full_face."
            )
            return build_crop_command(
                temp_file,
                cropped_file,
                "full_face",
                out_w,
                out_h,
                cx_norm,
                cy_norm,
                cx2_norm,
                cy2_norm,
            )

        if config.output_ratio == "original" or not out_w or not out_h or out_h < out_w:
            # Fallback: jika rasio output tidak portrait, lakukan full mode saja
            vf = (
                build_cover_scale_crop_vf(out_w or 720, out_h or 1280)
                if config.output_ratio != "original"
                else None
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "info",
                "-i",
                temp_file,
            ]
            if vf:
                cmd.extend(["-vf", vf])
            cmd.extend(get_video_codec_args())
            cmd.extend(["-c:a", "aac", "-b:a", "128k", cropped_file])
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

            return (
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "info",
                    "-i",
                    temp_file,
                    "-filter_complex",
                    vf,
                    "-map",
                    "[out]",
                    "-map",
                    "0:a?",
                ]
                + get_video_codec_args()
                + ["-c:a", "aac", "-b:a", "128k", cropped_file]
            )

    elif crop_mode == "split_broll":
        if config.output_ratio == "original" or not out_w or not out_h or out_h < out_w:
            vf = (
                build_cover_scale_crop_vf(out_w or 720, out_h or 1280)
                if config.output_ratio != "original"
                else None
            )
            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "info",
                "-i",
                temp_file,
            ]
            if vf:
                cmd.extend(["-vf", vf])
            cmd.extend(get_video_codec_args())
            cmd.extend(["-c:a", "aac", "-b:a", "128k", cropped_file])
            return cmd
        else:
            import os
            import random
            import subprocess
            from core.logger import log
            from core.utils import get_app_root
            
            broll_dir = os.path.join(get_app_root(), "assets", "broll")
            broll_file = None
            if os.path.exists(broll_dir):
                brolls = [os.path.join(broll_dir, f) for f in os.listdir(broll_dir) if f.endswith((".mp4", ".mkv"))]
                if brolls:
                    broll_file = random.choice(brolls)
            
            if not broll_file:
                log.warning("[cropper] B-Roll file not found in assets/broll/. Falling back to split_face.")
                return build_crop_command(
                    temp_file,
                    cropped_file,
                    "split_face",
                    out_w,
                    out_h,
                    cx_norm,
                    cy_norm,
                    cx2_norm,
                    cy2_norm,
                    face_keyframes
                )

            # Komposisi 40:60 (40% video utama, 60% b-roll)
            top_h = int(out_h * 0.40)
            if top_h % 2 != 0:
                top_h -= 1
            bottom_h = out_h - top_h
            
            scaled = build_cover_scale_vf(out_w, out_h)
            
            # Baca durasi b-roll secara dinamis via ffprobe agar tidak hardcode
            # Gunakan binary ffprobe eksternal (BUKAN sys.executable — lihat AGENTS.md §1.4)
            random_start = 0
            try:
                probe_result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", broll_file],
                    capture_output=True, text=True
                )
                broll_duration = float(probe_result.stdout.strip())
                # Pastikan tidak mulai di detik terakhir agar transisi loop mulus
                max_start = max(0, int(broll_duration) - 1)
                if max_start > 0:
                    random_start = random.randint(0, max_start)
                log.info(f"[cropper] B-Roll duration: {broll_duration:.1f}s, random start: {random_start}s")
            except (ValueError, OSError) as e:
                log.warning(f"[cropper] Failed to probe b-roll duration, starting at 0s: {e}")

            # Top: Full Original Video (scaled to fit, with blurred background padding)
            # Bottom: B-Roll (scaled and cropped to fit the bottom half)
            vf = (
                # Buat background blur untuk video utama (top)
                f"[0:v]scale={out_w}:{top_h}:force_original_aspect_ratio=increase,crop={out_w}:{top_h},boxblur=20:20[bg_top];"
                # Scale video utama agar pas di dalam kotak top_h tanpa memotong (fit)
                f"[0:v]scale={out_w}:{top_h}:force_original_aspect_ratio=decrease[fg_top];"
                # Gabungkan video utama dengan background blurnya
                f"[bg_top][fg_top]overlay=(W-w)/2:(H-h)/2[top];"
                # B-roll dipotong (crop) agar memenuhi kotak bottom_h
                f"[1:v]scale={out_w}:{bottom_h}:force_original_aspect_ratio=increase,crop={out_w}:{bottom_h}[bottom];"
                # Tumpuk atas dan bawah
                f"[top][bottom]vstack[outv];"
                # Tambahkan suara broll sebesar 0.2 dan campur dengan suara video utama
                f"[1:a]volume=0.2[a_broll];"
                f"[0:a][a_broll]amix=inputs=2:duration=first[outa]"
            )

            return (
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "info",
                    "-i",
                    temp_file,
                    "-stream_loop", "-1",
                    "-ss", str(random_start),
                    "-i",
                    broll_file,
                    "-filter_complex",
                    vf,
                    "-map",
                    "[outv]",
                    "-map",
                    "[outa]",
                ]
                + get_video_codec_args()
                + ["-c:a", "aac", "-b:a", "128k", "-shortest", cropped_file]
            )

    raise ValueError(f"Unknown crop mode: {crop_mode}")
