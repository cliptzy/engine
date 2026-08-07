import cv2
import os
from typing import Dict, List, Any
from core.logger import log

def analyze_video_emotions(video_path: str, cx_norm: float = 0.5, cy_norm: float = 0.5, interval_sec: float = 1.0, crop_mode: str = "raw") -> List[Dict[str, Any]]:
    """
    Mengekstrak frame dari video pada interval `interval_sec`.
    Jika crop_mode adalah mode split (full_face, split_face, dll), kita potong (crop) separuh bawah layar
    untuk menghindari deteksi wajah pada game.
    Meneruskan frame crop tersebut ke DeepFace untuk mendeteksi emosi wajah dominan.
    """
    try:
        from deepface import DeepFace
    except ImportError:
        log.warning("Modul deepface belum terinstall. Lewati analisis emosi visual.")
        return []

    if not os.path.exists(video_path):
        return []

    log.info(f"Menganalisis emosi visual wajah (DeepFace) pada: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        log.warning(f"Tidak dapat membuka video {video_path} untuk DeepFace")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    frame_interval = max(1, int(fps * interval_sec))

    emotion_timeline = []
    current_frame = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    while current_frame < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        h, w = frame.shape[:2]

        # Selalu potong kotak kecil di sekitar wajah pada video raw (temp_file)
        crop_size = int(min(w, h) * 0.6)
        center_x = int(cx_norm * w)
        center_y = int(cy_norm * h)
        x1 = max(0, center_x - crop_size // 2)
        y1 = max(0, center_y - crop_size // 2)
        x2 = min(w, x1 + crop_size)
        y2 = min(h, y1 + crop_size)
        cropped_face = frame[y1:y2, x1:x2]

        if cropped_face.size > 0:
            try:
                import typing
                result = DeepFace.analyze(cropped_face, actions=['emotion'], detector_backend='mtcnn', enforce_detection=False, silent=True)

                dominant_emotion = None
                emotion_scores = {}
                region = {}
                if isinstance(result, list) and len(result) > 0:
                    face_data = typing.cast(Dict[str, Any], result[0])
                    dominant_emotion = face_data.get('dominant_emotion')
                    emotion_scores = face_data.get('emotion', {})
                    region = face_data.get('region', {})
                elif isinstance(result, dict):
                    dominant_emotion = result.get('dominant_emotion')
                    emotion_scores = result.get('emotion', {})
                    region = result.get('region', {})

                # Turunkan threshold menjadi 25.0 karena skor probabilitas dari 7 kelas sering terdistribusi
                if dominant_emotion and dominant_emotion != 'neutral':
                    score = emotion_scores.get(dominant_emotion, 0)
                    if score < 25.0:
                        dominant_emotion = 'neutral'

                if dominant_emotion:
                    timestamp_sec = current_frame / fps
                    actual_score = emotion_scores.get(dominant_emotion, 0)
                    final_box = {}

                    if region and crop_mode in ["split_left", "split_right", "split_face", "full_face"]:
                        # Kembalikan ke koordinat absolut raw video
                        raw_x = region.get('x', 0) + x1
                        raw_y = region.get('y', 0) + y1
                        raw_w = region.get('w', 0)
                        raw_h = region.get('h', 0)

                        # Kalkulasi matematis pemetaan (mapping) koordinat FFmpeg
                        from core.config import config
                        from core.ffmpeg import get_split_heights
                        out_w = config.out_width or 720
                        out_h = config.out_height or 1280
                        _, bottom_h = get_split_heights(out_h, config.bottom_height)
                        bottom_h = bottom_h or 400

                        S = max(out_w / w, out_h / h)
                        scaled_w = w * S
                        scaled_h = h * S

                        x_offset = max(0, min(w * cx_norm * S - out_w / 2, scaled_w - out_w))
                        y_offset = max(0, min(h * cy_norm * S - bottom_h / 2, scaled_h - bottom_h))

                        bottom_x = raw_x * S - x_offset
                        bottom_y = raw_y * S - y_offset

                        top_h = h * (out_w / w)
                        bg_y_offset = (out_h - (top_h + bottom_h)) / 2

                        final_x = bottom_x
                        final_y = bg_y_offset + top_h + bottom_y

                        final_box = {
                            'x': int(final_x), 'y': int(final_y),
                            'w': int(raw_w * S), 'h': int(raw_h * S)
                        }
                    elif region:
                        final_box = {k: int(v) for k, v in region.items() if k in ['x', 'y', 'w', 'h']}

                    data = {
                        "time": round(timestamp_sec, 2),
                        "emotion": dominant_emotion,
                        "score": round(float(actual_score), 1),
                        "box": final_box
                    }
                    log.info(f"[visual emotion]: {data['time']} -> {data['emotion']} ({data['score']}%) box={data['box']}")
                    emotion_timeline.append(data)
            except Exception as e:
                log.error(f"[visual emotion] Error: {e}")

        current_frame += frame_interval

    cap.release()

    # --- Terapkan Aturan Cooldown 5 Detik ---
    filtered_timeline = []
    last_non_neutral_time = -999.0

    for entry in emotion_timeline:
        t = entry["time"]
        emo = entry["emotion"]

        if emo != "neutral":
            if t - last_non_neutral_time >= 5.0:
                filtered_timeline.append(entry)
                last_non_neutral_time = t
            else:
                # Masih dalam cooldown 5 detik dari emosi non-netral sebelumnya
                filtered_timeline.append({"time": t, "emotion": "neutral", "score": entry.get("score", 0), "box": entry.get("box", {})})
        else:
            filtered_timeline.append(entry)

    if filtered_timeline:
        log.info(f"Berhasil mengekstrak {len(filtered_timeline)} data emosi visual wajah dari klip.")
    else:
        log.info("Tidak ada emosi dominan yang terdeteksi secara visual.")

    return filtered_timeline
