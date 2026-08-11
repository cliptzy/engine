import os
import json
from typing import List, Dict, Any
from core.logger import log

_text_emotion_pipeline = None

def get_text_emotion_pipeline(language: str):
    global _text_emotion_pipeline
    if _text_emotion_pipeline is None:
        try:
            import torch
            from transformers import pipeline
            device = 0 if torch.cuda.is_available() else -1
            
            if language.strip().lower() in ['id', 'indonesia', 'indonesian']:
                repo_id = "StevenLimcorn/indonesian-roberta-base-emotion-classifier"
            else:
                repo_id = "bhadresh-savani/bert-base-uncased-emotion"
                
            log.info(f"Memuat model emosi teks Hugging Face ({repo_id})...")
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
            os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
            
            _text_emotion_pipeline = pipeline("text-classification", model=repo_id, device=device)
        except Exception as e:
            log.error(f"Gagal memuat model emosi teks: {e}")
            _text_emotion_pipeline = False
    return _text_emotion_pipeline

def map_text_emotion(label: str) -> str:
    label = label.lower()
    mapping = {
        'joy': 'happy',
        'happiness': 'happy',
        'anger': 'angry',
        'sadness': 'sad'
    }
    return mapping.get(label, label)

def analyze_text_emotions(segments: List[Any], words_data: List[Dict[str, Any]], language: str) -> None:
    # Set default
    for w in words_data:
        w['text_emotion'] = 'neutral'

    from core.config import config
    # Jika Anda ingin memberi opsi toggle di masa depan:
    # if not getattr(config.ai, "use_text_analysis", True):
    #     return

    classifier = get_text_emotion_pipeline(language)
    if not classifier:
        return

    log.info("Memulai analisis emosi teks per segmen kalimat...")
    
    wd_idx = 0
    for segment in segments:
        text = getattr(segment, 'text', '').strip()
        if not text:
            continue
            
        dominant_emotion = 'neutral'
        try:
            results = classifier(text, top_k=None)
            scores = results[0] if isinstance(results, list) and isinstance(results[0], list) else (results if isinstance(results, list) else [])
            if scores:
                top_result = scores[0]
                if top_result['score'] > 0.4:  # Threshold keyakinan model
                    dominant_emotion = map_text_emotion(top_result['label'])
        except Exception as e:
            log.warning(f"Error classifying text emotion for segment '{text}': {e}")

        # Terapkan emosi segmen ini ke setiap kata yang termasuk di dalamnya
        segment_words = getattr(segment, 'words', [])
        if segment_words:
            for w in segment_words:
                if getattr(w, 'word', '').strip():
                    if wd_idx < len(words_data):
                        words_data[wd_idx]['text_emotion'] = dominant_emotion
                        wd_idx += 1
                        
    log.info("Analisis emosi teks selesai.")
