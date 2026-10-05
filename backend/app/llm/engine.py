import hashlib
import asyncio
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

def _make_cache_key(provider: str, model: str, system_prompt: str, user_prompt: str) -> str:
    combined = provider + "|||" + model + "|||" + system_prompt + "|||" + user_prompt
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
    provider_name = provider.provider_name
    model_name = provider.default_model
    
    cache_key = _make_cache_key(provider_name, model_name, system_prompt, user_prompt)

    if db:
        cached = db.query(LLMLog).filter(LLMLog.prompt_hash == cache_key, LLMLog.response_text != None).first()
        if cached:
            log = LLMLog(
                project_id=project_id,
                provider=provider_name,
                model=model_name,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0.0,
                cache_hit="true",
                prompt_hash=cache_key,
                response_text=cached.response_text
            )
            db.add(log)
            db.commit()
            return cached.response_text

    last_error = None
    backoff = 1.0
    for attempt in range(retry):
        try:
            response: LLMResponse = await provider.complete(system_prompt, user_prompt)
            if db:
                log = LLMLog(
                    project_id=project_id,
                    provider=response.provider,
                    model=response.model,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    latency_ms=response.latency_ms,
                    cache_hit="false",
                    prompt_hash=cache_key,
                    response_text=response.content
                )
                db.add(log)
                db.commit()
            return response.content
        except Exception as e:
            last_error = e
            if "Rate Limit" in str(e) or "429" in str(e):
                await asyncio.sleep(backoff)
                backoff *= 2
            continue
    raise RuntimeError(f"LLM call failed after {retry} attempts: {last_error}")
