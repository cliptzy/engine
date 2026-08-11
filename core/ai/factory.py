from core.ai.base_provider import AIProvider
from core.ai.gemini_provider import GeminiProvider
from core.ai.ollama_provider import OllamaProvider
from core.ai.openai_provider import OpenAIProvider


class AIProviderFactory:
    @staticmethod
    def create(provider_name: str) -> AIProvider:
        provider_name = provider_name.lower()
        if provider_name == "ollama":
            return OllamaProvider()
        elif provider_name == "gemini":
            return GeminiProvider()
        elif provider_name == "openai":
            return OpenAIProvider()
        else:
            raise ValueError(f"AI Provider tidak dikenal: {provider_name}")
