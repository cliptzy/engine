import os
import pathlib
import shutil

# Bypassing Windows symlink errors (penting untuk HuggingFace model cache di Windows)
pathlib.Path.symlink_to = lambda self, target, *args, **kwargs: shutil.copy(
    str(target), str(self)
)  # type: ignore
from typing import Any, Dict, List

import numpy as np

from core.logger import log


def analyze_voice_emotions(
    audio_path: str, words_data: List[Dict[str, Any]], language: str
) -> None:
    """
    Menganalisis emosi dari potongan audio per kata (berdasarkan words_data)
    menggunakan Deep Learning Transformer (Wav2Vec2) dan ekstraksi fitur (Librosa).

    Data emosi akan langsung disematkan kembali ke dalam `words_data` di dalam
    key `voice_emotion` (misal: 'happy/excited', 'angry', 'neutral', dll) beserta fitur akustiknya.
    """
    from core.config import config

    if not config.ai.use_voice_analysis:
        for w in words_data:
            w["voice_emotion"] = "neutral"
        return

    try:
        import librosa
        from transformers import pipeline
    except Exception as e:
        # Fallback: jika modul tidak terinstall, pastikan 'voice_emotion' tetap diisi 'neutral'
        for w in words_data:
            w["voice_emotion"] = "neutral"
        log.warning(
            f"Modul transformers atau librosa belum terinstall. Lewati analisis emosi suara. Error: {e}"
        )
        return

    if not os.path.exists(audio_path):
        log.error(f"File audio tidak ditemukan untuk analisis emosi: {audio_path}")
        return

    if not words_data:
        return

    log.info(
        f"Memulai analisis emosi suara (Deep Learning SER) pada {len(words_data)} kata..."
    )

    try:
        # -----------------------------------------------------------------
        # PENENTUAN MODEL BERDASARKAN BAHASA SECARA DINAMIS
        # -----------------------------------------------------------------
        if language.strip().lower() == "id":
            model_name = (
                "alianurrahman/wav2vec2-base-indonesian-speech-emotion-recognition"
            )
            log.info("Bahasa [ID] terdeteksi. Memuat model spesifik Indonesia...")
        else:
            model_name = "superb/wav2vec2-base-superb-er"
            log.info(f"Bahasa [{language}] terdeteksi. Memuat model SUPERB...")

        classifier = pipeline("audio-classification", model=model_name)

        target_sr = 16000
        log.info("Memuat sinyal audio untuk analisis SER...")
        y, sr = librosa.load(audio_path, sr=target_sr)

        # Kalkulasi Global RMS untuk mengukur seberapa keras audio ini secara keseluruhan
        # Berguna untuk mengoreksi AI saat menebak 'angry' pada kata yang sebenarnya diucapkan pelan
        global_rms = float(np.sqrt(np.mean(y**2)))

        log.info("Mengekstrak fitur dan memprediksi emosi per kata...")
        for i, w in enumerate(words_data):
            start_time = w.get("start", 0.0)
            end_time = w.get("end", 0.0)

            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)

            # Buffer konteks 0.5s (Jalan tengah: 1.5s membuat seluruh kalimat jadi 'angry' jika ada 1 teriakan)
            context_buffer = int(0.5 * sr)
            slice_start = max(0, start_sample - context_buffer)
            slice_end = min(len(y), end_sample + context_buffer)

            y_segment = y[slice_start:slice_end]

            emotion = "neutral"
            if len(y_segment) > 1000:
                # 1. Klasifikasi dengan Transformer (Wav2Vec2)
                preds = classifier({"array": y_segment, "sampling_rate": sr})
                if preds:
                    best_pred = max(preds, key=lambda x: x["score"])
                    raw_label = best_pred["label"].lower().strip()

                    # ---------------------------------------------------------
                    # PEMETAAN LABEL GABUNGAN (SUPERB & ALIANURRAHMAN)
                    # ---------------------------------------------------------
                    label_map = {
                        # Format SUPERB
                        "neu": "neutral",
                        "hap": "happy/excited",
                        "ang": "angry",
                        "sad": "sad",
                        # Format Alianurrahman
                        "neutral": "neutral",
                        "happy": "happy/excited",
                        "angry": "angry",
                        "fear": "fear",  # Dipertahankan jika Anda ingin mengolah fear ke depan
                        "disgust": "disgust",  # Dipertahankan jika Anda ingin mengolah disgust ke depan
                    }
                    emotion = label_map.get(raw_label, raw_label)

                # Skip
                # # 2. Ekstraksi Fitur Tradisional untuk Analytics
                # # MFCC
                # mfcc = librosa.feature.mfcc(y=y_segment, sr=sr, n_mfcc=13)
                # mfcc_mean = np.mean(mfcc, axis=1).tolist() if mfcc.size > 0 else [0]*13
                # # ZCR (Tingkat kebisingan/desis)
                # zcr = librosa.feature.zero_crossing_rate(y_segment)
                # zcr_mean = float(np.mean(zcr)) if zcr.size > 0 else 0.0
                # # RMS (Volume Segmen)
                # rms = librosa.feature.rms(y=y_segment)
                # rms_mean = float(np.mean(rms)) if rms.size > 0 else 0.0

                # # Pitch (F0)
                # try:
                #     f0 = librosa.yin(y_segment, fmin=50, fmax=300)
                #     valid_f0 = f0[f0 > 0]
                #     pitch_mean = float(np.mean(valid_f0)) if valid_f0.size > 0 else 0.0
                # except:
                #     pitch_mean = 0.0

                # words_data[i]['features'] = {
                #     "rms_energy": round(rms_mean, 4),
                #     "zero_crossing_rate": round(zcr_mean, 4),
                #     "pitch_f0": round(pitch_mean, 2),
                #     "mfcc_vector": [round(m, 2) for m in mfcc_mean],
                #     "relative_energy": round(rel_energy, 4)
                # }

                log.info(f"Word: {words_data[i]['word']}, Emotion: {emotion}")

            # Sematkan emosi yang didapat
            words_data[i]["voice_emotion"] = emotion

        log.info("Analisis emosi suara Deep Learning selesai secara menyeluruh.")

    except Exception as ex:
        log.error(
            f"Gagal melakukan analisis emosi suara dengan model Deep Learning: {ex}"
        )
