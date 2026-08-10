from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SubtitleConfig:
    enabled: bool = True
    style: str = "plain"
    whisper_model: str = "small"
    font: str = "Arial"
    fonts_dir: Optional[str] = None
    location: str = "bottom"
    delay: float = 0.0
    font_size: int = 60
    color: str = "&H0000FFFF"
    bg_color: str = "&H80000000"
    border_style: int = 3
    animation: str = "none"
    max_words: int = 3

@dataclass
class AIConfig:
    provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    gemini_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    openai_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = ""
    use_highlight: bool = False
    use_generate_intro: bool = False
    use_emotion_detection: bool = True
    use_voice_analysis: bool = True

@dataclass
class YoutubeConfig:
    upload: bool = False
    session: Optional[str] = "cred/yt_cookies.txt"
    client_id: str = ""
    client_secret: str = ""
    visibility: str = "Public"
    auto_upload: bool = False

@dataclass
class TikTokConfig:
    upload: bool = False
    session: str = "cred/tiktok_cookies.txt"
    privacy: str = "Public (Semua Orang)"
    auto_upload: bool = False

@dataclass
class InstagramConfig:
    upload: bool = False
    business_id: str = ""
    access_token: str = ""
    session: str = "cred/instagram_cookies.txt"
    auto_upload: bool = False

import os
import sys

from core.utils import get_app_root

APP_ROOT = get_app_root()

@dataclass
class AppConfig:
    """Application configuration container."""
    output_dir: str = os.path.join(APP_ROOT, "clips")
    min_duration: int = 60
    min_score: float = 0.40
    max_clips: int = 10
    padding: int = 10
    
    top_height: int = 960
    bottom_height: int = 320
    
    intro_video: Optional[str] = None
    outro_video: Optional[str] = None
    watermark_image: Optional[str] = None
    video_frame: Optional[str] = None
    watermark_position: str = "center"
    
    output_ratio: str = "9:16"
    out_width: Optional[int] = 720
    out_height: Optional[int] = 1280
    
    job_dir: str = ""

    crop_mode: str = "default"
    merge_clips: bool = False
    ui_locked: bool = False

    upload_interval: float = 0.0
    hw_accel: str = "cpu"
    
    debug_mode: bool = False
    
    max_workers: int = 2
    max_effects_per_clip: int = 3
    
    tts_language: str = "default"
    tts_voice: str = "female"
    
    default_hashtags: str = "#Shorts #Viral #Cliptzy #fyp"
    
    subtitle: SubtitleConfig = field(default_factory=SubtitleConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    youtube: YoutubeConfig = field(default_factory=YoutubeConfig)
    tiktok: TikTokConfig = field(default_factory=TikTokConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)

    def set_ratio_preset(self, preset: str) -> None:
        """Sets the output resolution based on the given ratio preset."""
        self.output_ratio = preset
        if preset == "9:16":
            self.out_width, self.out_height = 720, 1280
        elif preset == "1:1":
            self.out_width, self.out_height = 720, 720
        elif preset == "16:9":
            self.out_width, self.out_height = 1280, 720
        elif preset == "original":
            self.out_width, self.out_height = None, None
        else:
            raise ValueError(f"Invalid ratio preset: {preset}")

    def to_dict(self) -> dict:
        """Exports configuration to dictionary."""
        return {
            "output_dir": self.output_dir,
            "min_duration": self.min_duration,
            "min_score": self.min_score,
            "max_clips": self.max_clips,
            "padding": self.padding,
            "top_height": self.top_height,
            "bottom_height": self.bottom_height,
            
            "use_subtitle": self.subtitle.enabled,
            "use_highlight": self.ai.use_highlight,
            "use_generate_intro": self.ai.use_generate_intro,
            "use_emotion_detection": self.ai.use_emotion_detection,
            "use_voice_analysis": self.ai.use_voice_analysis,
            "whisper_model": self.subtitle.whisper_model,
            "subtitle_font": self.subtitle.font,
            "subtitle_fonts_dir": self.subtitle.fonts_dir,
            "subtitle_location": self.subtitle.location,
            "subtitle_delay": self.subtitle.delay,
            "subtitle_font_size": self.subtitle.font_size,
            "subtitle_color": self.subtitle.color,
            "subtitle_bg_color": self.subtitle.bg_color,
            "subtitle_border_style": self.subtitle.border_style,
            "subtitle_animation": self.subtitle.animation,
            "subtitle_style": self.subtitle.style,
            "subtitle_max_words": self.subtitle.max_words,
            
            "yt_session": self.youtube.session,
            "intro_video": self.intro_video,
            "outro_video": self.outro_video,
            "watermark_image": self.watermark_image,
            "video_frame": self.video_frame,
            "watermark_position": self.watermark_position,
            "output_ratio": self.output_ratio,
            "crop_mode": self.crop_mode,
            "merge_clips": self.merge_clips,
            "ui_locked": self.ui_locked,
            "default_hashtags": self.default_hashtags,
            "max_workers": self.max_workers,
            "max_effects_per_clip": self.max_effects_per_clip,
            
            "upload_youtube": self.youtube.upload,
            "upload_tiktok": self.tiktok.upload,
            "upload_instagram": self.instagram.upload,
            
            "yt_client_id": self.youtube.client_id,
            "yt_client_secret": self.youtube.client_secret,
            "yt_visibility": self.youtube.visibility,
            "yt_auto_upload": self.youtube.auto_upload,
            
            "tt_session": self.tiktok.session,
            "tt_privacy": self.tiktok.privacy,
            "tt_auto_upload": self.tiktok.auto_upload,
            
            "ig_business_id": self.instagram.business_id,
            "ig_access_token": self.instagram.access_token,
            "ig_session": self.instagram.session,
            "ig_auto_upload": self.instagram.auto_upload,
            
            "ai_provider": self.ai.provider,
            "ollama_host": self.ai.ollama_host,
            "ollama_model": self.ai.ollama_model,
            "gemini_key": self.ai.gemini_key,
            "gemini_model": self.ai.gemini_model,
            "openai_key": self.ai.openai_key,
            "openai_model": self.ai.openai_model,
            "openai_base_url": self.ai.openai_base_url,
            
            "tts_language": self.tts_language,
            "tts_voice": self.tts_voice,
            "upload_interval": self.upload_interval,
            "hw_accel": self.hw_accel,
        }

    def update_from_dict(self, data: dict) -> None:
        """Updates configuration from dictionary."""
        if "output_dir" in data and data["output_dir"]:
            self.output_dir = data["output_dir"]
        if "min_duration" in data and data["min_duration"] is not None:
            self.min_duration = int(data["min_duration"])
        elif "max_duration" in data and data["max_duration"] is not None:
            self.min_duration = int(data["max_duration"])
        if "min_score" in data and data["min_score"] is not None:
            self.min_score = float(data["min_score"])
        if "max_clips" in data and data["max_clips"] is not None:
            self.max_clips = int(data["max_clips"])
        if "padding" in data and data["padding"] is not None:
            self.padding = int(data["padding"])
            
        if "use_subtitle" in data:
            self.subtitle.enabled = bool(data["use_subtitle"])
        if "use_highlight" in data:
            self.ai.use_highlight = bool(data["use_highlight"])
        if "use_generate_intro" in data:
            self.ai.use_generate_intro = bool(data["use_generate_intro"])
        if "use_emotion_detection" in data:
            self.ai.use_emotion_detection = bool(data["use_emotion_detection"])
        if "use_voice_analysis" in data:
            self.ai.use_voice_analysis = bool(data["use_voice_analysis"])
            
        if "whisper_model" in data and data["whisper_model"]:
            self.subtitle.whisper_model = data["whisper_model"]
        if "subtitle_font" in data and data["subtitle_font"]:
            self.subtitle.font = data["subtitle_font"]
        if "subtitle_fonts_dir" in data:
            self.subtitle.fonts_dir = data["subtitle_fonts_dir"]
        if "subtitle_location" in data and data["subtitle_location"]:
            self.subtitle.location = data["subtitle_location"]
        if "subtitle_delay" in data and data["subtitle_delay"] is not None:
            self.subtitle.delay = float(data["subtitle_delay"])
        if "subtitle_font_size" in data and data["subtitle_font_size"] is not None:
            self.subtitle.font_size = int(data["subtitle_font_size"])
        if "subtitle_color" in data and data["subtitle_color"]:
            self.subtitle.color = data["subtitle_color"]
        if "subtitle_bg_color" in data and data["subtitle_bg_color"]:
            self.subtitle.bg_color = data["subtitle_bg_color"]
        if "subtitle_border_style" in data and data["subtitle_border_style"] is not None:
            self.subtitle.border_style = int(data["subtitle_border_style"])
        if "subtitle_animation" in data and data["subtitle_animation"]:
            self.subtitle.animation = data["subtitle_animation"]
        if "subtitle_style" in data and data["subtitle_style"]:
            self.subtitle.style = data["subtitle_style"]
        if "subtitle_max_words" in data and data["subtitle_max_words"] is not None:
            self.subtitle.max_words = int(data["subtitle_max_words"])
            
        if "yt_session" in data:
            self.youtube.session = data["yt_session"]
        if "intro_video" in data:
            self.intro_video = data["intro_video"]
        if "outro_video" in data:
            self.outro_video = data["outro_video"]
        if "watermark_image" in data:
            self.watermark_image = data["watermark_image"]
        if "video_frame" in data:
            self.video_frame = data["video_frame"]
        if "watermark_position" in data:
            self.watermark_position = data["watermark_position"]
        if "output_ratio" in data and data["output_ratio"]:
            self.set_ratio_preset(data["output_ratio"])
        if "crop_mode" in data and data["crop_mode"]:
            self.crop_mode = data["crop_mode"]
        if "merge_clips" in data:
            self.merge_clips = bool(data["merge_clips"])
        if "ui_locked" in data:
            self.ui_locked = bool(data["ui_locked"])
        if "max_workers" in data:
            self.max_workers = int(data["max_workers"])
        if "max_effects_per_clip" in data and data["max_effects_per_clip"] is not None:
            self.max_effects_per_clip = int(data["max_effects_per_clip"])
        if "default_hashtags" in data:
            self.default_hashtags = data["default_hashtags"]
            
        if "upload_youtube" in data:
            self.youtube.upload = bool(data["upload_youtube"])
        if "upload_tiktok" in data:
            self.tiktok.upload = bool(data["upload_tiktok"])
        if "upload_instagram" in data:
            self.instagram.upload = bool(data["upload_instagram"])
            
        if "yt_client_id" in data: self.youtube.client_id = data["yt_client_id"]
        if "yt_client_secret" in data: self.youtube.client_secret = data["yt_client_secret"]
        if "yt_visibility" in data: self.youtube.visibility = data["yt_visibility"]
        if "yt_auto_upload" in data: self.youtube.auto_upload = bool(data["yt_auto_upload"])

        if "tt_session" in data: self.tiktok.session = data["tt_session"]
        if "tt_privacy" in data: self.tiktok.privacy = data["tt_privacy"]
        if "tt_auto_upload" in data: self.tiktok.auto_upload = bool(data["tt_auto_upload"])

        if "ig_business_id" in data: self.instagram.business_id = data["ig_business_id"]
        if "ig_access_token" in data: self.instagram.access_token = data["ig_access_token"]
        if "ig_session" in data: self.instagram.session = data["ig_session"]
        if "ig_auto_upload" in data: self.instagram.auto_upload = bool(data["ig_auto_upload"])
        
        if "ai_provider" in data and data["ai_provider"]:
            self.ai.provider = data["ai_provider"]
        if "ollama_host" in data and data["ollama_host"]:
            self.ai.ollama_host = data["ollama_host"]
        if "ollama_model" in data and data["ollama_model"]:
            self.ai.ollama_model = data["ollama_model"]
        if "gemini_key" in data:
            self.ai.gemini_key = data["gemini_key"]
        if "gemini_model" in data and data["gemini_model"]:
            m = str(data["gemini_model"]).strip()
            if m.startswith("gemini-2.5"):
                m = "gemini-1.5-flash"
            self.ai.gemini_model = m

        if "openai_key" in data:
            self.ai.openai_key = data["openai_key"]
        if "openai_model" in data and data["openai_model"]:
            self.ai.openai_model = data["openai_model"]
        if "openai_base_url" in data:
            self.ai.openai_base_url = data["openai_base_url"]
            
        if "tts_language" in data:
            self.tts_language = data["tts_language"]
        if "tts_voice" in data:
            self.tts_voice = data["tts_voice"]
        if "upload_interval" in data:
            self.upload_interval = float(data["upload_interval"])
        if "hw_accel" in data and data["hw_accel"]:
            self.hw_accel = data["hw_accel"]


    def save_to_file(self, filepath: str = "config.json") -> bool:
        """Saves configuration to JSON file."""
        from core.utils import write_json
        w = write_json(filepath, self.to_dict(), indent=2)
        if w:
            self.load_from_file(filepath)
        return w

    def load_from_file(self, filepath: str = "config.json") -> bool:
        """Loads configuration from JSON file."""
        import os
        from core.utils import read_json
        if not os.path.exists(filepath):
            return False
        data = read_json(filepath)
        if data:
            self.update_from_dict(data)
            return True
        return False

    def get_files_to_sync(self) -> list:
        """Returns a list of credential/session files to sync."""
        files = ["cred/youtube_token.json"]
        if self.tiktok.session: files.append(self.tiktok.session)
        if self.youtube.session: files.append(self.youtube.session)
        if self.instagram.session: files.append(self.instagram.session)
        return files

    def ensure_cred_dir(self) -> None:
        """Ensures the credential directory exists."""
        import os
        os.makedirs("cred", exist_ok=True)

# Global configuration instance
config = AppConfig()
