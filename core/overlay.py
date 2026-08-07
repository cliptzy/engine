import json
import os
import random
from typing import Optional
from core.utils import get_app_root

class OverlayManager:
    def __init__(self):
        self.overlay_file = os.path.join(get_app_root(), "overlay.json")
        self.overlay_map = {}
        self.load()

    def load(self):
        if os.path.exists(self.overlay_file):
            try:
                with open(self.overlay_file, 'r', encoding='utf-8') as f:
                    self.overlay_map = json.load(f)
            except Exception:
                self._load_default()
        else:
            self._load_default()
            self.save()

    def _load_default(self):
        # Struktur map: { emotion: [ { "file": "nama_file.ext", "effect": "transparent", "opacity": 0.5 } ] }
        # File media harus diletakkan di dalam assets/overlay/
        self.overlay_map = {
            "sad": [{"name": "Noice Effect", "file": "noice.mp4", "effect": "transparent", "opacity": 0.5}, {"name": "None (No Effect)"}],
            "shock": [{"name": "Noice Effect", "file": "noice.mp4", "effect": "transparent", "opacity": 0.5}, {"name": "None (No Effect)"}],
            "fear": [{"name": "Noice Effect", "file": "noice.mp4", "effect": "transparent", "opacity": 0.5}, {"name": "None (No Effect)"}],
            "angry": [{"name": "Noice Effect", "file": "noice.mp4", "effect": "transparent", "opacity": 0.5}, {"name": "None (No Effect)"}],
            "disgust": [{"name": "Noice Effect", "file": "noice.mp4", "effect": "transparent", "opacity": 0.5}, {"name": "None (No Effect)"}],
            "confused": [{"name": "Noice Effect", "file": "noice.mp4", "effect": "transparent", "opacity": 0.5}, {"name": "None (No Effect)"}],
            "happy": [{"name": "Noice Effect", "file": "noice.mp4", "effect": "transparent", "opacity": 0.5}, {"name": "None (No Effect)"}],
            "amused": [{"name": "Noice Effect", "file": "noice.mp4", "effect": "transparent", "opacity": 0.5}, {"name": "None (No Effect)"}],
            "transition": [{"name": "Noice Effect", "file": "noice.mp4", "effect": "transparent", "opacity": 0.5}, {"name": "None (No Effect)"}]
        }

    def save(self):
        with open(self.overlay_file, 'w', encoding='utf-8') as f:
            json.dump(self.overlay_map, f, indent=4)

    def get_random_overlay(self, emotion: str) -> Optional[dict]:
        if emotion in self.overlay_map and len(self.overlay_map[emotion]) > 0:
            return random.choice(self.overlay_map[emotion])
        return None

overlay_manager = OverlayManager()
