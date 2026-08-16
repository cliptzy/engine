import json
import re
from typing import Any, Dict, List, Optional

from core.ai.factory import AIProviderFactory
from core.logger import log

DEFAULT_PROMPT_TEMPLATE = """
You are a Viral Content Producer and Professional Video Editor who is an expert at highlight detection.
Your task is to analyze the following video transcript and find "Golden" moments that have high viral potential to be made into vertical short videos (YouTube Shorts, TikTok, Reels).

Input Context:
The transcript below is equipped with timestamps in seconds with the format [start_s - end_s]: conversation text.

Moment Selection Criteria (Mandatory):
1. Contains Emotion/Intrigue: Look for the funniest, most chaotic, emotional, story climax, heated debates, or extreme reactions (e.g., gamer screaming during a clutch/epic moment).
2. Has a Hook & Payoff: The clip must begin with an interesting statement/event (hook) and end with a clear conclusion/punchline (payoff).
3. Context Completeness: Never cut a conversation mid-sentence or leave hanging information.
4. Clip Duration: The total duration of each clip MUST be between 15 to 60 seconds.
5. Must not be the video opening and closing (first and last minutes of the video).
6. The distance between moments must be far enough (minimum 5 minutes).

Output Rules:
Since your output will be read by a system, you MUST ONLY respond with a valid JSON Object inside a Markdown code block (```json ... ```). Do not add introductory or closing text outside the JSON block.
Use the language according to the requested output language.

JSON Structure that must be used:
```json
{
  "segments": [
    {
      "start": 12.5,
      "end": 45.0,
      "duration": 32.5,
      "title": "A catchy and clickbait title for this clip (Max 6 words)",
      "reason": "Detailed reason why this moment is interesting, the emotion highlighted, and why it is suitable for a TikTok/Shorts audience",
      "score": 0.95
    }
  ]
}
```

Output Language: {language}
{custom_context}

Video Transcript:
{transcript_text}
"""


class AIHighlightDetector:
    def _is_local_provider(self, ai_config: Dict[str, Any]) -> bool:
        """
        Menentukan apakah provider AI berjenis Local (misal: Ollama, local OpenAI-compatible endpoint)
        atau Cloud External (misal: Google Gemini, official OpenAI, Groq, OpenRouter).
        """
        is_local = False
        provider = (
            ai_config.get("provider") or ai_config.get("ai_provider") or "ollama"
        ).lower()
        if provider == "ollama":
            is_local = True
        if provider == "openai":
            base_url = (ai_config.get("openai_base_url") or "").lower().strip()
            if base_url:
                local_indicators = [
                    "localhost",
                    "127.0.0.1",
                    "0.0.0.0",
                    "192.168.",
                    "10.",
                    "172.16.",
                    "lmstudio",
                    "vllm",
                    "local",
                ]
                if any(ind in base_url for ind in local_indicators):
                    is_local = True

        if is_local:
            log.info(f"[AI] Provider {provider} terdeteksi sebagai AI LOKAL. ")
        else:
            log.info(f"[AI] Provider {provider} terdeteksi sebagai AI CLOUD/EXTERNAL. ")
        return is_local

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

        provider_name = (
            ai_config.get("provider") or ai_config.get("ai_provider") or "ollama"
        ).lower()
        is_local = self._is_local_provider(ai_config)

        # Batas ukuran chunk (kondisional):
        # - AI Lokal (Ollama / local LLM 3B-9B): ~12.000 karakter (~2.500-3.000 token transkrip)
        #   Alasan: Model lokal 3-9B (Ornith-9B, Qwen3.5 7B, Llama 3 8B) memiliki batasan performa & konteks.
        #   Konteks ~3.000 token per chunk menjaga perhatian model tetap tajam, mecegah hallucination,
        #   serta memastikan output JSON selalu valid tanpa kehabisan memori VRAM/RAM.
        # - AI Cloud (Gemini, OpenAI, Groq, dll.): ~250.000 karakter (1 single chunk untuk transkrip normal)
        #   Alasan: Cloud LLM memiliki window konteks sangat besar (128k - 1M+ token).
        #   Tanpa pemecahan chunk, kita menghemat tagihan API token dari pengulangan prompt template & header overhead.
        max_chunk_chars = 12000 if is_local else 250000

        chunks = []
        current_chunk = []
        current_len = 0
        for line in formatted_lines:
            line_len = len(line) + 1  # +1 untuk newline
            if current_len + line_len > max_chunk_chars and current_chunk:
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
            f"\nAdditional User Context:\n{custom_prompt}\n" if custom_prompt else ""
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

            log.info(
                f"=== PROMPT KE AI ({provider_name.upper()}) ===\n{prompt}\n=========================================="
            )
            try:
                raw_response = provider.generate(prompt, ai_config, event_hook)
                log.info(
                    f"=== RESPONSE DARI AI ({provider_name.upper()}) ===\n{raw_response}\n============================================"
                )
            except Exception as ex:
                log.error(
                    f"=== ERROR DARI AI ({provider_name.upper()}) ===\n{ex}\n============================================"
                )
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
            f"- Additional Context from User: {user_context}\n" if user_context else ""
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
            f'{i}. "neutral" : Normal, flat, informative, or no prominent emotion.'
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
                    f'- "{eff_name}" (suitable for emotions: {", ".join(eff_emotions)})'
                )
            effects_str = "\n".join(effect_lines)
        except Exception:
            effects_str = "- (Video effect data not available)"

        is_local = self._is_local_provider(ai_config)
        # Untuk AI Cloud, gunakan chunk_size 1000 kata agar tidak memecah kata klip pendek secara berlebihan
        # Untuk AI Lokal, 150 kata menjaga reliabilitas JSON output pada model 3B-9B
        chunk_size = 150 if is_local else 1000
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
                f"\n(IMPORTANT: This is part {idx + 1} of {len(words_chunks)} of the total words. Focus on providing `enriched_transcript` ONLY for the words in this part!)\n"
                if len(words_chunks) > 1
                else ""
            )

            prompt = f"""
You are a Social Media Manager specializing in viral vertical videos.
Task: Create Title, Tags, Highlight (short funny pop-up text max 4 words), and `enriched_transcript`.
The response MUST be a valid JSON Object in markdown (```json ... ```).

Language: {language}
Video Context: {channel_name} - {youtube_title} ({youtube_url})
{context_str}{visual_str}{audio_str}{chunk_info}

RULES:
1. `highlight` must be very short (max 3-4 words).
2. If `Input words_data` is provided, rewrite it into `enriched_transcript` by adding `emotion` and `color` fields (Hex: #FFFF00 for neutral, striking colors for strong emotions). If `Input words_data` is `None.`, you MUST return an empty array `[]` for `enriched_transcript`.
3. Add a `score` field to `enriched_transcript` for each word, with a value between 0.0 to 1.0.
4. HOLISTIC EMOTION SYNTHESIS (IMPORTANT FOR STREAMERS/GAMERS):
   You have 3 sources of raw AI predictions: Face (Visual Emotion), Voice (voice_emotion/audio_event), and Text (text_emotion).
   - STREAMER ROLEPLAY AWARENESS: Streamers often say extreme words ("mati kau", "I'm dead") while joking. DO NOT TRUST TEXT 100%!
   - If the text has a strong meaning (angry/fear/shock) BUT Face (Visual) or Voice shows 'neutral' / 'happy', then it is only roleplay/casual. You MUST make it 'neutral' or 'happy'.
   - Strong emotions (angry/fear/shock) MUST ONLY BE CHOSEN if truly supported by Face evidence (panicking/angry) OR Voice (screaming/explosions/slamming table).
   - Your goal: Prevent emotion detection spam on casual chats.
5. VIDEO EFFECT OVERRIDE:
   Besides emotion, choose the specific video effect name that best describes the moment/word from the list below.
   Write that effect name into the `video_effect_override` field.
   - If the moment is a casual chat or does not need emphasis, you MUST fill it with "none".
   - If the moment is a climax but you are confused about choosing an effect, fill "random".
   - DO NOT SPAM! Use video effects (especially memes) only on moments that are truly funny or surprising.
6. NON-VERBAL EVENTS:
   If there is a screaming moment (Scream) or other important audio events but no words are spoken in `words_data` at that second, you CAN put a video effect into the `"standalone_video_effects"` array.
   Fill `"time"` (start second) and `"video_effect_override"` with the appropriate effect name.

VALID EMOTION CATEGORIES:
{emotion_str}

AVAILABLE VIDEO EFFECTS LIST:
{effects_str}

Overall Subtitle Text (as context):
{clip_text}

Input words_data (PART {idx + 1}/{len(words_chunks)}):
{json.dumps(chunk) if chunk else "None."}

JSON Output Format:
```json
{{
    "title": "...",
    "tags": "#...",
    "highlight": "...",
    "enriched_transcript": [
        {{"word": "word", "start": 0.0, "end": 0.5, "emotion": "surprise", "color": "#FF0000", "voice_emotion": "angry", "score": 0.8, "video_effect_override": "vineboom"}}
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
                log.info(
                    f"=== PROMPT KE AI ({provider_name.upper()}) ===\n{prompt}\n=========================================="
                )
                raw_response = provider.generate(prompt, ai_config, event_hook)
                log.info(
                    f"=== RESPONSE DARI AI ({provider_name.upper()}) ===\n{raw_response}\n============================================"
                )
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
