import os
import random
from typing import Dict, List, Optional
from core.logger import log
from core.utils import get_app_root

class VideoEffectManager:
    def __init__(self):
        self.root = get_app_root()
        self.effects_dir = os.path.join(self.root, "assets", "video_effects")

        # Hardcoded video effects mapping
        # type: "greenscreen" (needs colorkey), "alpha" (transparent webm/mov), "fullscreen" (opaque overlay)
        self.effects_map: Dict[str, List[Dict]] = {
            "happy": [
                {"name": "Happy Jump", "file": "Shocked Face Meme.mp4", "type": "greenscreen", "key_color": "0x00FF00"}
            ],
            "sad": [
                {"name": "Happy Jump", "file": "Shocked Face Meme.mp4", "type": "greenscreen", "key_color": "0x00FF00"}
            ],
            "angry": [
                {"name": "Happy Jump", "file": "Shocked Face Meme.mp4", "type": "greenscreen", "key_color": "0x00FF00"}
            ],
            "shock": [
                {"name": "Happy Jump", "file": "Shocked Face Meme.mp4", "type": "greenscreen", "key_color": "0x00FF00"}
            ],
            "fear": [
                {"name": "Happy Jump", "file": "Shocked Face Meme.mp4", "type": "greenscreen", "key_color": "0x00FF00"}
            ],
            "disgust": [
                {"name": "Happy Jump", "file": "Shocked Face Meme.mp4", "type": "greenscreen", "key_color": "0x00FF00"}
            ],
            "neutral": [],
            "fun": [
                {"name": "Happy Jump", "file": "Shocked Face Meme.mp4", "type": "greenscreen", "key_color": "0x00FF00"}
            ],
            "laugh": [
                {"name": "Happy Jump", "file": "Shocked Face Meme.mp4", "type": "greenscreen", "key_color": "0x00FF00"}
            ],
            "love": [
                {"name": "Happy Jump", "file": "Shocked Face Meme.mp4", "type": "greenscreen", "key_color": "0x00FF00"}
            ]
        }

        # Ensure directory exists but don't create JSON config
        os.makedirs(self.effects_dir, exist_ok=True)
        log.info("[VideoEffectManager] Loaded hardcoded video effects")

    def get_effect(self, emotion: str) -> Optional[Dict]:
        """
        Returns a random video effect for the given emotion, or None if empty.
        """
        effects = self.effects_map.get(emotion, [])
        if not effects:
            return None
        effect = random.choice(effects)
        # Check if file actually exists
        file_path = os.path.join(self.effects_dir, effect.get("file", ""))
        if not os.path.exists(file_path):
            return None
        return effect

    def get_effect_by_name(self, name: str) -> Optional[Dict]:
        for effects in self.effects_map.values():
            for effect in effects:
                if effect.get("name") == name:
                    return effect
        return None

    def get_all_effect_names(self) -> List[str]:
        names = []
        for effects in self.effects_map.values():
            for effect in effects:
                n = effect.get("name")
                if n and n not in names:
                    names.append(n)
        return names

video_effect_manager = VideoEffectManager()
