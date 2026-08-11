import json
from typing import Any, Dict, Optional

import requests

from core.ai.base_provider import AIProvider
from core.logger import log


class GeminiProvider:
    def generate(
        self, prompt: str, ai_config: Dict[str, Any], event_hook: Optional[Any] = None
    ) -> str:
        api_key = (ai_config.get("gemini_key") or "").strip()
        if not api_key:
            raise ValueError(
                "Google Gemini API Key belum diisi. Masukkan API Key di form AI!"
            )

        model_name = (ai_config.get("gemini_model") or "gemini-1.5-flash").strip()

        try:
            from google import genai
            from google.genai import types

            log.info(
                f"Connecting to Google GenAI SDK (model: {model_name}) with streaming..."
            )
            client = genai.Client(api_key=api_key)

            response = client.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            full_response = ""
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    if callable(event_hook):
                        event_hook("log_inline", chunk.text)

            log.info("")

            if not full_response:
                raise RuntimeError("Respon dari Google GenAI SDK kosong.")
            return full_response
        except Exception as e:
            log.warning(
                f"Google GenAI SDK error ({e}). Falling back to REST API streaming..."
            )
            return self._call_gemini_rest(prompt, api_key, model_name, event_hook)

    def _call_gemini_rest(
        self, prompt: str, api_key: str, model_name: str, event_hook: Optional[Any]
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?alt=sse&key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        res = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120,
            stream=True,
        )
        if res.status_code != 200:
            try:
                err_msg = res.json().get("error", {}).get("message", res.text[:200])
            except Exception:
                err_msg = res.text[:200]
            raise RuntimeError(f"HTTP {res.status_code} - {err_msg}")

        full_response = ""
        for line in res.iter_lines():
            line = line.decode("utf-8").strip()
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            chunk = parts[0].get("text", "")
                            full_response += chunk
                            if callable(event_hook) and chunk:
                                event_hook("log_inline", chunk)
                except Exception:
                    pass

        log.info("")

        if not full_response:
            raise RuntimeError("Respon dari Gemini REST API kosong.")
        return full_response
