import argparse
import json
import os


def test_text_emotion(text: str):
    try:
        import torch
        from transformers import pipeline
    except ImportError:
        print(
            json.dumps(
                {"error": "Modul 'transformers' atau 'torch' belum terinstall."},
                indent=2,
            )
        )
        return

    device = 0 if torch.cuda.is_available() else -1

    # Mengurangi log bawaan tensorflow/pytorch jika ada
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"

    repo_id = "StevenLimcorn/indonesian-roberta-base-emotion-classifier"
    print(f"Memuat model emosi teks standar Hugging Face ({repo_id})...")

    try:
        # Gunakan pipeline text-classification standar
        classifier = pipeline("text-classification", model=repo_id, device=device)
    except Exception as e:
        print(json.dumps({"error": f"Gagal memuat model: {e}"}, indent=2))
        return

    print(f'\n[Input Teks] -> "{text}"\n')
    try:
        # Menghasilkan list of dict yang berisi label dan score
        # top_k=None akan mengembalikan seluruh nilai probabilitas dari tiap kelas
        results = classifier(text, top_k=None)

        # Pipeline pada single input biasanya mengembalikan array 2 dimensi (list of list)
        if isinstance(results, list) and len(results) > 0:
            if isinstance(results[0], list):
                scores = results[0]
            else:
                scores = results
        else:
            scores = []

        print("[Hasil Analisis]")
        print(json.dumps(scores, indent=2))

        if scores:
            top_result = scores[0]
            print(
                f"\nEmosi Dominan: {top_result['label']} (Akurasi: {top_result['score'] * 100:.2f}%)"
            )

    except Exception as e:
        print(json.dumps({"error": f"Gagal menganalisis teks: {e}"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Proof of Concept for Text Emotion Detection menggunakan StevenLimcorn/indonesian-roberta-base-emotion-classifier"
    )
    parser.add_argument(
        "text", type=str, help="Teks bahasa Indonesia yang akan dianalisis emosinya"
    )
    args = parser.parse_args()

    test_text_emotion(args.text)
