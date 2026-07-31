from dataclasses import dataclass
from typing import Optional

@dataclass
class AppConfig:
    """Application configuration container."""
    output_dir: str = "clips"
    max_duration: int = 60
    min_score: float = 0.40
    max_clips: int = 10
    padding: int = 10
    
    top_height: int = 960
    bottom_height: int = 320
    
    use_subtitle: bool = True
    whisper_model: str = "small"
    subtitle_font: str = "Arial"
    subtitle_fonts_dir: Optional[str] = None
    subtitle_location: str = "bottom"
    subtitle_delay: float = 0.0
    
    subtitle_font_size: int = 60
    subtitle_color: str = "&H0000FFFF"
    subtitle_bg_color: str = "&H80000000"
    subtitle_border_style: int = 3
    subtitle_animation: str = "none"
    subtitle_max_words: int = 3
    
    intro_video: Optional[str] = None
    outro_video: Optional[str] = None
    
    output_ratio: str = "9:16"
    out_width: Optional[int] = 720
    out_height: Optional[int] = 1280
    
    job_dir: str = ""

    crop_mode: str = "default"
    ui_locked: bool = False

    upload_youtube: bool = False
    upload_tiktok: bool = False
    upload_instagram: bool = False
    upload_interval: float = 0.0
    hw_accel: str = "cpu"
    

    yt_session: Optional[str] = "cred/yt_cookies.txt"
    yt_client_id: str = ""
    yt_client_secret: str = ""
    yt_visibility: str = "Public"
    yt_tags: str = "#Shorts #Viral #Cliptzy"
    yt_auto_upload: bool = False

    tt_session: str = "cred/tiktok_cookies.txt"
    tt_privacy: str = "Public (Semua Orang)"
    tt_caption: str = "Cuplikan seru hari ini! #fyp #viral"
    tt_auto_upload: bool = False

    ig_business_id: str = ""
    ig_access_token: str = ""
    ig_session: str = "cred/instagram_cookies.txt"
    ig_caption: str = "Best moment clip #reels #instagram"
    ig_auto_upload: bool = False

    ai_provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    gemini_key: str = ""
    gemini_model: str = "gemini-3.5-flash"

    openai_key: str = ""
    openai_model: str = "gpt-4o-mini"
    
    ai_prompt: str = ""
    use_highlight: bool = False

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
            "max_duration": self.max_duration,
            "min_score": self.min_score,
            "max_clips": self.max_clips,
            "padding": self.padding,
            "top_height": self.top_height,
            "bottom_height": self.bottom_height,
            "use_subtitle": self.use_subtitle,
            "use_highlight": self.use_highlight,
            "whisper_model": self.whisper_model,
            "subtitle_font": self.subtitle_font,
            "subtitle_fonts_dir": self.subtitle_fonts_dir,
            "subtitle_location": self.subtitle_location,
            "subtitle_delay": self.subtitle_delay,
            "subtitle_font_size": self.subtitle_font_size,
            "subtitle_color": self.subtitle_color,
            "subtitle_bg_color": self.subtitle_bg_color,
            "subtitle_border_style": self.subtitle_border_style,
            "subtitle_animation": self.subtitle_animation,
            "subtitle_max_words": self.subtitle_max_words,
            "yt_session": self.yt_session,
            "intro_video": self.intro_video,
            "outro_video": self.outro_video,
            "output_ratio": self.output_ratio,
            "crop_mode": self.crop_mode,
            "ui_locked": self.ui_locked,
            "upload_youtube": self.upload_youtube,
            "upload_tiktok": self.upload_tiktok,
            "upload_instagram": self.upload_instagram,
            "yt_client_id": self.yt_client_id,
            "yt_client_secret": self.yt_client_secret,
            "yt_visibility": self.yt_visibility,
            "yt_tags": self.yt_tags,
            "yt_auto_upload": self.yt_auto_upload,
            "tt_session": self.tt_session,
            "tt_privacy": self.tt_privacy,
            "tt_caption": self.tt_caption,
            "tt_auto_upload": self.tt_auto_upload,
            "ig_business_id": self.ig_business_id,
            "ig_access_token": self.ig_access_token,
            "ig_session": self.ig_session,
            "ig_caption": self.ig_caption,
            "ig_auto_upload": self.ig_auto_upload,
            "ai_provider": self.ai_provider,
            "ollama_host": self.ollama_host,
            "ollama_model": self.ollama_model,
            "gemini_key": self.gemini_key,
            "gemini_model": self.gemini_model,
            "openai_key": self.openai_key,
            "openai_model": self.openai_model,
            "ai_prompt": self.ai_prompt,
            "upload_interval": self.upload_interval,
            "hw_accel": self.hw_accel,
        }


    def update_from_dict(self, data: dict) -> None:
        """Updates configuration from dictionary."""
        if "output_dir" in data and data["output_dir"]:
            self.output_dir = data["output_dir"]
        if "max_duration" in data and data["max_duration"] is not None:
            self.max_duration = int(data["max_duration"])
        if "min_score" in data and data["min_score"] is not None:
            self.min_score = float(data["min_score"])
        if "max_clips" in data and data["max_clips"] is not None:
            self.max_clips = int(data["max_clips"])
        if "padding" in data and data["padding"] is not None:
            self.padding = int(data["padding"])
        if "use_subtitle" in data:
            self.use_subtitle = bool(data["use_subtitle"])
        if "use_highlight" in data:
            self.use_highlight = bool(data["use_highlight"])
        if "whisper_model" in data and data["whisper_model"]:
            self.whisper_model = data["whisper_model"]
        if "subtitle_font" in data and data["subtitle_font"]:
            self.subtitle_font = data["subtitle_font"]
        if "subtitle_fonts_dir" in data:
            self.subtitle_fonts_dir = data["subtitle_fonts_dir"]
        if "subtitle_location" in data and data["subtitle_location"]:
            self.subtitle_location = data["subtitle_location"]
        if "subtitle_delay" in data and data["subtitle_delay"] is not None:
            self.subtitle_delay = float(data["subtitle_delay"])
        if "subtitle_font_size" in data and data["subtitle_font_size"] is not None:
            self.subtitle_font_size = int(data["subtitle_font_size"])
        if "subtitle_color" in data and data["subtitle_color"]:
            self.subtitle_color = data["subtitle_color"]
        if "subtitle_bg_color" in data and data["subtitle_bg_color"]:
            self.subtitle_bg_color = data["subtitle_bg_color"]
        if "subtitle_border_style" in data and data["subtitle_border_style"] is not None:
            self.subtitle_border_style = int(data["subtitle_border_style"])
        if "subtitle_animation" in data and data["subtitle_animation"]:
            self.subtitle_animation = data["subtitle_animation"]
        if "subtitle_max_words" in data and data["subtitle_max_words"] is not None:
            self.subtitle_max_words = int(data["subtitle_max_words"])
        if "yt_session" in data:
            self.yt_session = data["yt_session"]
        if "intro_video" in data:
            self.intro_video = data["intro_video"]
        if "outro_video" in data:
            self.outro_video = data["outro_video"]
        if "output_ratio" in data and data["output_ratio"]:
            self.set_ratio_preset(data["output_ratio"])
        if "crop_mode" in data and data["crop_mode"]:
            self.crop_mode = data["crop_mode"]
        if "ui_locked" in data:
            self.ui_locked = bool(data["ui_locked"])
        if "upload_youtube" in data:
            self.upload_youtube = bool(data["upload_youtube"])
        if "upload_tiktok" in data:
            self.upload_tiktok = bool(data["upload_tiktok"])
        if "upload_instagram" in data:
            self.upload_instagram = bool(data["upload_instagram"])
            
        if "yt_client_id" in data: self.yt_client_id = data["yt_client_id"]
        if "yt_client_secret" in data: self.yt_client_secret = data["yt_client_secret"]
        if "yt_visibility" in data: self.yt_visibility = data["yt_visibility"]
        if "yt_tags" in data: self.yt_tags = data["yt_tags"]
        if "yt_auto_upload" in data: self.yt_auto_upload = bool(data["yt_auto_upload"])

        if "tt_session" in data: self.tt_session = data["tt_session"]
        if "tt_privacy" in data: self.tt_privacy = data["tt_privacy"]
        if "tt_caption" in data: self.tt_caption = data["tt_caption"]
        if "tt_auto_upload" in data: self.tt_auto_upload = bool(data["tt_auto_upload"])

        if "ig_business_id" in data: self.ig_business_id = data["ig_business_id"]
        if "ig_access_token" in data: self.ig_access_token = data["ig_access_token"]
        if "ig_session" in data: self.ig_session = data["ig_session"]
        if "ig_caption" in data: self.ig_caption = data["ig_caption"]
        if "ig_auto_upload" in data: self.ig_auto_upload = bool(data["ig_auto_upload"])
        
        if "ai_provider" in data and data["ai_provider"]:
            self.ai_provider = data["ai_provider"]
        if "ollama_host" in data and data["ollama_host"]:
            self.ollama_host = data["ollama_host"]
        if "ollama_model" in data and data["ollama_model"]:
            self.ollama_model = data["ollama_model"]
        if "gemini_key" in data:
            self.gemini_key = data["gemini_key"]
        if "gemini_model" in data and data["gemini_model"]:
            m = str(data["gemini_model"]).strip()
            if m.startswith("gemini-2.5"):
                m = "gemini-1.5-flash"
            self.gemini_model = m

        if "openai_key" in data:
            self.openai_key = data["openai_key"]
        if "openai_model" in data and data["openai_model"]:
            self.openai_model = data["openai_model"]
        if "ai_prompt" in data and data["ai_prompt"]:
            self.ai_prompt = data["ai_prompt"]
        if "upload_interval" in data:
            self.upload_interval = float(data["upload_interval"])
        if "hw_accel" in data and data["hw_accel"]:
            self.hw_accel = data["hw_accel"]


    def save_to_file(self, filepath: str = "config.json") -> bool:
        """Saves configuration to JSON file."""
        import json
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            return False

    def load_from_file(self, filepath: str = "config.json") -> bool:
        """Loads configuration from JSON file."""
        import json
        import os
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.update_from_dict(data)
            return True
        except Exception as e:
            return False

# Global configuration instance
config = AppConfig()

