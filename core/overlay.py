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
        # Struktur map: { emotion: [ { "file": "nama_file.ext", "effect": "random" } ] }
        # File media harus diletakkan di dalam assets/overlay/
        self.overlay_map = {
            "sad": [
                {"name": "Cry", "file": "cryy.jpg", "effect": "random"},
                {"name": "Patrick Sleep", "file": "patricksleep.jpg", "effect": "random"},
                {"name": "Sponge Smoke", "file": "spongesmoke.jpg", "effect": "random"},
                {"name": "None (No Effect)"}
            ],
            "shock": [
                {"name": "Cat Shock", "file": "catshock.jpg", "effect": "random"},
                {"name": "Apa Coba", "file": "apacoba.jpg", "effect": "random"},
                {"name": "Apa Tuh", "file": "apatuh.jpg", "effect": "random"},
                {"name": "Sus", "file": "sus.jpg", "effect": "random"},
                {"name": "None (No Effect)"}
            ],
            "fear": [
                {"name": "Cat Shock", "file": "catshock.jpg", "effect": "random"},
                {"name": "Apa Tuh", "file": "apatuh.jpg", "effect": "random"},
                {"name": "Uhhhh", "file": "uhhhh.jpg", "effect": "random"},
                {"name": "None (No Effect)"}
            ],
            "angry": [
                {"name": "Patrick Dongo", "file": "patrickdongo.jpg", "effect": "random"},
                {"name": "Dongo", "file": "dongoo.jpg", "effect": "random"},
                {"name": "Apa Coba", "file": "apacoba.jpg", "effect": "random"},
                {"name": "Angry Cat", "file": "angry-cat.gif", "effect": "random"},
                {"name": "None (No Effect)"}
            ],
            "disgust": [
                {"name": "Iuh", "file": "iuhh.jpg", "effect": "random"},
                {"name": "Tai Lung Iuh", "file": "tailung-iuhhhh.jpg", "effect": "random"},
                {"name": "Apa Coba", "file": "apacoba.jpg", "effect": "random"},
                {"name": "Uhhhh", "file": "uhhhh.jpg", "effect": "random"},
                {"name": "None (No Effect)"}
            ],
            "confused": [
                {"name": "Mikir Keras", "file": "mikirkeras.jpg", "effect": "random"},
                {"name": "Think", "file": "think.jpg", "effect": "random"},
                {"name": "Let Me Think", "file": "lemiting.jpg", "effect": "random"},
                {"name": "Uhhhh", "file": "uhhhh.jpg", "effect": "random"},
                {"name": "Apa Coba", "file": "apacoba.jpg", "effect": "random"},
                {"name": "Apa Tuh", "file": "apatuh.jpg", "effect": "random"},
                {"name": "Dongo", "file": "dongoo.jpg", "effect": "random"},
                {"name": "None (No Effect)"}
            ],
            "happy": [
                {"name": "Nah Ini", "file": "nahini.jpg", "effect": "random"},
                {"name": "Terus Terang", "file": "terusterang.jpg", "effect": "random"},
                {"name": "Let Me Think", "file": "lemiting.jpg", "effect": "random"},
                {"name": "None (No Effect)"}
            ],
            "amused": [
                {"name": "Patrick Dongo", "file": "patrickdongo.jpg", "effect": "random"},
                {"name": "Terus Terang", "file": "terusterang.jpg", "effect": "random"},
                {"name": "Nah Ini", "file": "nahini.jpg", "effect": "random"},
                {"name": "Let Me Think", "file": "lemiting.jpg", "effect": "random"},
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

    def get_filter_strings(self, i: int, ov_idx: int, ov_start: float, ov_end: float, effect: str) -> tuple[str, str]:
        duration = ov_end - ov_start
        base_filter = f"[{ov_idx}:v]setpts=PTS-STARTPTS+{ov_start}/TB,format=argb"
        
        if effect == "random":
            effect = random.choice(["transparent", "blocking"])
            
        if effect == "transparent":
            fade_d = min(0.5, duration / 2)
            fade_st = ov_end - fade_d
            ov_filter = f"{base_filter},scale=720:-1,colorchannelmixer=aa=0.5,fade=t=out:st={fade_st}:d={fade_d}:alpha=1[ov_processed_{i}]"
            overlay_cmd = "overlay=shortest=1:x=(W-w)/2:y=(H-h)/2"
        elif effect == "blocking":
            # Solid (tanpa transparansi), dimensi lebih kecil, diletakkan di kiri tengah
            ov_filter = f"{base_filter},scale=300:-1[ov_processed_{i}]"
            overlay_cmd = "overlay=shortest=1:x=20:y=(H-h)/2"
        else:
            ov_filter = f"{base_filter},scale=720:-1[ov_processed_{i}]"
            overlay_cmd = "overlay=shortest=1:x=(W-w)/2:y=(H-h)/2"
            
        return ov_filter, overlay_cmd

overlay_manager = OverlayManager()
