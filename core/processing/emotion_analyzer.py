import cv2
import os
from typing import Dict, List, Any
from core.logger import log

def analyze_video_emotions(video_path: str, cx_norm: float = 0.5, cy_norm: float = 0.5, interval_sec: float = 1.0) -> List[Dict[str, Any]]:
    """
    Mengekstrak frame dari video mentah (temporal cut) pada interval `interval_sec`.
    Melakukan cropping secara matematis pada frame berpusat di cx_norm dan cy_norm
    (hasil dari face_tracker.py) agar fokus murni pada wajah streamer tanpa terganggu elemen game.
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

        # Crop area untuk fokus ke wajah streamer (asumsi lebar wajah sekitar 30-40% dari ukuran layar pendek)
        # Atau kita ambil 40% dari tinggi layar sebagai dimensi kotak crop
        crop_size = int(min(w, h) * 0.4)

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
                # Gunakan detector_backend='mtcnn' untuk melacak wajah secara presisi di dalam kotak crop streamer
                result = DeepFace.analyze(cropped_face, actions=['emotion'], detector_backend='mtcnn', enforce_detection=False, silent=True)

                dominant_emotion = None
                emotion_scores = {}
                if isinstance(result, list) and len(result) > 0:
                    face_data = typing.cast(Dict[str, Any], result[0])
                    dominant_emotion = face_data.get('dominant_emotion')
                    emotion_scores = face_data.get('emotion', {})
                elif isinstance(result, dict):
                    dominant_emotion = result.get('dominant_emotion')
                    emotion_scores = result.get('emotion', {})

                # --- Pengurangan Sensitivitas ---
                # DeepFace sering over-sensitive. Kita turunkan sensitivitasnya
                # dengan mewajibkan skor persentase emosi > 55% untuk dianggap valid.
                if dominant_emotion and dominant_emotion != 'neutral':
                    score = emotion_scores.get(dominant_emotion, 0)
                    if score < 85.0:
                        dominant_emotion = 'neutral'



                if dominant_emotion:
                    timestamp_sec = current_frame / fps
                    actual_score = emotion_scores.get(dominant_emotion, 0)
                    data = {
                        "time": round(timestamp_sec, 2),
                        "emotion": dominant_emotion,
                        "score": round(float(actual_score), 1)
                    }
                    log.info(f"[visual emotion]: {data['time']} -> {data['emotion']} ({data['score']}%)")
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
                filtered_timeline.append({"time": t, "emotion": "neutral", "score": entry.get("score", 0)})
        else:
            filtered_timeline.append(entry)

    if filtered_timeline:
        log.info(f"Berhasil mengekstrak {len(filtered_timeline)} data emosi visual wajah dari klip.")
    else:
        log.info("Tidak ada emosi dominan yang terdeteksi secara visual.")

    return filtered_timeline
