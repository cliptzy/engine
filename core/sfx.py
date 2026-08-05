import json
import os
from core.utils import get_app_root

class SFXManager:
    def __init__(self):
        self.sfx_file = os.path.join(get_app_root(), "sfx.json")
        self.sfx_map = {}
        self.load()

    def load(self):
        if os.path.exists(self.sfx_file):
            try:
                with open(self.sfx_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sfx_map = {}
                    for k, v in data.items():
                        if isinstance(v, list):
                            self.sfx_map[k] = {"desc": "", "files": v}
                        else:
                            self.sfx_map[k] = v
            except Exception:
                self._load_default()
        else:
            self._load_default()
            self.save()

    def _load_default(self):
        self.sfx_map = {
            "sad": {"desc": "Sedih, menangis, kecewa, atau suasana murung.", "files": ["fail.mp3"]},
            "bored": {"desc": "Bosan, lelah, capek, pasrah, atau kalimat garing/monoton.", "files": ["bruh.mp3", "fail.mp3"]},
            "shock": {"desc": "Kaget, terkejut keras, teriakan tiba-tiba, atau momen plot twist.", "files": ["vine-boom.mp3", "amongus.mp3", "anime-wow.mp3"]},
            "fear": {"desc": "Takut, panik, ngeri, seram, atau kekhawatiran yang mendesak.", "files": ["amongus.mp3", "vine-boom.mp3", "error.mp3"]},
            "angry": {"desc": "Marah, kesal, frustrasi, emosi, atau mengeluh dengan keras/kasar.", "files": ["vine-boom.mp3"]},
            "disgust": {"desc": "Jijik, ilfeel, menolak sesuatu yang kotor/aneh (\"ew\", \"najis\", \"bau\").", "files": ["bruh.mp3", "error.mp3"]},
            "confused": {"desc": "Bingung, heran, merasa ada yang janggal, atau tidak paham.", "files": ["bruh.mp3", "faaah.mp3", "error.mp3", "slip.mp3"]},
            "happy": {"desc": "Senang, antusias (excited), memuji (\"keren\", \"mantap\"), atau merayakan sesuatu.", "files": ["anime-wow.mp3", "ding.mp3", "rizz.mp3"]},
            "amused": {"desc": "Lucu, terhibur, tertawa (\"haha\", \"wkwk\", \"bjir\"), atau sarkasme komedi ringan.", "files": ["pop.mp3", "slip.mp3", "rizz.mp3"]}
        }

    def save(self):
        with open(self.sfx_file, 'w', encoding='utf-8') as f:
            json.dump(self.sfx_map, f, indent=4)

sfx_manager = SFXManager()
