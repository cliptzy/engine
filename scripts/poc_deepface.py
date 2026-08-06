import sys
import cv2
import argparse
import time
import os
import json

def test_deepface_video(media_path: str, interval_sec: float = 1.0):
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

    frame_interval = max(1, int(fps * interval_sec))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    emotion_timeline = []
    current_frame = 0
    
    import typing
    
    while current_frame < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if not ret or frame is None:
            break
            
        try:
            # Gunakan detector_backend='mtcnn' karena ini adalah raw video penuh
            result = DeepFace.analyze(frame, actions=['emotion'], detector_backend='mtcnn', enforce_detection=False, silent=False)
            print(result)
            
            dominant_emotion = None
            if isinstance(result, list) and len(result) > 0:
                face_data = typing.cast(dict, result[0])
                dominant_emotion = face_data.get('dominant_emotion')
            elif isinstance(result, dict):
                dominant_emotion = result.get('dominant_emotion')
                
            if dominant_emotion:
                timestamp_sec = current_frame / fps
                emotion_timeline.append({
                    "time": round(timestamp_sec, 2),
                    "emotion": dominant_emotion
                })
        except Exception:
            pass
            
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
                filtered_timeline.append({"time": t, "emotion": "neutral"})
        else:
            filtered_timeline.append(entry)
    
    # Cetak output sebagai JSON agar rapi
    print(json.dumps(filtered_timeline, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proof of Concept for DeepFace Emotion Detection (JSON Video Timeline)")
    parser.add_argument("media_path", type=str, help="Path to video file to test")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval in seconds between frames to analyze")
    args = parser.parse_args()
    
    test_deepface_video(args.media_path, args.interval)
