"""OpenAI-compatible local inference using the same audited gateway contract."""
import ipaddress
import time
from urllib.parse import urlsplit
import httpx
from .base import BaseLLMProvider, LLMResponse
from ..core.config import get_settings


class LocalProvider(BaseLLMProvider):
    def __init__(self):
        self.settings = get_settings()
        self.url = self.settings.LOCAL_LLM_URL
        parsed = urlsplit(self.url)
        try:
            local = ipaddress.ip_address(parsed.hostname or '').is_loopback
        except ValueError:
            local = parsed.hostname == 'localhost'
        if not local or parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('local_provider_requires_loopback_url')

    @property
    def provider_name(self):
        return 'local'

    @property
    def default_model(self):
        return self.settings.LLM_MODEL

    async def complete(self, system_prompt, user_prompt, model=None):
        started = time.monotonic()
        chosen = model or self.default_model
        payload = {'model': chosen, 'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}], 'temperature': 0.1, 'max_tokens': 2048}
        # Never inherit an outbound proxy or follow redirects to another host.
        async with httpx.AsyncClient(timeout=self.settings.LLM_TIMEOUT_SECONDS, trust_env=False, follow_redirects=False) as client:
            async with client.stream('POST', self.url, json=payload) as response:
                if response.status_code != 200:
                    raise RuntimeError('local_provider_failed')
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > self.settings.LLM_MAX_RESPONSE_CHARACTERS * 8 + 65536:
                        raise RuntimeError('local_provider_response_too_large')
        import json
        data = json.loads(body)
        choice = data['choices'][0]
        content = choice['message']['content']
        if not isinstance(content, str) or len(content) > self.settings.LLM_MAX_RESPONSE_CHARACTERS:
            raise RuntimeError('local_provider_invalid_response')
        usage = data.get('usage') or {}
        return LLMResponse(content, usage.get('prompt_tokens'), usage.get('completion_tokens'),
            (time.monotonic() - started) * 1000, 'local', chosen, finish_reason=choice.get('finish_reason', 'unknown'))
