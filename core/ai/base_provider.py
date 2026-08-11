from typing import Any, Dict, Optional, Protocol


class AIProvider(Protocol):
    def generate(
        self, prompt: str, ai_config: Dict[str, Any], event_hook: Optional[Any] = None
    ) -> str:
        """Generates a response from the AI model based on the prompt."""
        ...
