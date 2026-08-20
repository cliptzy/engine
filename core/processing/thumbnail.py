import os
import subprocess
from core.logger import log

def get_dominant_emotion(metadata: dict) -> str:
    import random
    from core.constant import VALID_EMOTIONS
    if not metadata:
        return random.choice(["happy", "shock", "confused"])
        
    visuals = metadata.get("visual_emotions", [])
    if visuals and isinstance(visuals, list):
        counts = {}
        for v in visuals:
            emo = v.get("emotion") if isinstance(v, dict) else v
            if emo and emo in VALID_EMOTIONS and emo != "neutral":
                counts[emo] = counts.get(emo, 0) + 1
        if counts:
            return max(counts, key=counts.get)
            
    transcript = metadata.get("enriched_transcript", [])
    if transcript and isinstance(transcript, list):
        counts = {}
        for w in transcript:
            emo = w.get("text_emotion") if isinstance(w, dict) else None
            if emo and emo in VALID_EMOTIONS and emo != "neutral":
                counts[emo] = counts.get(emo, 0) + 1
        if counts:
            return max(counts, key=counts.get)
            
    tags = metadata.get("tags", [])
    if isinstance(tags, list):
        for tag in tags:
            tag_clean = tag.replace("#", "").lower()
            if tag_clean in VALID_EMOTIONS:
                return tag_clean
                
def get_best_timestamp(metadata: dict) -> str:
    """Finds the best timestamp to extract a frame so subtitles/highlights are visible."""
    if metadata:
        # Jika ada highlight hook (yang biasanya tayang di 3 detik pertama), ambil dari detik ke-1
        if metadata.get("highlight"):
            return "00:00:01.000"
            
        transcript = metadata.get("enriched_transcript", [])
        if transcript and isinstance(transcript, list) and len(transcript) > 0:
            # Cari kata pertama yang diucapkan
            first_word = transcript[0]
            start_time = first_word.get("start")
            if start_time is not None:
                # Ambil sedikit setelah start agar teks pasti sudah muncul
                target_sec = float(start_time) + 0.1
                
                # Format ke HH:MM:SS.mmm
                hours = int(target_sec // 3600)
                minutes = int((target_sec % 3600) // 60)
                seconds = target_sec % 60
                return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
                
    return "00:00:01.000"

def generate_thumbnail(video_path: str, output_path: str, metadata: dict = None) -> bool:
    """
    Generate a thumbnail from a video file with emotion-based video effect overlay.
    
    Args:
        video_path: Path to the input video.
        output_path: Path to save the output thumbnail (e.g., .jpg).
        metadata: Optional metadata for emotion extraction.
        
    Returns:
        bool: True if generation is successful, False otherwise.
    """
    if not os.path.exists(video_path):
        log.error(f"Generate thumbnail failed: Video path does not exist: {video_path}")
        return False
        
    log.info(f"Generating dynamic thumbnail for {video_path}...")
    
    emotion = get_dominant_emotion(metadata)
    from core.video_effects import video_effect_manager
    from core.utils import get_app_root
    
    effect = video_effect_manager.get_effect(emotion)
    effect_path = None
    if effect:
        effect_file = effect.get("file")
        if effect_file:
            effect_path = os.path.join(get_app_root(), "assets", "video_effects", effect_file)
            if not os.path.exists(effect_path):
                effect_path = None
                
    best_time = get_best_timestamp(metadata)
    
    if effect_path:
        log.info(f"Overlaying video effect for emotion '{emotion}' onto thumbnail at {best_time}...")
        # FFmpeg filter complex to overlay effect onto main frame (No scaling, Green Screen Removal)
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-ss", best_time,
            "-i", video_path,
            "-ss", "00:00:01.000",
            "-i", effect_path,
            "-filter_complex",
            "[1:v]colorkey=0x00FF00:0.3:0.2,format=rgba[efx];[0:v]format=rgba[bg];[bg][efx]overlay=(W-w)/2:(H-h)/2[out]",
            "-map", "[out]",
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
    else:
        log.info(f"No effect found for emotion '{emotion}', generating standard thumbnail at {best_time}...")
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-ss", best_time,
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            log.error(f"Failed to generate thumbnail: {res.stderr}")
            return False
            
        # Optional Text Burning
        # If we have title in metadata, we could run another ffmpeg or ImageMagick pass here.
            
        log.info(f"Thumbnail successfully generated: {output_path}")
        return True
    except Exception as e:
        log.error(f"Exception during thumbnail generation: {e}")
        return False
