import os

import librosa
import torch
from transformers import ASTFeatureExtractor, ASTForAudioClassification

# PoC: Deteksi Audio Event menggunakan MIT/ast-finetuned-audioset-10-10-0.4593 (Sliding Window & Timestamps)


def detect_audio_events_with_timestamps(
    audio_path: str, chunk_duration: float = 2.0, overlap: float = 1.0
):
    """
    Mendeteksi audio event dengan memotong audio menjadi beberapa segmen kecil (sliding window).

    Args:
        chunk_duration: Durasi per potongan audio dalam detik (diperkecil agar suara kejutan singkat/scream mendominasi).
        overlap: Durasi tumpang tindih antar potongan dalam detik.
    """
    print(f"Menganalisis file: {audio_path}")

    model_id = "MIT/ast-finetuned-audioset-10-10-0.4593"
    print(f"Loading {model_id}...")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    feature_extractor = ASTFeatureExtractor.from_pretrained(model_id)
    model = ASTForAudioClassification.from_pretrained(model_id)
    model.to(device)  # type: ignore

    # Load seluruh audio
    sr = 16000  # AST model dilatih dengan 16kHz
    print("Memuat audio...")
    waveform, _ = librosa.load(audio_path, sr=sr)

    total_duration = len(waveform) / sr
    print(f"Total durasi audio: {total_duration:.2f} detik")

    chunk_samples = int(chunk_duration * sr)
    step_samples = int((chunk_duration - overlap) * sr)

    id2label = model.config.id2label
    threshold = 0.02  # Threshold diturunkan lebih jauh (2%) untuk mendeteksi suara yang mungkin tertimpa BGM

    print(
        f"Menganalisis per segmen {chunk_duration} detik dengan overlap {overlap} detik...\n"
    )

    # Sliding window
    for start_sample in range(0, len(waveform), step_samples):
        end_sample = start_sample + chunk_samples
        chunk_waveform = waveform[start_sample:end_sample]

        # Hitung timestamp
        start_time = start_sample / sr
        end_time = (start_sample + len(chunk_waveform)) / sr

        # Lewati jika terlalu pendek (misal di ujung akhir audio)
        if len(chunk_waveform) < sr * 0.5:
            break

        # Proses chunk ke model
        inputs = feature_extractor(
            chunk_waveform, sampling_rate=sr, padding="max_length", return_tensors="pt"
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)

        logits = outputs.logits
        predicted_probabilities = torch.sigmoid(logits)[0]

        # Ekstrak event yang melebihi threshold
        chunk_results = []
        for i, prob in enumerate(predicted_probabilities):
            if prob.item() > threshold:
                chunk_results.append((id2label[i], prob.item()))  # type: ignore

        # Urutkan berdasarkan probabilitas tertinggi
        chunk_results.sort(key=lambda x: x[1], reverse=True)

        # Hanya cetak jika ada suara yang terdeteksi
        print(f"[{start_time:05.2f}s - {end_time:05.2f}s] : ", end="")

        if not chunk_results:
            print(" (Hanya hening atau suara tidak dikenal)")
        else:
            # Ambil Top 5 untuk menghindari spam di console
            top_5 = chunk_results[:5]
            desc = []
            for label, score in top_5:
                marker = (
                    "⭐"
                    if label.lower()
                    in [
                        "yell",
                        "shout",
                        "scream",
                        "groan",
                        "grunt",
                        "laugh",
                        "laughter",
                        "gasp",
                        "whimper",
                    ]
                    else ""
                )
                desc.append(f"{marker}{label} ({score * 100:.1f}%)")

            print(" | ".join(desc))

    print("\nAnalisis selesai.")


if __name__ == "__main__":
    # Ganti dengan path ke audio.wav kamu yang berisi gaming footage
    test_audio = "./scripts/audio.wav"

    if os.path.exists(test_audio):
        detect_audio_events_with_timestamps(test_audio, chunk_duration=2.0, overlap=1.0)
    else:
        # Fallback ke root jika tidak ketemu
        test_audio = "../audio.wav"
        if os.path.exists(test_audio):
            detect_audio_events_with_timestamps(
                test_audio, chunk_duration=2.0, overlap=1.0
            )
        else:
            print(f"Error: Tidak dapat menemukan file audio.")
            print(
                "Silakan siapkan file audio.wav di dalam folder scripts/ atau root proyek."
            )
