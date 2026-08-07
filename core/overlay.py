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
            "sad": [
                {"name": "Cry", "file": "cryy.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Patrick Sleep", "file": "patricksleep.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Sponge Smoke", "file": "spongesmoke.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "None (No Effect)"}
            ],
            "shock": [
                {"name": "Cat Shock", "file": "catshock.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Apa Coba", "file": "apacoba.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Apa Tuh", "file": "apatuh.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Sus", "file": "sus.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "None (No Effect)"}
            ],
            "fear": [
                {"name": "Cat Shock", "file": "catshock.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Apa Tuh", "file": "apatuh.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Uhhhh", "file": "uhhhh.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "None (No Effect)"}
            ],
            "angry": [
                {"name": "Patrick Dongo", "file": "patrickdongo.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Dongo", "file": "dongoo.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Apa Coba", "file": "apacoba.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "None (No Effect)"}
            ],
            "disgust": [
                {"name": "Iuh", "file": "iuhh.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Tai Lung Iuh", "file": "tailung-iuhhhh.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Apa Coba", "file": "apacoba.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Uhhhh", "file": "uhhhh.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "None (No Effect)"}
            ],
            "confused": [
                {"name": "Mikir Keras", "file": "mikirkeras.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Think", "file": "think.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Let Me Think", "file": "lemiting.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Uhhhh", "file": "uhhhh.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Apa Coba", "file": "apacoba.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Apa Tuh", "file": "apatuh.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Dongo", "file": "dongoo.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "None (No Effect)"}
            ],
            "happy": [
                {"name": "Nah Ini", "file": "nahini.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Terus Terang", "file": "terusterang.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Let Me Think", "file": "lemiting.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "None (No Effect)"}
            ],
            "amused": [
                {"name": "Patrick Dongo", "file": "patrickdongo.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Terus Terang", "file": "terusterang.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Nah Ini", "file": "nahini.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "Let Me Think", "file": "lemiting.jpg", "effect": "transparent", "opacity": 0.5},
                {"name": "None (No Effect)"}
            ],
            "transition": [
                # TIDAK BOLEH ADA EFEK
                {"name": "None (No Effect)"}
            ]
        }

    def save(self):
        with open(self.overlay_file, 'w', encoding='utf-8') as f:
            json.dump(self.overlay_map, f, indent=4)

    def get_random_overlay(self, emotion: str) -> Optional[dict]:
        if emotion in self.overlay_map and len(self.overlay_map[emotion]) > 0:
            return random.choice(self.overlay_map[emotion])
        return None

overlay_manager = OverlayManager()
