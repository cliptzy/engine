import sys
import cv2
import argparse
import time
import os
import json
import typing

def test_deepface_video(media_path: str, interval_sec: float = 1.0, output_path: str = ""):
    try:
        # Suppress TensorFlow logging
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        from deepface import DeepFace
    except ImportError:
        print(json.dumps({"error": "deepface is not installed. Run 'python scripts/manage_reqs.py add deepface'"}, indent=2))
        return

    if not os.path.exists(media_path):
        print(json.dumps({"error": f"File not found: {media_path}"}, indent=2))
        return

    cap = cv2.VideoCapture(media_path)
    if not cap.isOpened():
        print(json.dumps({"error": f"Cannot read '{media_path}' as video."}, indent=2))
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if not output_path:
        base, ext = os.path.splitext(media_path)
        output_path = f"{base}_analyzed.mp4"

    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # type: ignore
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_interval = max(1, int(fps * interval_sec))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    emotion_timeline = []
    current_frame = 0

    current_emotion = None
    current_score = 0.0
    current_box = None

    print(f"Total frames: {total_frames}, Interval: {frame_interval} frames")

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        if current_frame % frame_interval == 0:
            print(f"Processing frame {current_frame}/{total_frames} with DeepFace...", end='\r')
            try:
                # Gunakan detector_backend='mtcnn' karena ini adalah raw video penuh
                result = DeepFace.analyze(frame, actions=['emotion'], detector_backend='mtcnn', enforce_detection=False, silent=True)

                dominant_emotion = None
                emotion_dict = {}
                region = {}

                if isinstance(result, list) and len(result) > 0:
                    face_data = typing.cast(dict, result[0])
                    dominant_emotion = face_data.get('dominant_emotion')
                    emotion_dict = face_data.get('emotion', {})
                    region = face_data.get('region', {})
                elif isinstance(result, dict):
                    dominant_emotion = result.get('dominant_emotion')
                    emotion_dict = result.get('emotion', {})
                    region = result.get('region', {})

                current_emotion = dominant_emotion
                current_box = region
                current_score = emotion_dict.get(dominant_emotion, 0) if dominant_emotion else 0.0

                if dominant_emotion:
                    timestamp_sec = current_frame / fps
                    emotion_timeline.append({
                        "time": round(float(timestamp_sec), 2),
                        "emotion": dominant_emotion,
                        "score": round(float(current_score), 1),
                        "box": {k: int(v) for k, v in region.items() if k in ['x', 'y', 'w', 'h']} if region else {}
                    })
            except Exception as e:
                print(f"\n[DeepFace Error on frame {current_frame}]: {e}")
                # Wajah tidak ditemukan
                current_emotion = None
                current_box = None

        # Gambar metadata dan kotak di frame
        if current_box and current_emotion:
            x = current_box.get('x', 0)
            y = current_box.get('y', 0)
            w = current_box.get('w', 0)
            h = current_box.get('h', 0)

            # Kotak merah
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 4)
            # Label
            text = f"{current_emotion} ({current_score:.1f}%)"
            # Background untuk teks
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            cv2.rectangle(frame, (x, max(0, y-30)), (x + text_w, max(0, y-30) + text_h + 10), (0, 0, 255), -1)
            cv2.putText(frame, text, (x, max(0, y-30) + text_h + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        out.write(frame)
        current_frame += 1

    print("\nVideo processing complete.")
    cap.release()
    out.release()

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
                filtered_timeline.append({"time": t, "emotion": "neutral", "score": entry.get("score"), "box": entry.get("box")})
        else:
            filtered_timeline.append(entry)

    # Cetak output sebagai JSON agar rapi
    print(json.dumps(filtered_timeline, indent=2))
    print(f"\nAnalyzed video saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proof of Concept for DeepFace Emotion Detection (JSON & Video Output)")
    parser.add_argument("media_path", type=str, help="Path to video file to test")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval in seconds between frames to analyze")
    parser.add_argument("--output", type=str, default="", help="Path for the output video file")
    args = parser.parse_args()

    test_deepface_video(args.media_path, args.interval, args.output)
