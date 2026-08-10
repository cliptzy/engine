import os
import random
from typing import Dict, List, Optional
from core.logger import log
from core.utils import get_app_root
from core.constant import VALID_EMOTIONS

class VideoEffectManager:
    def __init__(self):
        self.root = get_app_root()
        self.effects_dir = os.path.join(self.root, "assets", "video_effects")

        self.effects_map = {}
        for emo in VALID_EMOTIONS:
            json_path = os.path.join(self.root, "core", "constant", f"{emo}.json")
            if os.path.exists(json_path):
                import json
                with open(json_path, 'r', encoding='utf-8') as jf:
                    self.effects_map[emo] = json.load(jf)
            else:
                self.effects_map[emo] = []

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
