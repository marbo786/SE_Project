"""Schema-valid scripted demo responses; never a real AI quality assessment."""
import json
import re
from typing import Optional
from .base import BaseLLMProvider, LLMResponse

class MockLLMProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-model-v2"

    async def complete(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> LLMResponse:
        data = json.loads(user_prompt)
        if system_prompt.startswith("Testability review schema v4."):
            results = []
            for item in data:
                vague = re.search(r"\b(?:fast|quickly|user-friendly)\b", item["text"], re.I)
                results.append({"requirement_id": item["requirement_id"], "testable": not bool(vague),
                    "reason": "Mock demo: the scripted check found vague wording; ask a stakeholder for a measurable target." if vague else None,
                    "evidence": vague.group() if vague else None})
            content = {"results": results}
        elif system_prompt.startswith("Conflict review schema v4."):
            content = {"reviewed_pairs": [item["pair_id"] for item in data], "conflicts": []}
        elif system_prompt.startswith("Requirements rewrite schema v2."):
            # Do not invent thresholds or silently change the author's intent.
            content = {"rewrite_suggestion": data["original_requirement"]}
        elif system_prompt.startswith("Semantic comparison schema v1."):
            content = {"intent_preserved": False, "original_quote": data["original"],
                "proposal_quote": data["proposal"],
                "explanation": "Mock demo cannot assess semantic equivalence; human review is required."}
        else:
            raise ValueError("unsupported_mock_schema")
        return LLMResponse(
            content=json.dumps(content),
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=0.0,
            provider="mock",
            model=self.default_model
        )
