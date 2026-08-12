import os
from typing import Any, Dict, List

import librosa
import torch

from core.logger import log

_audio_event_model = None
_audio_event_extractor = None


def get_audio_event_pipeline() -> Any:
    global _audio_event_model, _audio_event_extractor
    if _audio_event_model is None:
        try:
            from transformers import ASTFeatureExtractor, ASTForAudioClassification

            model_id = "MIT/ast-finetuned-audioset-10-10-0.4593"
            log.info(f"Memuat model deteksi Audio Event ({model_id})...")
            device = "cuda" if torch.cuda.is_available() else "cpu"

            _audio_event_extractor = ASTFeatureExtractor.from_pretrained(model_id)
            _audio_event_model = ASTForAudioClassification.from_pretrained(model_id)
            _audio_event_model.to(device)  # type: ignore
            _audio_event_model.eval()
        except Exception as e:
            log.error(f"Gagal memuat model Audio Event: {e}")
            _audio_event_model = False  # tandai gagal agar tidak retrying
    return _audio_event_extractor, _audio_event_model


def analyze_audio_emotions(
    audio_path: str, chunk_duration: float = 2.0, overlap: float = 1.0
) -> List[Dict[str, Any]]:
    """
    Menganalisis file audio untuk mencari momen teriakan/kaget/tertawa (Scream, Yell, Laughter, dll).
    Mengembalikan timeline JSON array berisi kejadian-kejadian tersebut.
    """
    extractor, model = get_audio_event_pipeline()
    if not model:
        log.warning("Model Audio Event tidak tersedia. Lewati analisis audio event.")
        return []

    if not os.path.exists(audio_path):
        log.warning(f"File audio tidak ditemukan untuk dianalisis: {audio_path}")
        return []

    log.info(f"Menganalisis audio event pada: {audio_path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    sr = 16000
    try:
        waveform, _ = librosa.load(audio_path, sr=sr)
    except Exception as e:
        log.error(f"Gagal memuat audio menggunakan librosa: {e}")
        return []

    chunk_samples = int(chunk_duration * sr)
    step_samples = int((chunk_duration - overlap) * sr)
    id2label = model.config.id2label
    threshold = 0.02

    # Target kategori yang penting untuk jumpscare/lucu
    target_labels = [
        "yell",
        "shout",
        "scream",
        "screaming",
        "groan",
        "grunt",
        "laugh",
        "laughter",
        "gasp",
        "whimper",
        "wail",
    ]

    audio_timeline = []

    for start_sample in range(0, len(waveform), step_samples):
        end_sample = start_sample + chunk_samples
        chunk_waveform = waveform[start_sample:end_sample]

        start_time = start_sample / sr

        if len(chunk_waveform) < sr * 0.5:
            break

        inputs = extractor(
            chunk_waveform, sampling_rate=sr, padding="max_length", return_tensors="pt"
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)

        probabilities = torch.sigmoid(outputs.logits)[0]

        detected_events = []
        for i, prob in enumerate(probabilities):
            if prob.item() > threshold:
                label = id2label[i].lower()
                for target in target_labels:
                    if target in label:
                        detected_events.append((label, prob.item()))
                        break  # cukup 1 pencocokan per label

        if detected_events:
            # Urutkan dari probability terbesar
            detected_events.sort(key=lambda x: x[1], reverse=True)
            best_event, score = detected_events[0]

            audio_timeline.append(
                {
                    "time": round(start_time, 2),
                    "event": best_event,
                    "score": round(score, 3),
                }
            )

    # Lakukan filtering cooldown 2 detik agar tidak spam
    filtered_timeline = []
    last_time = -999.0
    for item in audio_timeline:
        if item["time"] - last_time >= 2.0:
            filtered_timeline.append(item)
            last_time = item["time"]

    if filtered_timeline:
        log.info(f"Berhasil mendeteksi {len(filtered_timeline)} momen audio penting.")
    else:
        log.info("Tidak ada momen audio (scream/laugh) dominan terdeteksi.")

    return filtered_timeline
