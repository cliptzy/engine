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
    
    cookies_file: Optional[str] = None
    intro_video: Optional[str] = None
    outro_video: Optional[str] = None
    
    output_ratio: str = "9:16"
    out_width: Optional[int] = 720
    out_height: Optional[int] = 1280

    ai_provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    gemini_key: str = ""
    gemini_model: str = "gemini-3.5-flash"

    openai_key: str = ""
    openai_model: str = "gpt-4o-mini"
    
    ai_prompt: str = ""

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
            "whisper_model": self.whisper_model,
            "subtitle_font": self.subtitle_font,
            "subtitle_fonts_dir": self.subtitle_fonts_dir,
            "subtitle_location": self.subtitle_location,
            "subtitle_delay": self.subtitle_delay,
            "cookies_file": self.cookies_file,
            "intro_video": self.intro_video,
            "outro_video": self.outro_video,
            "output_ratio": self.output_ratio,
            "ai_provider": self.ai_provider,
            "ollama_host": self.ollama_host,
            "ollama_model": self.ollama_model,
            "gemini_key": self.gemini_key,
            "gemini_model": self.gemini_model,
            "openai_key": self.openai_key,
            "openai_model": self.openai_model,
            "ai_prompt": self.ai_prompt,
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
        if "cookies_file" in data:
            self.cookies_file = data["cookies_file"]
        if "intro_video" in data:
            self.intro_video = data["intro_video"]
        if "outro_video" in data:
            self.outro_video = data["outro_video"]
        if "output_ratio" in data and data["output_ratio"]:
            self.set_ratio_preset(data["output_ratio"])
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

