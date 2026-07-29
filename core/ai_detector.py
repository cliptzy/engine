"""
AI Highlight Detection Service supporting Local Ollama, Google Gemini, and OpenAI GPT.
"""

import json
import re
import requests
from typing import List, Dict, Any, Optional
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
5. Larangan: Tidak boleh opening dan closing video

Aturan Output:
Karena output Anda akan dibaca oleh sistem, Anda HANYA boleh merespons dengan JSON Object yang valid di dalam blok kode Markdown (```json ... ```). Jangan menambahkan teks pengantar atau penutup di luar blok JSON tersebut.

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

Transkrip Video:
{transcript_text}
"""

class AIHighlightDetector:
    def detect_highlights(
        self,
        transcript_segments: List[Dict[str, Any]],
        ai_config: Dict[str, Any],
        event_hook: Optional[Any] = None
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

        transcript_text = "\n".join(formatted_lines)
        if len(transcript_text) > 25000:
            # Trim if transcript exceeds context budget
            transcript_text = transcript_text[:25000] + "\n...[transkrip dipotong]"

        template = ai_config.get("ai_prompt")
        if not template or not template.strip():
            template = DEFAULT_PROMPT_TEMPLATE
        
        prompt = template.replace("{transcript_text}", transcript_text)
        provider = (ai_config.get("provider") or "ollama").lower()

        if callable(event_hook):
            event_hook("log", f"[AI] Mengirim transkrip ke AI Provider: {provider.upper()}...")

        if provider == "ollama":
            raw_response = self._call_ollama(prompt, ai_config, event_hook)
        elif provider == "gemini":
            raw_response = self._call_gemini(prompt, ai_config, event_hook)
        elif provider == "openai":
            raw_response = self._call_openai(prompt, ai_config, event_hook)
        else:
            raise ValueError(f"AI Provider tidak dikenal: {provider}")

        highlights = self._parse_json_highlights(raw_response)
        if callable(event_hook):
            event_hook("log", f"[AI] Berhasil mendeteksi {len(highlights)} momen highlight dari AI!")

        return highlights

    def _call_ollama(self, prompt: str, ai_config: Dict[str, Any], event_hook: Optional[Any]) -> str:
        host = (ai_config.get("ollama_host") or "http://localhost:11434").rstrip("/")
        model = ai_config.get("ollama_model") or "llama3"
        url = f"{host}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.3}
        }
        
        log.info(f"Connecting to Local Ollama at {url} (model: {model})...")
        try:
            res = requests.post(url, json=payload, timeout=120)
            if res.status_code != 200:
                err_detail = res.text[:300]
                raise RuntimeError(f"HTTP {res.status_code}: {err_detail}")
            data = res.json()
            return data.get("response", "")
        except Exception as e:
            msg = f"Gagal menghubungi Local Ollama ({url}): {e}"
            log.error(msg)
            raise RuntimeError(msg)

    def _call_gemini(self, prompt: str, ai_config: Dict[str, Any], event_hook: Optional[Any]) -> str:
        api_key = (ai_config.get("gemini_key") or "").strip()
        if not api_key:
            raise ValueError("Google Gemini API Key belum diisi. Masukkan API Key di form AI!")

        model_name = (ai_config.get("gemini_model") or "gemini-1.5-flash").strip()

        try:
            from google import genai
            from google.genai import types

            log.info(f"Connecting to Google GenAI SDK (model: {model_name})...")
            client = genai.Client(api_key=api_key)
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            if response and response.text:
                return response.text
            raise RuntimeError("Respon dari Google GenAI SDK kosong.")
        except Exception as e:
            log.warning(f"Google GenAI SDK error ({e}). Falling back to REST API...")
            return self._call_gemini_rest(prompt, api_key, model_name, event_hook)

    def _call_gemini_rest(self, prompt: str, api_key: str, model_name: str, event_hook: Optional[Any]) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        if res.status_code != 200:
            try:
                err_msg = res.json().get("error", {}).get("message", res.text[:200])
            except Exception:
                err_msg = res.text[:200]
            raise RuntimeError(f"HTTP {res.status_code} - {err_msg}")
        
        data = res.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
        raise RuntimeError("Respon dari Gemini REST API kosong.")



    def _call_openai(self, prompt: str, ai_config: Dict[str, Any], event_hook: Optional[Any]) -> str:
        api_key = (ai_config.get("openai_key") or "").strip()
        if not api_key:
            raise ValueError("OpenAI API Key belum diisi. Masukkan API Key di form AI!")

        model_name = (ai_config.get("openai_model") or "gpt-4o-mini").strip()
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a professional video editor and JSON highlight generator."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3
        }

        try:
            res = requests.post(url, json=payload, headers=headers, timeout=60)
            if res.status_code != 200:
                try:
                    err_json = res.json()
                    err_msg = err_json.get("error", {}).get("message", res.text[:200])
                except Exception:
                    err_msg = res.text[:200]
                raise RuntimeError(f"HTTP {res.status_code} - {err_msg}")

            data = res.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            raise RuntimeError("Respon dari OpenAI API kosong.")
        except Exception as e:
            msg = f"Gagal memanggil OpenAI API: {e}"
            log.error(msg)
            raise RuntimeError(msg)

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
        ai_config: Dict[str, Any],
        event_hook: Optional[Any] = None
    ) -> Dict[str, Any]:
        if not clip_text or not clip_text.strip():
            log.warning("Teks subtitle klip kosong, tidak dapat men-generate metadata.")
            return {}

        clip_text = clip_text.strip()
        if len(clip_text) > 10000:
            clip_text = clip_text[:10000] + "..."

        prompt = f"""
Anda adalah seorang Social Media Manager spesialis konten viral (TikTok, YouTube Shorts, Reels).
Berdasarkan teks subtitle spesifik dari klip video berikut, dan informasi konteks video aslinya, buatkan Title (Judul menarik), Description (Deskripsi ringkas yang memancing interaksi), dan Tags (Hashtags yang relevan).
Respons HANYA dalam bentuk JSON yang valid di dalam blok kode Markdown (```json ... ```) tanpa tambahan teks apapun.

Konteks Video Asli:
- Channel: {channel_name}
- Judul Video: {youtube_title}

Teks Subtitle Klip Ini:
{clip_text}

Format JSON yang wajib:
```json
{{
    "title": "Judul klip clickbait yang menarik",
    "description": "Deskripsi klip yang interaktif",
    "tags": "#foryou #viral #dsb"
}}
```
"""
        provider = (ai_config.get("provider") or "ollama").lower()
        if callable(event_hook):
            event_hook("log", f"[AI] Mengirim permintaan metadata ke AI Provider: {provider.upper()}...")

        try:
            if provider == "ollama":
                raw_response = self._call_ollama(prompt, ai_config, event_hook)
            elif provider == "gemini":
                raw_response = self._call_gemini(prompt, ai_config, event_hook)
            elif provider == "openai":
                raw_response = self._call_openai(prompt, ai_config, event_hook)
            else:
                raise ValueError(f"AI Provider tidak dikenal: {provider}")

            # Find JSON
            match_obj = re.search(r'\{\s*".*"\s*:.*\s*\}', raw_response, re.DOTALL)
            if match_obj:
                return json.loads(match_obj.group(0))
            return json.loads(raw_response.strip())
        except Exception as e:
            if callable(event_hook):
                event_hook("log", f"[ERROR] Gagal men-generate metadata: {e}")
            return {}

ai_detector = AIHighlightDetector()
