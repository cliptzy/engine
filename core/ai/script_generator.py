import json
import re
from typing import Any, Dict, List, Optional

from core.ai.factory import AIProviderFactory
from core.logger import log


class BrainrotScriptGenerator:
    """Generator untuk script percakapan Brainrot video."""

    def generate_script(
        self,
        topic: str,
        narrator: str,
        ai_config: Dict[str, Any],
        event_hook: Optional[Any] = None,
        language: str = "Indonesian",
    ) -> Dict[str, Any]:
        """
        Men-generate script menggunakan LLM.
        Kembaliannya adalah dict dengan format:
        {
            "title": "...",
            "tags": ["...", "..."],
            "script": [
                {"speaker": "narrator", "text": "story text..."},
                ...
            ]
        }
        """
        provider_name = (
            ai_config.get("provider") or ai_config.get("ai_provider") or "ollama"
        ).lower()

        try:
            provider = AIProviderFactory.create(provider_name)
        except Exception as e:
            log.error(f"[ERROR] Gagal memuat AI Provider untuk script generator: {e}")
            return {}

        prompt = f"""
You are an expert storyteller specializing in viral TikTok/YouTube Shorts content (like Reddit stories).
Your task is to write a highly engaging, dramatic, and interesting story/narration about a specific topic.

Topic: {topic}
Narrator: {narrator}

Rules:
1. Make the narration punchy, fast-paced, and engaging (suitable for vertical short videos).
2. The total story should take about 120-180 seconds when spoken. Split it into multiple short sentences/segments.
3. Stay in character! Exaggerate the narrator's personality if needed.
4. DO NOT add any emotion or action tags (like [scared], [sigh], [angry]). Only output the spoken text.
5. Output MUST be a valid JSON object containing a "script" array, "title" (string), and "tags" (array of strings).
6. Use {language} Language.
7. Include a Call to Action (CTA) in the middle of the script asking viewers to subscribe/follow, like, and share the video.

JSON Structure:
```json
{{
  "title": "Judul Menarik",
  "tags": ["#tag1", "#tag2"],
  "script": [
    {{"speaker": "{narrator}", "text": "Kalimat pertama dari cerita..."}},
    {{"speaker": "{narrator}", "text": "Kalimat kedua yang lebih seru..."}}
  ]
}}
```
"""
        log.info(
            f"[Brainrot] Meminta script ke AI Provider: {provider_name.upper()}..."
        )
        if event_hook:
            event_hook("status", "Sedang membuat script percakapan (AI)...")

        try:
            raw_response = provider.generate(prompt, ai_config, event_hook)
            log.info(f"[Brainrot] AI Script Response:\n{raw_response}")

            def extract_dict(text: str) -> dict:
                match_md = re.search(
                    r"```json\s*(\{.*?\})\s*```",
                    text,
                    re.DOTALL | re.IGNORECASE,
                )
                if match_md:
                    return json.loads(match_md.group(1))

                match_arr = re.search(r"\{.*\}", text, re.DOTALL)
                if match_arr:
                    try:
                        return json.loads(match_arr.group(0))
                    except:
                        pass

                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except:
                    pass
                return {}

            try:
                parsed_raw = json.loads(raw_response.strip())
                if isinstance(parsed_raw, dict) and "script" in parsed_raw:
                    return parsed_raw
            except Exception:
                pass

            extracted = extract_dict(raw_response)
            if extracted and "script" in extracted:
                return extracted

            log.warning("Format JSON tidak dikenali.")
            return {}
        except Exception as e:
            log.error(f"[Brainrot] Gagal generate script: {e}")
            return {}


brainrot_script_generator = BrainrotScriptGenerator()
