import json
import re
from typing import Any, Dict, List, Optional

from core.ai.factory import AIProviderFactory
from core.logger import log

DEFAULT_PROMPT_TEMPLATE = """
Anda adalah seorang Produser Konten Viral dan Editor Video Profesional ahli pencari momen (highlight detector).
Tugas Anda adalah menganalisis transkrip video berikut dan menemukan momen-momen "Emas" yang memiliki potensi viral tinggi untuk dijadikan video pendek vertikal (YouTube Shorts, TikTok, Reels).

Konteks Input:
Transkrip di bawah ini dilengkapi dengan stempel waktu (timestamp) dalam hitungan detik dengan format [start_s - end_s]: teks percakapan.

Kriteria Pemilihan Momen (Wajib Dipenuhi):
1. Mengandung Emosi/Intrik: Cari momen paling lucu, heboh, emosional, klimaks cerita, perdebatan panas, atau reaksi ekstrem (misal: gamer berteriak saat clutch/epic moment).
2. Memiliki Hook & Payoff: Klip harus diawali dengan pernyataan/kejadian menarik (hook) dan diakhiri dengan konklusi/punchline yang jelas (payoff).
3. Kelengkapan Konteks: Jangan pernah memotong percakapan di tengah kalimat atau menyisakan informasi yang menggantung.
4. Durasi Klip: Total durasi setiap klip HARUS di antara 15 hingga 60 detik.
5. Tidak boleh opening dan closing video (menit awal dan akhir video)
6. Jarak antar momen harus cukup jauh (minimal 5 menit)

Aturan Output:
Karena output Anda akan dibaca oleh sistem, Anda HANYA boleh merespons dengan JSON Object yang valid di dalam blok kode Markdown (```json ... ```). Jangan menambahkan teks pengantar atau penutup di luar blok JSON tersebut.
Gunakan bahasa sesuai dengan output yang diminta

Struktur JSON yang wajib digunakan:
```json
{
  "segments": [
    {
      "start": 12.5,
      "end": 45.0,
      "duration": 32.5,
      "title": "Judul clickbait dan menarik untuk klip ini (Maks 6 kata)",
      "reason": "Alasan detail mengapa momen ini menarik, emosi yang ditonjolkan, dan mengapa cocok untuk audiens TikTok/Shorts",
      "score": 0.95
    }
  ]
}
```

Output Bahasa: {language}
{custom_context}

Transkrip Video:
{transcript_text}
"""


class AIHighlightDetector:
    def detect_highlights(
        self,
        transcript_segments: List[Dict[str, Any]],
        ai_config: Dict[str, Any],
        event_hook: Optional[Any] = None,
        video_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Sends transcript to configured AI model provider and returns structured highlight segments.
        """
        if not transcript_segments:
            log.warning("Transkrip kosong, tidak dapat menjalankan deteksi AI.")
            return []

        # Formats timestamped transcript for LLM
        formatted_lines = []
        for seg in transcript_segments:
            start_s = seg.get("start", 0.0)
            end_s = seg.get("end", start_s + 2.0)
            text = seg.get("text", "").strip()
            if text:
                formatted_lines.append(f"[{start_s:.1f}s - {end_s:.1f}s]: {text}")

        # Memecah transkrip jika terlalu panjang (maksimal ~25000 karakter per bagian)
        chunks = []
        current_chunk = []
        current_len = 0
        for line in formatted_lines:
            line_len = len(line) + 1  # +1 untuk newline
            if current_len + line_len > 25000 and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        # Mengambil bahasa dari preview.json (default: Indonesia)
        language = "Indonesia"
        if video_id:
            from core.utils import get_preview_data

            preview_data = get_preview_data(video_id=video_id)
            if preview_data.get("language"):
                language = preview_data["language"]

        all_highlights = []
        provider_name = (
            ai_config.get("provider") or ai_config.get("ai_provider") or "ollama"
        ).lower()
        provider = AIProviderFactory.create(provider_name)

        custom_prompt = ai_config.get("custom_prompt", "")
        custom_context_str = (
            f"\nKonteks Tambahan Pengguna:\n{custom_prompt}\n" if custom_prompt else ""
        )

        for i, chunk_text in enumerate(chunks):
            template = DEFAULT_PROMPT_TEMPLATE
            prompt = template.replace("{transcript_text}", chunk_text)
            prompt = prompt.replace("{language}", language)
            prompt = prompt.replace("{custom_context}", custom_context_str)

            if len(chunks) > 1:
                log.info(
                    f"[AI] Mengirim transkrip (Bagian {i + 1}/{len(chunks)}) ke AI Provider: {provider_name.upper()}..."
                )
            else:
                log.info(
                    f"[AI] Mengirim transkrip ke AI Provider: {provider_name.upper()}..."
                )

            log.info(f"=== PROMPT KE AI ({provider_name.upper()}) ===\n{prompt}\n==========================================")
            try:
                raw_response = provider.generate(prompt, ai_config, event_hook)
                log.info(f"=== RESPONSE DARI AI ({provider_name.upper()}) ===\n{raw_response}\n============================================")
            except Exception as ex:
                log.error(f"=== ERROR DARI AI ({provider_name.upper()}) ===\n{ex}\n============================================")
                raise ex

            highlights = self._parse_json_highlights(raw_response)
            all_highlights.extend(highlights)

        # Mengurutkan semua highlight berdasarkan waktu mulai
        all_highlights.sort(key=lambda x: float(x.get("start", 0)))

        log.info(
            f"[AI] Berhasil mendeteksi total {len(all_highlights)} momen highlight dari AI!"
        )

        return all_highlights

    def _parse_json_highlights(self, raw_text: str) -> List[Dict[str, Any]]:
        """Extracts and parses JSON array/object from LLM response."""
        if not raw_text:
            return []

        # Find JSON array [...] or JSON object {...} in text
        match_arr = re.search(r"\[\s*\{.*\}\s*\]", raw_text, re.DOTALL)
        match_obj = re.search(r'\{\s*".*"\s*:.*\s*\}', raw_text, re.DOTALL)

        if match_arr:
            json_str = match_arr.group(0)
        elif match_obj:
            json_str = match_obj.group(0)
        else:
            json_str = raw_text.strip()

        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                # If LLM returned {"segments": [...]}, {"highlights": [...]}, or similar
                items = (
                    parsed.get("segments")
                    or parsed.get("highlights")
                    or parsed.get("clips")
                    or list(parsed.values())[0]
                )
            else:
                items = parsed

            if not isinstance(items, list):
                return []

            clean_highlights = []
            for item in items:
                try:
                    start = float(item.get("start", 0))
                    dur = float(item.get("duration", 20))
                    title = (
                        item.get("title") or item.get("reason") or "Momen Menarik AI"
                    )
                    reason = item.get("reason", "Dideteksi oleh AI model")
                    score = float(item.get("score", 0.9))
                    clean_highlights.append(
                        {
                            "start": start,
                            "duration": dur,
                            "title": title,
                            "reason": reason,
                            "score": score,
                        }
                    )
                except Exception:
                    continue

            clean_highlights.sort(key=lambda x: x["start"])
            return clean_highlights
        except Exception as e:
            log.warning(
                f"Gagal meng-parse JSON dari respon AI: {e}. Raw text: {raw_text[:200]}"
            )
            return []

    def generate_metadata(
        self,
        clip_text: str,
        youtube_title: str,
        channel_name: str,
        youtube_url: str,
        ai_config: Dict[str, Any],
        user_context: str = "",
        event_hook: Optional[Any] = None,
        language: str = "Indonesia",
        words_data: Optional[List[Dict[str, Any]]] = None,
        visual_emotions: Optional[List[Dict[str, Any]]] = None,
        audio_emotions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not clip_text or not clip_text.strip():
            log.warning("Teks subtitle klip kosong, tidak dapat men-generate metadata.")
            return {}

        clip_text = clip_text.strip()
        if len(clip_text) > 10000:
            clip_text = clip_text[:10000] + "..."

        context_str = (
            f"- Konteks Tambahan dari Pengguna: {user_context}\n"
            if user_context
            else ""
        )
        from core.constant import EMOTION_DESCRIPTIONS, VALID_EMOTIONS

        emotion_lines = []
        i = 1
        for emo in VALID_EMOTIONS:
            if emo == "neutral":
                continue
            desc = EMOTION_DESCRIPTIONS.get(emo, emo)
            emotion_lines.append(f'{i}. "{emo}" : {desc}')
            i += 1

        emotion_lines.append(
            f'{i}. "neutral" : Normal, datar, informatif biasa, atau tidak ada emosi yang menonjol.'
        )
        emotion_str = "\n".join(emotion_lines)

        visual_str = ""
        if visual_emotions:
            compact_vis = [f"{em['time']}s:{em['emotion']}" for em in visual_emotions]
            visual_str = "\nVisual Emotion Timeline:\n" + ", ".join(compact_vis) + "\n"

        audio_str = ""
        if audio_emotions:
            compact_aud = [f"{em['time']}s:{em['event']}" for em in audio_emotions]
            audio_str = "\nAudio Event Timeline:\n" + ", ".join(compact_aud) + "\n"

        try:
            from core.video_effects import video_effect_manager

            effect_lines = []
            for eff in video_effect_manager.all_effects:
                eff_name = eff.get("name", "unknown")
                eff_emotions = eff.get("emotions", [])
                effect_lines.append(
                    f'- "{eff_name}" (cocok untuk emosi: {", ".join(eff_emotions)})'
                )
            effects_str = "\n".join(effect_lines)
        except Exception:
            effects_str = "- (Data efek video tidak tersedia)"

        chunk_size = 150
        if not words_data:
            words_chunks = [None]
        else:
            words_chunks = [
                words_data[i : i + chunk_size]
                for i in range(0, len(words_data), chunk_size)
            ]

        provider_name = (
            ai_config.get("provider") or ai_config.get("ai_provider") or "ollama"
        ).lower()

        try:
            provider = AIProviderFactory.create(provider_name)
        except Exception as e:
            log.error(f"[ERROR] Gagal memuat AI Provider: {e}")
            return {}

        global_metadata = {}
        all_enriched = []
        all_standalone = []

        for idx, chunk in enumerate(words_chunks):
            chunk_info = (
                f"\n(PENTING: Ini adalah bagian {idx + 1} dari {len(words_chunks)} dari total kata yang ada. Fokus berikan `enriched_transcript` HANYA untuk kata-kata di bagian ini saja!)\n"
                if len(words_chunks) > 1
                else ""
            )

            prompt = f"""
Anda adalah Social Media Manager spesialis video vertikal viral.
Tugas: Buat Title, Tags, Highlight (teks pop-up lucu maks 4 kata), dan `enriched_transcript`.
Respons HARUS JSON Object valid dalam markdown (```json ... ```).

Bahasa: {language}
Konteks Video: {channel_name} - {youtube_title} ({youtube_url})
{context_str}{visual_str}{audio_str}{chunk_info}

ATURAN:
1. `highlight` sangat singkat (maks 3-4 kata).
2. Jika `words_data` ada, tulis ulang ke `enriched_transcript` dengan menambah field `emotion` dan `color` (Hex: #FFFF00 untuk netral, warna mencolok untuk emosi kuat).
3. Tambahkan field `score` ke `enriched_transcript` untuk setiap kata, dengan nilai antara 0.0 hingga 1.0.
4. SINTESIS EMOSI HOLISTIK (PENTING UNTUK STREAMER/GAMER):
   Anda memiliki 3 sumber prediksi AI mentah: Wajah (Visual Emotion), Suara (voice_emotion/audio_event), dan Teks (text_emotion).
   - STREAMER ROLEPLAY AWARENESS: Streamer sering mengucapkan kata ekstrem ("mati kau", "I'm dead") sambil bercanda. JANGAN PERCAYA TEKS 100%!
   - Jika teks bermakna kuat (angry/fear/shock) NAMUN Wajah (Visual) atau Suara menunjukkan 'neutral' / 'happy', maka itu hanya roleplay/kasual. Anda WAJIB menjadikannya 'neutral' atau 'happy'.
   - Emosi kuat (angry/fear/shock) HANYA BOLEH DIPILIH jika benar-benar didukung oleh bukti Wajah (panik/marah) ATAU Suara (teriakan/ledakan/gebrak meja).
   - Tujuan Anda: Mencegah spam deteksi emosi pada obrolan kasual.
5. PILIHAN EFEK VIDEO (VIDEO EFFECT OVERRIDE):
   Selain emosi, pilih spesifik nama efek video yang paling menggambarkan momen/kata tersebut dari daftar di bawah.
   Tulis nama efek tersebut ke dalam field `video_effect_override`.
   - Jika momen adalah obrolan biasa atau tidak butuh penekanan, Anda WAJIB mengisi dengan "none".
   - Jika momen adalah klimaks tapi Anda bingung pilih efek, isi "random".
   - JANGAN LAKUKAN SPAM! Gunakan efek video (khususnya meme) hanya pada momen yang benar-benar lucu atau mengagetkan.
6. Momen Tanpa Bicara (NON-VERBAL EVENTS):
   Jika ada momen jeritan (Scream) atau kejadian audio penting lainnya namun tidak ada kata yang terucap di `words_data` pada detik tersebut, Anda BISA meletakkan efek video ke dalam array `"standalone_video_effects"`.
   Isikan `"time"` (detik mulainya) dan `"video_effect_override"` dengan nama efek yang sesuai.

KATEGORI EMOSI VALID:
{emotion_str}

DAFTAR EFEK VIDEO TERSEDIA:
{effects_str}

Teks Subtitle Keseluruhan (sebagai konteks):
{clip_text}

Input words_data (BAGIAN {idx + 1}/{len(words_chunks)}):
{json.dumps(chunk) if chunk else "Tidak ada."}

Format Output JSON:
```json
{{
    "title": "...",
    "tags": "#...",
    "highlight": "...",
    "enriched_transcript": [
        {{"word": "kata", "start": 0.0, "end": 0.5, "emotion": "surprise", "color": "#FF0000", "voice_emotion": "angry", "score": 0.8, "video_effect_override": "vineboom"}}
    ],
    "standalone_video_effects": [
        {{"time": 48.5, "video_effect_override": "tyler1_scream"}}
    ]
}}
```
"""
            log.info(
                f"[AI] Mengirim permintaan metadata (Chunk {idx + 1}/{len(words_chunks)}) ke AI Provider: {provider_name.upper()}..."
            )
            if event_hook:
                event_hook(
                    "ai_status",
                    f"Men-generate metadata (Bagian {idx + 1}/{len(words_chunks)})...",
                )

            try:
                log.info(f"=== PROMPT KE AI ({provider_name.upper()}) ===\n{prompt}\n==========================================")
                raw_response = provider.generate(prompt, ai_config, event_hook)
                log.info(f"=== RESPONSE DARI AI ({provider_name.upper()}) ===\n{raw_response}\n============================================")
                match_obj = re.search(r'\{\s*".*"\s*:.*\s*\}', raw_response, re.DOTALL)
                if match_obj:
                    metadata = json.loads(match_obj.group(0))
                else:
                    metadata = json.loads(raw_response.strip())

                if idx == 0:
                    global_metadata["title"] = metadata.get("title", "")
                    global_metadata["tags"] = metadata.get("tags", "")
                    global_metadata["highlight"] = metadata.get("highlight", "")

                all_enriched.extend(metadata.get("enriched_transcript", []))
                all_standalone.extend(metadata.get("standalone_video_effects", []))
            except Exception as e:
                log.error(f"[ERROR] Gagal memproses metadata chunk {idx + 1}: {e}")
                continue

        # Kembalikan seluruh emosi mentah tanpa penghapusan cooldown
        global_metadata["enriched_transcript"] = all_enriched
        global_metadata["standalone_video_effects"] = all_standalone
        return global_metadata


ai_detector = AIHighlightDetector()
