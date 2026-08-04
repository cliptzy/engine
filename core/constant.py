SFX_MAP = {
    # Emosi Negatif / Low Energy
    "sad": ["sad-violin.mp3", "fail.mp3"],
    "bored": ["bruh.mp3", "fail.mp3"],
    
    # Emosi Kaget / Intensitas Tinggi
    "shock": ["vine-boom.mp3", "metal-pipe-clang.mp3", "amongus.mp3", "anime-wow.mp3"],
    "fear": ["amongus.mp3", "vine-boom.mp3", "error.mp3"],
    
    # Emosi Frustrasi / Penolakan
    "angry": ["halah-nyocot.mp3", "metal-pipe-clang.mp3", "vine-boom.mp3"],
    "disgust": ["halah-nyocot.mp3", "bruh.mp3", "error.mp3"],
    
    # Emosi Kebingungan / Aneh
    "confused": ["bruh.mp3", "faaah.mp3", "error.mp3", "slip.mp3"],
    
    # Emosi Positif / High Energy
    "happy": ["anime-wow.mp3", "cihuy.mp3", "ding.mp3", "rizz.mp3"],
    "amused": ["hee-hee.mp3", "pop.mp3", "slip.mp3", "rizz.mp3"]
}

SYNTH_SFX_MAP = {
    "happy": "sine=f=1200:d=0.2,afade=t=out:st=0:d=0.2,volume=1.5,aformat=channel_layouts=stereo",
    
    "shock": "anoisesrc=d=0.6:c=pink,afade=t=out:st=0:d=0.6,volume=4,aformat=channel_layouts=stereo",
    
    "fear": "sine=f=150:d=1.5,tremolo=f=8:d=0.8,afade=t=out:st=0.5:d=1,volume=2,aformat=channel_layouts=stereo",
    
    "angry": "anoisesrc=d=0.4:c=pink,lowpass=f=3000,tremolo=f=60:d=1,afade=t=out:st=0:d=0.4,volume=2,aformat=channel_layouts=stereo",
    
    "sad": "sine=f=250:d=1,afade=t=out:st=0.5:d=0.5,volume=1.5,aformat=channel_layouts=stereo",
    
    "bored": "sine=f=200:d=0.5,tremolo=f=2:d=1,afade=t=out:st=0:d=0.5,volume=1.5,aformat=channel_layouts=stereo"
}