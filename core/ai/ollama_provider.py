import json
from typing import Any, Dict, Optional

import requests

from core.ai.base_provider import AIProvider
from core.logger import log


class OllamaProvider:
    def generate(
        self, prompt: str, ai_config: Dict[str, Any], event_hook: Optional[Any] = None
    ) -> str:
        host = (ai_config.get("ollama_host") or "http://localhost:11434").rstrip("/")
        model = ai_config.get("ollama_model") or "llama3"
        url = f"{host}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.3,
                "num_predict": 8192,
                "num_ctx": 16384
            },
        }

        log.info(f"Connecting to Local Ollama at {url} (model: {model})...")
        try:
            res = requests.post(url, json=payload, timeout=120, stream=True)
            if res.status_code != 200:
                err_detail = res.text[:300]
                raise RuntimeError(f"HTTP {res.status_code}: {err_detail}")

            full_response = ""
            for line in res.iter_lines():
                if line:
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    full_response += chunk

            log.info("")
            return full_response
        except Exception as e:
            msg = f"Gagal menghubungi Local Ollama ({url}): {e}"
            log.error(msg)
            raise RuntimeError(msg)
