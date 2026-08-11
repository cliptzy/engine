import argparse
import json
import os
import sys

import numpy as np


def main():
    parser = argparse.ArgumentParser(
        description="PoC Speech Emotion Recognition (SER) Deep Learning Analyzer"
    )
    parser.add_argument(
        "--audio",
        type=str,
        default="scripts/audio.wav",
        help="Path ke file audio (.wav)",
    )
    args = parser.parse_args()

    audio_path = args.audio
    if not os.path.exists(audio_path):
        print(f"Error: File audio {audio_path} tidak ditemukan.")
        sys.exit(1)

    print(f"Memproses file audio: {audio_path}")

    try:
        import librosa
        from faster_whisper import WhisperModel
        from transformers import pipeline
    except ImportError as e:
        print(f"Error import module: {e}")
        print(
            "Pastikan librosa, faster-whisper, transformers, dan torch sudah terinstall."
        )
        print(
            'Gunakan command: python scripts/manage_reqs.py add "librosa" "transformers" "torch"'
        )
        sys.exit(1)

    # 1. Transkripsi dengan Faster-Whisper dan Caching
    cache_path = audio_path + ".transcription.json"
    df_data = []

    if os.path.exists(cache_path):
        print(f"Menggunakan hasil transkripsi dari cache: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            df_data = json.load(f)
    else:
        print("Melakukan transkripsi dengan faster-whisper...")
        try:
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(audio_path, word_timestamps=True)

            for segment in segments:
                for word in segment.words:
                    df_data.append(
                        {
                            "file_path": audio_path,
                            "start": word.start,
                            "end": word.end,
                            "word": word.word.strip(),
                        }
                    )
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(df_data, f, indent=4)
        except Exception as e:
            print(f"Error saat transkripsi: {e}")
            sys.exit(1)

    if not df_data:
        print("Tidak ada kata yang ditranskripsi.")
        sys.exit(1)

    # 2. Muat Model Deep Learning (Wav2Vec2 dari HuggingFace Transformers)
    print("Memuat State-of-the-Art Pre-trained Transformer Model (Wav2Vec2 SER)...")
    try:
        # Model ini dibangun dengan PyTorch dan di-finetune untuk klasifikasi emosi (Point 2.D)
        classifier = pipeline(
            "audio-classification", model="superb/wav2vec2-base-superb-er"
        )
    except Exception as e:
        print(f"Error memuat model Transformers: {e}")
        sys.exit(1)

    results = []
    print(
        "Mengekstrak Fitur Akustik (MFCC, ZCR, RMS, Pitch) & Inferensi Emosi per kata..."
    )

    try:
        target_sr = 16000
        y, sr = librosa.load(audio_path, sr=target_sr)

        for row in df_data:
            start_time = row["start"]
            end_time = row["end"]
            word = row["word"]

            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)

            # Buffer konteks untuk model Deep Learning
            context_buffer = int(0.2 * sr)
            slice_start = max(0, start_sample - context_buffer)
            slice_end = min(len(y), end_sample + context_buffer)
            y_segment = y[slice_start:slice_end]

            # ---------------------------------------------------------------------
            # BAGIAN 1: EKSTRAKSI VARIABEL / FITUR (Sesuai Konsep SER Tradisional)
            # ---------------------------------------------------------------------

            # 1. MFCC (Mel-Frequency Cepstral Coefficients)
            # Merepresentasikan spektrum frekuensi (skala Mel) layaknya telinga manusia
            mfcc = librosa.feature.mfcc(y=y_segment, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfcc, axis=1).tolist() if mfcc.size > 0 else [0] * 13

            # 2. Zero Crossing Rate (ZCR)
            # Mengukur keagresifan suara/frikatif (suara desis atau noise)
            zcr = librosa.feature.zero_crossing_rate(y_segment)
            zcr_mean = float(np.mean(zcr)) if zcr.size > 0 else 0.0

            # 3. Energy / Root Mean Square (RMS)
            # Intensitas kelantangan suara
            rms = librosa.feature.rms(y=y_segment)
            rms_mean = float(np.mean(rms)) if rms.size > 0 else 0.0

            # 4. Pitch (Fundamental Frequency / F0) menggunakan librosa.yin
            # Frekuensi dasar; orang marah/panik cenderung punya Pitch lebih tinggi
            try:
                f0 = librosa.yin(y_segment, fmin=50, fmax=300)
                valid_f0 = f0[f0 > 0]
                pitch_mean = float(np.mean(valid_f0)) if valid_f0.size > 0 else 0.0
            except:
                pitch_mean = 0.0

            # ---------------------------------------------------------------------
            # BAGIAN 2: KLASIFIKASI DENGAN TRANSFORMER (Wav2Vec2 via PyTorch)
            # ---------------------------------------------------------------------
            emotion = "neutral"
            if len(y_segment) > 1000:
                preds = classifier({"array": y_segment, "sampling_rate": sr})
                if preds:
                    best_pred = max(preds, key=lambda x: x["score"])
                    label_map = {
                        "neu": "neutral",
                        "hap": "happy/excited",
                        "ang": "angry",
                        "sad": "sad",
                    }
                    emotion = label_map.get(best_pred["label"], best_pred["label"])

            results.append(
                {
                    "word": word,
                    "start": float(start_time),
                    "end": float(end_time),
                    "dl_emotion": emotion,
                    "features": {
                        "rms_energy": round(rms_mean, 4),
                        "zero_crossing_rate": round(zcr_mean, 4),
                        "pitch_f0": round(pitch_mean, 2),
                        "mfcc_vector": [round(m, 2) for m in mfcc_mean],
                    },
                }
            )

    except Exception as e:
        print(f"Error saat klasifikasi emosi: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    json_output = json.dumps(
        {"status": "success", "audio_file": audio_path, "segments": results}, indent=4
    )

    print("\n--- HASIL ANALISIS JSON ---")
    print(json_output)

    out_file = "poc_dl_ser_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(json_output)
    print(f"\nBerhasil disimpan ke {out_file}")


if __name__ == "__main__":
    main()
