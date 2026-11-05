import asyncio
import httpx
import pytest
from app.core.config import get_settings
from app.llm.local_provider import LocalProvider


@pytest.mark.parametrize('url', ['https://example.com/v1/chat/completions', 'http://127.0.0.1.evil.example/v1', 'http://user:pass@localhost/v1', 'file:///tmp/model', 'http://192.168.1.1/v1'])
def test_local_provider_rejects_non_loopback_and_credentials(monkeypatch, url):
    monkeypatch.setattr(get_settings(), 'LOCAL_LLM_URL', url)
    with pytest.raises(ValueError):
        LocalProvider()


def test_local_provider_contract_and_redirect_refusal(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'LOCAL_LLM_URL', 'http://127.0.0.1:11434/v1/chat/completions')
    real_client = httpx.AsyncClient
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"ok":true}'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 3, 'completion_tokens': 4}})
    def client(**kwargs):
        assert kwargs['trust_env'] is False
        assert kwargs['follow_redirects'] is False
        return real_client(**kwargs, transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, 'AsyncClient', client)
    result = asyncio.run(LocalProvider().complete('Return JSON', 'Source text'))
    assert result.provider == 'local' and result.prompt_tokens == 3
    assert requests[0].url.host == '127.0.0.1'
    assert 'authorization' not in requests[0].headers
    def redirect(request):
        return httpx.Response(302, headers={'location': 'https://example.com'})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real_client(**kw, transport=httpx.MockTransport(redirect)))
    with pytest.raises(RuntimeError, match='local_provider_failed'):
        asyncio.run(LocalProvider().complete('Return JSON', 'Source text'))
