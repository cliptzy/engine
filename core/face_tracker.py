import cv2
import os
from core.logger import log

def get_dominant_face_normalized_center(video_path: str, max_samples: int = 10) -> tuple[float | None, float | None, str]:
    """
    Reads a video and samples frames to detect faces.
    Returns the median normalized center (cx_norm, cy_norm, error_message) of the largest face detected.
    Values are between 0.0 and 1.0.
    Returns (None, None, error_message) if no face is detected or if an error occurs.
    """
    if not os.path.exists(video_path):
        return None, None, "File video tidak ditemukan."

    try:
        import sys
        model_dir = "models"
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "face_detection_yunet.onnx")
        
        if not os.path.exists(model_path):
            log.info(f"YuNet model not found. Downloading to {model_path}...")
            import urllib.request
            url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
            try:
                urllib.request.urlretrieve(url, model_path)
                log.info("YuNet model downloaded successfully.")
            except Exception as e:
                log.error(f"Failed to download YuNet model: {e}")
                return None, None, "Gagal mengunduh model AI pendeteksi wajah (YuNet). Pastikan koneksi internet stabil."

        cap = cv2.VideoCapture(video_path)
        
        frames_list = []
        
        # Check if OpenCV can read the file
        ret, test_frame = cap.read()
        if not cap.isOpened() or not ret:
            log.info("OpenCV VideoCapture failed (likely codec issue). Falling back to FFmpeg frame extraction...")
            cap.release()
            try:
                import tempfile
                import glob
                import subprocess
                tmpdir = tempfile.mkdtemp()
                
                cmd = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", video_path,
                    "-vf", "fps=1",
                    "-vframes", str(max_samples),
                    os.path.join(tmpdir, "frame_%03d.jpg")
                ]
                subprocess.run(cmd, check=True)
                
                for fpath in glob.glob(os.path.join(tmpdir, "*.jpg")):
                    img = cv2.imread(fpath)
                    if img is not None:
                        frames_list.append(img)
                        
                import shutil
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception as e:
                log.warning(f"FFmpeg fallback extraction failed: {e}")
        else:
            # OpenCV works, append the first frame we already read
            frames_list.append(test_frame)
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if frame_count <= 0:
                frame_count = 300  # Fallback

            step = max(1, frame_count // max_samples)
            for i in range(1, max_samples):
                frame_id = i * step
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
                r, frame = cap.read()
                if r and frame is not None:
                    frames_list.append(frame)
            cap.release()

        if not frames_list:
            return None, None, "Sistem gagal membaca stream video (kemungkinan codec tidak didukung)."

        centers = []
        detector = None
        
        for frame in frames_list:
            h, w = frame.shape[:2]
            
            # Downscale frame if it's too large to improve speed
            scale_ratio = 1.0
            max_dim = 1280
            if max(h, w) > max_dim:
                scale_ratio = max_dim / float(max(h, w))
                frame = cv2.resize(frame, (0,0), fx=scale_ratio, fy=scale_ratio)
                h, w = frame.shape[:2]
            
            if detector is None:
                # Create detector on first frame with exact dimensions
                detector = cv2.FaceDetectorYN.create(
                    model_path,
                    "",
                    (w, h),
                    score_threshold=0.6,
                    nms_threshold=0.3,
                    top_k=5000
                )
            else:
                detector.setInputSize((w, h))
            
            # Detect faces
            ret, faces = detector.detect(frame)
            
            if faces is not None and len(faces) > 0:
                # Find the largest face by bounding box area (w * h)
                # faces format: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                x, y, fw, fh = largest_face[:4]
                
                # Map coordinates back to original scale
                x = x / scale_ratio
                y = y / scale_ratio
                fw = fw / scale_ratio
                fh = fh / scale_ratio
                
                # Calculate original image center
                orig_h, orig_w = h / scale_ratio, w / scale_ratio
                
                cx = x + fw / 2.0
                cy = y + fh / 2.0
                centers.append((cx / orig_w, cy / orig_h))

        if not centers:
            log.info("No face detected in sampled frames.")
            return None, None, "Secara alami tidak ada wajah manusia (atau terlalu buram) yang terdeteksi pada klip ini."

        # Calculate median center to ignore outliers
        centers.sort(key=lambda c: c[0])
        median_cx = centers[len(centers) // 2][0]
        
        centers.sort(key=lambda c: c[1])
        median_cy = centers[len(centers) // 2][1]
        
        log.info(f"Dominant face detected at normalized center ({median_cx:.2f}, {median_cy:.2f})")
        return median_cx, median_cy, ""

    except Exception as e:
        log.warning(f"Face tracking error: {e}")
        return None, None, f"Kesalahan sistem saat deteksi wajah: {str(e)}"
