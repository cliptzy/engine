import os
import shutil
import pathlib
# Bypassing Windows symlink errors (penting untuk HuggingFace model cache di Windows)
pathlib.Path.symlink_to = lambda self, target, *args, **kwargs: shutil.copy(target, self) # type: ignore
import numpy as np
from typing import List, Dict, Any
from core.logger import log

def analyze_voice_emotions(audio_path: str, words_data: List[Dict[str, Any]]) -> None:
    """
    Menganalisis emosi dari potongan audio per kata (berdasarkan words_data)
    menggunakan Deep Learning Transformer (Wav2Vec2) dan ekstraksi fitur (Librosa).
    
    Data emosi akan langsung disematkan kembali ke dalam `words_data` di dalam
    key `voice_emotion` (misal: 'happy/excited', 'angry', 'neutral', dll) beserta fitur akustiknya.
    """
    try:
        import librosa
        from transformers import pipeline
    except ImportError:
        log.warning("Modul transformers atau librosa belum terinstall. Lewati analisis emosi suara.")
        return
        
    if not os.path.exists(audio_path):
        log.error(f"File audio tidak ditemukan untuk analisis emosi: {audio_path}")
        return

    if not words_data:
        return

    log.info(f"Memulai analisis emosi suara (Deep Learning SER) pada {len(words_data)} kata...")

    try:
        log.info("Memuat Pre-trained Transformer Model (Wav2Vec2)...")
        # pipeline akan mengunduh model ke cache HF pada run pertama kali
        classifier = pipeline("audio-classification", model="superb/wav2vec2-base-superb-er")
        
        target_sr = 16000
        log.info("Memuat sinyal audio untuk analisis SER...")
        y, sr = librosa.load(audio_path, sr=target_sr)
        
        # Kalkulasi Global RMS untuk mengukur seberapa keras audio ini secara keseluruhan
        # Berguna untuk mengoreksi AI saat menebak 'angry' pada kata yang sebenarnya diucapkan pelan
        global_rms = float(np.sqrt(np.mean(y**2)))
        
        log.info("Mengekstrak fitur dan memprediksi emosi per kata...")
        for i, w in enumerate(words_data):
            start_time = w.get('start', 0.0)
            end_time = w.get('end', 0.0)
            
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            
            # Buffer konteks 0.5s (Jalan tengah: 1.5s membuat seluruh kalimat jadi 'angry' jika ada 1 teriakan)
            context_buffer = int(0.5 * sr)
            slice_start = max(0, start_sample - context_buffer)
            slice_end = min(len(y), end_sample + context_buffer)
            
            y_segment = y[slice_start:slice_end]
            
            emotion = 'neutral'
            if len(y_segment) > 1000:
                # 1. Klasifikasi dengan Transformer (Wav2Vec2)
                preds = classifier({"array": y_segment, "sampling_rate": sr})
                if preds:
                    best_pred = max(preds, key=lambda x: x['score'])
                    label_map = {
                        'neu': 'neutral',
                        'hap': 'happy/excited',
                        'ang': 'angry',
                        'sad': 'sad'
                    }
                    emotion = label_map.get(best_pred['label'], best_pred['label'])
                    
                # 2. Ekstraksi Fitur Tradisional untuk Analytics
                # MFCC
                mfcc = librosa.feature.mfcc(y=y_segment, sr=sr, n_mfcc=13)
                mfcc_mean = np.mean(mfcc, axis=1).tolist() if mfcc.size > 0 else [0]*13
                # ZCR (Tingkat kebisingan/desis)
                zcr = librosa.feature.zero_crossing_rate(y_segment)
                zcr_mean = float(np.mean(zcr)) if zcr.size > 0 else 0.0
                # RMS (Volume Segmen)
                rms = librosa.feature.rms(y=y_segment)
                rms_mean = float(np.mean(rms)) if rms.size > 0 else 0.0
                
                # Pitch (F0)
                try:
                    f0 = librosa.yin(y_segment, fmin=50, fmax=300)
                    valid_f0 = f0[f0 > 0]
                    pitch_mean = float(np.mean(valid_f0)) if valid_f0.size > 0 else 0.0
                except:
                    pitch_mean = 0.0
                    
                # 3. KOREKSI HYBRID (Deep Learning + Akustik Heuristik)
                # Wav2Vec2 yang dilatih dengan bahasa Inggris sering mengira streamer Indonesia
                # yang bersemangat sebagai 'angry'. Kita koreksi menggunakan Relative Energy.
                rel_energy = rms_mean / (global_rms + 1e-6)
                
                if emotion == 'angry':
                    if rel_energy < 0.9:
                        # Model bilang marah, tapi suaranya pelan di bawah rata-rata. Koreksi jadi netral/sedih.
                        emotion = 'sad' if pitch_mean > 0 and pitch_mean < 120 else 'neutral'
                    elif rel_energy < 1.1 and pitch_mean > 160 and zcr_mean < 0.08:
                        # Model bilang marah, tapi nadanya sangat melengking bersih tanpa bising. Ini mungkin Happy.
                        emotion = 'happy/excited'
                elif emotion == 'happy/excited':
                    if rel_energy > 1.3 and zcr_mean > 0.12:
                        # Model bilang happy, tapi teriakannya sangat keras dan serak/bising (ZCR tinggi). Ini Marah.
                        emotion = 'angry'
                    elif rel_energy < 1.0 and pitch_mean < 140:
                        # Model bilang happy, tapi nadanya rendah dan pelan. Pasti salah tebak.
                        emotion = 'neutral'
                elif emotion == 'neutral' and rel_energy > 1.8:
                    # Model bilang netral, tapi suaranya melonjak ekstrim kerasnya.
                    emotion = 'happy/excited' if pitch_mean > 160 and zcr_mean < 0.1 else 'angry'
                    
                words_data[i]['features'] = {
                    "rms_energy": round(rms_mean, 4),
                    "zero_crossing_rate": round(zcr_mean, 4),
                    "pitch_f0": round(pitch_mean, 2),
                    "mfcc_vector": [round(m, 2) for m in mfcc_mean],
                    "relative_energy": round(rel_energy, 4)
                }
            
            # Sematkan emosi yang didapat
            words_data[i]['voice_emotion'] = emotion

        log.info("Analisis emosi suara Deep Learning selesai secara menyeluruh.")

    except Exception as ex:
        log.error(f"Gagal melakukan analisis emosi suara dengan model Deep Learning: {ex}")
