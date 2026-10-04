import time
import httpx
from typing import Optional
from .base import BaseLLMProvider, LLMResponse
from ..core.config import get_settings

class GroqProvider(BaseLLMProvider):
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        self.settings = get_settings()
        self._model = "llama3-8b-8192"

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def default_model(self) -> str:
        return self._model

    async def complete(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> LLMResponse:
        chosen_model = model or self._model
        headers = {
            "Authorization": f"Bearer {self.settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": chosen_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 2048
        }
        start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.BASE_URL, headers=headers, json=payload)
        latency = (time.time() - start) * 1000
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency,
            provider="groq",
            model=chosen_model
        )
