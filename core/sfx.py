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
            "sad": {"desc": "Sedih, menangis, kecewa, kasihan, atau suasana murung.", "files": ["sad-awwww.mp3", "fail.mp3", "bo-womp.mp3"]},
            "bored": {"desc": "Bosan, lelah, capek, pasrah, hening canggung (awkward silence), atau kalimat garing/monoton.", "files": ["bruh.mp3", "cricket.mp3", "fail.mp3"]},
            "shock": {"desc": "Kaget, terkejut keras, teriakan tiba-tiba, momen plot twist, atau hal tak terduga.", "files": ["vine-boom.mp3", "shocking.mp3", "shock-2.mp3", "gah-dayum.mp3", "undertakers-bell.mp3", "camera-flash.mp3"]},
            "fear": {"desc": "Takut, panik, ngeri, seram, suspense, atau kekhawatiran yang mendesak.", "files": ["amongus.mp3", "bone-crack.mp3", "error.mp3", "minecraft-whistle.mp3"]},
            "angry": {"desc": "Marah, kesal, frustrasi, emosi, ancaman, atau mengeluh dengan keras/kasar.", "files": ["angry-zombie.mp3", "vine-boom.mp3", "core-sound.mp3"]},
            "disgust": {"desc": "Jijik, ilfeel, menolak sesuatu yang kotor/aneh (\"ew\", \"najis\", \"bau\").", "files": ["dry-fart.mp3", "bruh.mp3", "error.mp3"]},
            "confused": {"desc": "Bingung, heran, merasa ada yang janggal, tidak paham, atau momen konyol bodoh.", "files": ["faaah.mp3", "quack.mp3", "duck-toy.mp3", "slip.mp3", "bruh.mp3"]},
            "happy": {"desc": "Senang, antusias (excited), memuji (\"keren\", \"mantap\"), menang, berhasil, atau hadiah.", "files": ["anime-wow.mp3", "rizz.mp3", "ding.mp3", "money.mp3", "meccha-whistle.mp3"]},
            "amused": {"desc": "Lucu, terhibur, tertawa (\"haha\", \"wkwk\", \"bjir\"), komedi troll, atau sarkasme ringan.", "files": ["funny.mp3", "hihihiha-royale.mp3", "pop.mp3", "slip.mp3"]},
            "transition": {"desc": "Perpindahan topik, momen cepat, aksi kilat, klik, atau pergerakan objek (opsional).", "files": ["whoosh.mp3", "whip.mp3", "notification-sound.mp3", "switch-sound.mp3"]}
        }

    def save(self):
        with open(self.sfx_file, 'w', encoding='utf-8') as f:
            json.dump(self.sfx_map, f, indent=4)

sfx_manager = SFXManager()
