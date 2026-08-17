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
        character_1: str,
        character_2: str,
        ai_config: Dict[str, Any],
        event_hook: Optional[Any] = None,
        language: str = "Indonesian",
    ) -> List[Dict[str, str]]:
        """
        Men-generate script menggunakan LLM.
        Kembaliannya adalah list of dict dengan format:
        [
            {"speaker": "character_name", "text": "dialog..."},
            ...
        ]
        """
        provider_name = (
            ai_config.get("provider") or ai_config.get("ai_provider") or "ollama"
        ).lower()

        try:
            provider = AIProviderFactory.create(provider_name)
        except Exception as e:
            log.error(f"[ERROR] Gagal memuat AI Provider untuk script generator: {e}")
            return []

        prompt = f"""
You are an expert comedy writer specializing in TikTok/YouTube Shorts content.
Your task is to write a highly engaging, funny, and slightly chaotic conversation between two cartoon characters about a specific topic.

Topic: {topic}
Character 1: {character_1}
Character 2: {character_2}

Rules:
1. Make the dialogue punchy and short (suitable for vertical short videos).
2. The total conversation should take about 30-60 seconds when spoken (around 6-12 lines of dialogue).
3. Stay in character! Exaggerate their personalities.
4. You CAN add emotion or action tags at the beginning of the text like [scared], [sigh], [angry], [laughs], etc., if it fits the character's reaction. This helps guide the AI voice engine.
5. Output MUST be a valid JSON object containing a "script" array.
6. Use {language} Language.

JSON Structure:
```json
{{
  "script": [
    {{"speaker": "{character_1}", "text": "[sigh] Dialog baris pertama..."}},
    {{"speaker": "{character_2}", "text": "[angry] Balasan dari karakter 2..."}}
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

            # Extract JSON array
            def extract_array(text: str) -> list:
                # Attempt to find ```json ... ``` block
                match_md = re.search(
                    r"```json\s*(\[\s*\{.*?\}\s*\])\s*```",
                    text,
                    re.DOTALL | re.IGNORECASE,
                )
                if match_md:
                    return json.loads(match_md.group(1))

                # Attempt to find bare array
                match_arr = re.search(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL)
                if match_arr:
                    return json.loads(match_arr.group(0))

                # Try parsing raw string
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return parsed
                return []

            try:
                # Check if the raw response is a JSON object (forced by response_format="json_object")
                parsed_raw = json.loads(raw_response.strip())
                if isinstance(parsed_raw, list):
                    return parsed_raw
                if isinstance(parsed_raw, dict):
                    if "script" in parsed_raw and isinstance(
                        parsed_raw["script"], list
                    ):
                        return parsed_raw["script"]
                    # If the LLM dumped everything in a single string value
                    for key, value in parsed_raw.items():
                        if isinstance(value, list):
                            return value
                        if isinstance(value, str):
                            extracted = extract_array(value)
                            if extracted:
                                return extracted
            except Exception:
                pass

            # Fallback to extracting from raw string
            extracted_script = extract_array(raw_response)
            if extracted_script:
                return extracted_script

            log.warning("Format JSON tidak dikenali.")
            return []
        except Exception as e:
            log.error(f"[Brainrot] Gagal generate script: {e}")
            return []


brainrot_script_generator = BrainrotScriptGenerator()
