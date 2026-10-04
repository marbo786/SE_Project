import hashlib
from typing import Optional
from sqlalchemy.orm import Session
from .base import BaseLLMProvider, LLMResponse
from .groq_provider import GroqProvider
from .mock_provider import MockLLMProvider
from ..core.config import get_settings
from ..models.llm_log import LLMLog

def get_provider() -> BaseLLMProvider:
    settings = get_settings()
    if settings.LLM_PROVIDER == "groq":
        return GroqProvider()
    return MockLLMProvider()

from collections import OrderedDict
# Simple in-memory bounded cache
_cache: OrderedDict[str, str] = OrderedDict()
MAX_CACHE_SIZE = 500

def _make_cache_key(system_prompt: str, user_prompt: str) -> str:
    combined = system_prompt + "|||" + user_prompt
    return hashlib.sha256(combined.encode()).hexdigest()

async def call_llm(
    system_prompt: str,
    user_prompt: str,
    db: Optional[Session] = None,
    project_id: Optional[int] = None,
    retry: int = 3
) -> str:
    """Call LLM with caching, logging, and retry."""
    provider = get_provider()
    cache_key = _make_cache_key(system_prompt, user_prompt)

    if cache_key in _cache:
        # Log cache hit
        if db:
            log = LLMLog(
                project_id=project_id,
                provider=provider.provider_name,
                model=provider.default_model,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0.0,
                cache_hit="true",
                prompt_hash=cache_key
            )
            db.add(log)
            db.commit()
        return _cache[cache_key]

    last_error = None
    for attempt in range(retry):
        try:
            response: LLMResponse = await provider.complete(system_prompt, user_prompt)
            _cache[cache_key] = response.content
            if len(_cache) > MAX_CACHE_SIZE:
                _cache.popitem(last=False)
            if db:
                log = LLMLog(
                    project_id=project_id,
                    provider=response.provider,
                    model=response.model,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    latency_ms=response.latency_ms,
                    cache_hit="false",
                    prompt_hash=cache_key
                )
                db.add(log)
                db.commit()
            return response.content
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"LLM call failed after {retry} attempts: {last_error}")
