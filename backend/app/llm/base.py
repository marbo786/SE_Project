from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    provider: str
    model: str
    cache_hit: bool = False

class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> LLMResponse:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        pass
