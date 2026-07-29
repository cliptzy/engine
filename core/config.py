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

# Global configuration instance
config = AppConfig()
