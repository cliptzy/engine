import json
import os
import random
from core.utils import get_app_root

class VFXManager:
    def __init__(self):
        self.vfx_file = os.path.join(get_app_root(), "vfx.json")
        self.vfx_map = {}
        self.load()

    def load(self):
        if os.path.exists(self.vfx_file):
            try:
                with open(self.vfx_file, 'r', encoding='utf-8') as f:
                    self.vfx_map = json.load(f)
            except Exception:
                self._load_default()
        else:
            self._load_default()
            self.save()

    def _load_default(self):
        self.vfx_map = {
            "sad": [
                {"name": "B&W Standard", "vf": ["hue=s=0"], "af": ["lowpass=f=500"]},
                {"name": "Dark B&W", "vf": ["hue=s=0.1", "eq=brightness=-0.1"], "af": ["lowpass=f=400"]},
                {"name": "None (No Effect)"}
            ],
            "bored": [
                {"name": "Faded", "vf": ["hue=s=0.2"], "af": []},
                {"name": "Washed Out", "vf": ["hue=s=0.3", "eq=contrast=0.8"], "af": []},
                {"name": "None (No Effect)"}
            ],
            "shock": [
                {
                    "name": "High Contrast & Tremolo",
                    "vf": ["eq=brightness=0.4:contrast=1.5"],
                    "af": ["bass=g=5", "tremolo=f=10:d=0.5"]
                },
                {
                    "name": "Cyan Tint & Deep Bass",
                    "vf": ["hue=h=180:s=2"],
                    "af": ["bass=g=7"]
                },
                {
                    "name": "Invert Colors",
                    "vf": ["colorchannelmixer=rr=-1:gg=-1:bb=-1"],
                    "af": ["tremolo=f=10:d=0.8"]
                },
                {"name": "None (No Effect)"}
            ],
            "fear": [
                {"name": "Dark & High Contrast", "vf": ["eq=brightness=-0.3:contrast=1.2"], "af": []},
                {"name": "Dark & Tremolo", "vf": ["eq=brightness=-0.2", "hue=s=0.2"], "af": ["tremolo=f=5:d=0.8"]},
                {"name": "None (No Effect)"}
            ],
            "angry": [
                {"name": "Red Tint", "vf": ["eq=gamma_r=1.5:gamma_g=0.8:gamma_b=0.8"], "af": []},
                {"name": "Deep Red & Saturated", "vf": ["eq=contrast=1.2:saturation=1.5:gamma_r=1.3"], "af": []},
                {"name": "Extreme Red", "vf": ["eq=gamma_r=1.8:gamma_g=0.5:gamma_b=0.5"], "af": []},
                {"name": "None (No Effect)"}
            ],
            "disgust": [
                {"name": "Green Tint", "vf": ["eq=gamma_g=1.5:gamma_r=0.8:gamma_b=0.8"], "af": []},
                {"name": "Sickly Yellow", "vf": ["hue=h=90:s=1.2"], "af": []},
                {"name": "None (No Effect)"}
            ],
            "confused": [
                {"name": "Orange Tint", "vf": ["hue=h=45:s=0.5"], "af": []},
                {"name": "Desaturated Dark", "vf": ["eq=saturation=0.5:brightness=-0.1"], "af": []},
                {"name": "None (No Effect)"}
            ],
            "happy": [
                {"name": "Bright & Saturated", "vf": ["eq=saturation=1.5:brightness=0.05"], "af": []},
                {"name": "High Contrast Vivid", "vf": ["eq=contrast=1.2:saturation=1.3"], "af": []},
                {"name": "None (No Effect)"}
            ],
            "amused": [
                {"name": "Punchy Contrast", "vf": ["eq=contrast=1.3"], "af": []},
                {"name": "Brightened", "vf": ["eq=brightness=0.1:saturation=1.2"], "af": []},
                {"name": "None (No Effect)"}
            ],
            "transition": [
                {"name": "Basic Transition", "vf": [], "af": []},
                {"name": "None (No Effect)"}
            ]
        }

    def save(self):
        with open(self.vfx_file, 'w', encoding='utf-8') as f:
            json.dump(self.vfx_map, f, indent=4)

    def get_random_effect(self, emotion: str) -> dict:
        if emotion in self.vfx_map and len(self.vfx_map[emotion]) > 0:
            return random.choice(self.vfx_map[emotion])
        return {"vf": [], "af": []}

vfx_manager = VFXManager()
