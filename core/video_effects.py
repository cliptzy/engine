import os
import random
from typing import Dict, List, Optional

from core.constant import VALID_EMOTIONS
from core.logger import log
from core.utils import get_app_root


class VideoEffectManager:
    def __init__(self):
        self.root = get_app_root()
        self.effects_dir = os.path.join(self.root, "assets", "video_effects")

        self.effects_map = {}
        self.all_effects = []

        json_path = os.path.join(self.root, "core", "constant", "video_effects.json")
        if os.path.exists(json_path):
            import json

            with open(json_path, "r", encoding="utf-8") as jf:
                self.all_effects = json.load(jf)

            for effect in self.all_effects:
                emotions = effect.get("emotions", [])
                for emo in emotions:
                    if emo not in self.effects_map:
                        self.effects_map[emo] = []
                    self.effects_map[emo].append(effect)

        for emo in VALID_EMOTIONS:
            if emo not in self.effects_map:
                self.effects_map[emo] = []

        # Ensure directory exists but don't create JSON config
        os.makedirs(self.effects_dir, exist_ok=True)
        log.info("[VideoEffectManager] Loaded consolidated video effects")

    def get_effect(
        self, emotion: str, exclude: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Returns a random video effect for the given emotion, or None if empty.
        """
        effects = self.effects_map.get(emotion, [])
        if not effects:
            return None
            
        # Filter out excluded effects if there are still alternatives left
        valid_effects = []
        for e in effects:
            file_path = os.path.join(self.effects_dir, e.get("file", ""))
            if os.path.exists(file_path):
                if not exclude or e.get("name") not in exclude:
                    valid_effects.append(e)
                    
        # If all valid effects were excluded, fallback to any existing effect
        if not valid_effects:
            for e in effects:
                file_path = os.path.join(self.effects_dir, e.get("file", ""))
                if os.path.exists(file_path):
                    valid_effects.append(e)
                    
        if not valid_effects:
            return None
            
        return random.choice(valid_effects)

    def get_effect_by_name(self, name: str) -> Optional[Dict]:
        normalized = name.replace("_", " ").lower()
        for effect in self.all_effects:
            en = effect.get("name", "")
            if en.replace("_", " ").lower() == normalized:
                return effect
        return None

    def get_all_effect_names(self) -> List[str]:
        names = []
        for effect in self.all_effects:
            n = effect.get("name")
            if n and n not in names:
                names.append(n)
        return names


video_effect_manager = VideoEffectManager()
