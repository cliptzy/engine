import json
import re
from typing import List, Dict, Any, Optional
from core.logger import log
from core.ai.factory import AIProviderFactory

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
5. Larangan: Tidak boleh opening dan closing video

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
        video_id: Optional[str] = None
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
        provider_name = (ai_config.get("provider") or ai_config.get("ai_provider") or "ollama").lower()
        provider = AIProviderFactory.create(provider_name)

        custom_prompt = ai_config.get("custom_prompt", "")
        custom_context_str = f"\nKonteks Tambahan Pengguna:\n{custom_prompt}\n" if custom_prompt else ""

        for i, chunk_text in enumerate(chunks):
            template = DEFAULT_PROMPT_TEMPLATE
            prompt = template.replace("{transcript_text}", chunk_text)
            prompt = prompt.replace("{language}", language)
            prompt = prompt.replace("{custom_context}", custom_context_str)
            
            if len(chunks) > 1:
                log.info( f"[AI] Mengirim transkrip (Bagian {i+1}/{len(chunks)}) ke AI Provider: {provider_name.upper()}...")
            else:
                log.info( f"[AI] Mengirim transkrip ke AI Provider: {provider_name.upper()}...")
            
            raw_response = provider.generate(prompt, ai_config, event_hook)
            highlights = self._parse_json_highlights(raw_response)
            all_highlights.extend(highlights)

        # Mengurutkan semua highlight berdasarkan waktu mulai
        all_highlights.sort(key=lambda x: float(x.get("start", 0)))

        log.info( f"[AI] Berhasil mendeteksi total {len(all_highlights)} momen highlight dari AI!")

        return all_highlights

    def _parse_json_highlights(self, raw_text: str) -> List[Dict[str, Any]]:
        """Extracts and parses JSON array/object from LLM response."""
        if not raw_text:
            return []

        # Find JSON array [...] or JSON object {...} in text
        match_arr = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
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
                items = parsed.get("segments") or parsed.get("highlights") or parsed.get("clips") or list(parsed.values())[0]
            else:
                items = parsed

            if not isinstance(items, list):
                return []
            
            clean_highlights = []
            for item in items:
                try:
                    start = float(item.get("start", 0))
                    dur = float(item.get("duration", 20))
                    title = item.get("title") or item.get("reason") or "Momen Menarik AI"
                    reason = item.get("reason", "Dideteksi oleh AI model")
                    score = float(item.get("score", 0.9))
                    clean_highlights.append({
                        "start": start,
                        "duration": dur,
                        "title": title,
                        "reason": reason,
                        "score": score
                    })
                except Exception:
                    continue

            clean_highlights.sort(key=lambda x: x["start"])
            return clean_highlights
        except Exception as e:
            log.warning(f"Gagal meng-parse JSON dari respon AI: {e}. Raw text: {raw_text[:200]}")
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
        words_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        if not clip_text or not clip_text.strip():
            log.warning("Teks subtitle klip kosong, tidak dapat men-generate metadata.")
            return {}

        clip_text = clip_text.strip()
        if len(clip_text) > 10000:
            clip_text = clip_text[:10000] + "..."

        context_str = f"- Konteks Tambahan dari Pengguna: {user_context}\n" if user_context else ""

        try:
            from core.sfx import sfx_manager
            emotions = sfx_manager.sfx_map
        except Exception:
            emotions = {}
            
        emotion_lines = []
        i = 1
        for emo, data in emotions.items():
            desc = data.get("desc", emo) if isinstance(data, dict) else emo
            emotion_lines.append(f"{i}. \"{emo}\" : {desc}")
            i += 1
            
        emotion_lines.append(f"{i}. \"neutral\" : Normal, datar, informatif biasa, atau tidak ada emosi yang menonjol.")
        emotion_str = "\n".join(emotion_lines)
        
        prompt = f"""
Anda adalah seorang Social Media Manager spesialis konten viral (TikTok, YouTube Shorts, Reels).
Berdasarkan teks subtitle spesifik dari klip video berikut, dan informasi konteks video aslinya, buatkan Title (Judul menarik), Description (Deskripsi ringkas yang memancing interaksi), Tags (Hashtags yang relevan), dan Highlight (Teks lucu/menjual singkat maksimal 3 kata, misal: "gg gak ?", "kaget momen", atau "minus -1 kuping").
Respons HANYA dalam bentuk JSON yang valid di dalam blok kode Markdown (```json ... ```) tanpa tambahan teks apapun.
Gunakan bahasa sesuai dengan output yang diminta.

Output Bahasa: {language}

Konteks Video Asli:
- Channel: {channel_name}
- Judul Video: {youtube_title}
- Link YouTube: {youtube_url}
{context_str}

WAJIB DITAATI: 
1. Pada bagian `description`, HARUS cantumkan link YouTube asli di atas agar tetap mendukung kreator aslinya.
2. Referensi / Contoh gaya bahasa pembuatan judul dan deskripsi:
   Title: TABRAK HANTU MALAH KENA JUMPSCARE! Windah Basudara.
   Description: Momen Bang Windah Lupa Disampingnya Ada Mamah Agnes
   Tonton video aslinya di: {youtube_url} #shorts #windahbasudara #windah #mediashare
3. Highlight adalah teks yang sangat singkat (maksimal 3-4 kata) yang memancing rasa penasaran, lucu, atau bombastis.
4. Jika data `words_data` diberikan, tulis ulang data tersebut ke dalam key `enriched_transcript` dengan menambahkan field `emotion` dan `color` (gunakan kode Hex). WAJIB gunakan `#FFFF00` (Kuning) untuk kata yang bernada netral/biasa. Gunakan warna mencolok lain (misal `#FF0000` untuk marah/umpatan) hanya pada kata yang memiliki emosi/penekanan kuat. Jangan mengubah nilai `start` dan `end`.
5. Gunakan informasi tingkat suara (`voice_level`: yelling, whispering, normal) pada setiap kata di dalam `words_data` untuk membantu menentukan `emotion` secara akurat (misal: yelling = marah/shock, whispering = fear/sedih/bored, normal = neutral/happy/dll).
6. Tidak boleh ada emosi bertumpuk kecuali emosi netral (tidak boleh: disgust -> marah -> happy, harus disgust -> netral (n detik) -> emosi lain), emosi yang sama boleh muncul kembali setelah 5 detik

Teks Subtitle Klip Ini:
{clip_text}

Data Kata (words_data) (Jika ada, gunakan untuk field enriched_transcript):
{json.dumps(words_data) if words_data else "Tidak ada data kata."}

KATEGORI EMOSI YANG DIIZINKAN (EMOTION_LIST):
Hanya gunakan salah satu dari nilai di bawah ini untuk setiap segmen teks. Jika tidak ada emosi spesifik, gunakan "neutral".

{emotion_str}

Format JSON yang wajib:
```json
{{
    "title": "Judul klip clickbait yang menarik",
    "description": "Deskripsi klip yang interaktif beserta link youtube asli",
    "tags": "#foryou #viral #dsb",
    "highlight": "Teks highlight lucu/singkat",
    "enriched_transcript": [
        {{
            "word": "kata",
            "start": 0.0,
            "end": 0.5,
            "emotion": "kaget",
            "color": "#FF0000"
        }}
    ]
}}
```
"""
        provider_name = (ai_config.get("provider") or ai_config.get("ai_provider") or "ollama").lower()
        log.info( f"[AI] Mengirim permintaan metadata ke AI Provider: {provider_name.upper()}...")

        try:
            provider = AIProviderFactory.create(provider_name)
            raw_response = provider.generate(prompt, ai_config, event_hook)

            # Find JSON
            match_obj = re.search(r'\{\s*".*"\s*:.*\s*\}', raw_response, re.DOTALL)
            if match_obj:
                return json.loads(match_obj.group(0))
            return json.loads(raw_response.strip())
        except Exception as e:
            log.error( f"[ERROR] Gagal men-generate metadata: {e}")
            return {}

ai_detector = AIHighlightDetector()
