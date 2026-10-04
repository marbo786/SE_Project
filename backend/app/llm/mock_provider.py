import time
from typing import Optional
from .base import BaseLLMProvider, LLMResponse

MOCK_RESPONSES = {
    "testability": '{"results": [{"requirement_id": "MOCK-01", "testable": false, "reason": "The requirement uses vague language that cannot be measured objectively."}]}',
    "conflicts": '{"conflicts": []}',
    "default": '{"result": "mock response"}'
}

class MockLLMProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-model-v1"

    async def complete(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> LLMResponse:
        time.sleep(0.1)  # simulate latency
        # Choose response based on system prompt content
        content = MOCK_RESPONSES["default"]
        if "testab" in system_prompt.lower():
            content = MOCK_RESPONSES["testability"]
        elif "conflict" in system_prompt.lower():
            content = MOCK_RESPONSES["conflicts"]
        return LLMResponse(
            content=content,
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=100.0,
            provider="mock",
            model="mock-model-v1"
        )
