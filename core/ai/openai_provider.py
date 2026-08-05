from typing import Dict, Any, Optional
from core.logger import log
from core.ai.base_provider import AIProvider

class OpenAIProvider:
    def generate(self, prompt: str, ai_config: Dict[str, Any], event_hook: Optional[Any] = None) -> str:
        from openai import OpenAI
        
        api_key = (ai_config.get("openai_key") or "").strip()
        if not api_key:
            raise ValueError("OpenAI API Key belum diisi. Masukkan API Key di form AI!")

        model_name = (ai_config.get("openai_model") or "gpt-4o-mini").strip()
        base_url = (ai_config.get("openai_base_url") or "").strip()
        
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
            
        client = OpenAI(**kwargs) # type: ignore

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a professional video editor and JSON highlight generator."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                stream=True
            )

            full_response = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    full_response += content_chunk
                    if callable(event_hook):
                        event_hook("log_inline", content_chunk)
                        
            log.info( "")
                
            if not full_response:
                raise RuntimeError("Respon dari OpenAI API kosong.")
            return full_response
        except Exception as e:
            msg = f"Gagal memanggil OpenAI API: {e}"
            log.error(msg)
            raise RuntimeError(msg)
