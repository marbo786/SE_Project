import json
from datetime import timedelta
import pytest
from app.core.config import ai_run, get_settings
from app.core.time import utcnow
from app.llm import engine
from app.llm.base import LLMResponse
from app.models.llm_log import LLMCache, LLMCall
from app.models.project import Project
from app.services.history import ensure_revision, start_run
from app.pipeline.checks.llm_checks import check_testability, LLMCheckError


class Provider:
    provider_name = "fixture"
    default_model = "fixture-v1"
    def __init__(self, content=None):
        self.content = content or '{"results":[{"requirement_id":"R0","testable":true}]}'
        self.calls = 0
    async def complete(self, *args):
        self.calls += 1
        return LLMResponse(self.content, 12, 8, 1, self.provider_name, self.default_model)


@pytest.fixture
def scope(client, headers, db_session):
    pid = client.post("/projects/", headers=headers, json={"name":"Cache"}).json()["id"]
    project = db_session.get(Project, pid)
    revision = ensure_revision(db_session, project)
    run = start_run(db_session, project, revision, project.user_id, validate=False)
    db_session.commit()
    token = ai_run.set(run.id)
    try:
        yield project, run
    finally:
        ai_run.reset(token)


REQS = [{"id":"FR-1", "text":"The system shall send mail to private@example.com."}]


async def test_validated_cache_hit_has_zero_charge(scope, db_session, monkeypatch):
    project, _ = scope
    provider = Provider()
    monkeypatch.setattr(engine, "get_provider", lambda: provider)
    for _ in range(2):
        assert await check_testability(REQS, db_session, project.id) == []
    assert provider.calls == 1
    assert db_session.query(LLMCache).count() == 1
    calls = db_session.query(LLMCall).order_by(LLMCall.id).all()
    assert [(c.status, c.usage_source) for c in calls] == [("validated", "provider"), ("cache_hit", "cache")]
    assert calls[1].reserved_tokens == 0
    assert "private@example.com" not in db_session.query(LLMCache).one().response_text


@pytest.mark.parametrize("damage", ["malformed", "references", "expired", "owner"])
async def test_bad_cache_entry_is_removed_and_refetched(scope, db_session, monkeypatch, damage):
    project, _ = scope
    provider = Provider()
    monkeypatch.setattr(engine, "get_provider", lambda: provider)
    await check_testability(REQS, db_session, project.id)
    cached = db_session.query(LLMCache).one()
    if damage == "malformed":
        cached.response_text = "{broken"
    elif damage == "references":
        cached.response_text = '{"results":[{"requirement_id":"invented","testable":true}]}'
    elif damage == "expired":
        cached.expires_at = utcnow() - timedelta(seconds=1)
    else:
        # A different existing user keeps the FK valid.
        from app.models.user import User
        other = User(name="Other", email="cacheother@example.com", hashed_password="unused")
        db_session.add(other); db_session.flush()
        cached.owner_id = other.id
    db_session.commit()
    assert await check_testability(REQS, db_session, project.id) == []
    assert provider.calls == 2


@pytest.mark.parametrize("changed", ["input", "model", "prompt"])
async def test_scope_changes_never_reuse_cache(scope, db_session, monkeypatch, changed):
    project, run = scope
    provider = Provider()
    monkeypatch.setattr(engine, "get_provider", lambda: provider)
    await check_testability(REQS, db_session, project.id)
    requirements = REQS
    if changed == "input":
        run.input_hash = "0" * 64; db_session.commit()
    elif changed == "model":
        provider.default_model = "fixture-v2"
    else:
        requirements = [{"id":"FR-1", "text":"The system shall save records."}]
    await check_testability(requirements, db_session, project.id)
    assert provider.calls == 2


async def test_invalid_provider_output_is_never_cached(scope, db_session, monkeypatch):
    project, _ = scope
    provider = Provider('{"results":[]}')
    monkeypatch.setattr(engine, "get_provider", lambda: provider)
    with pytest.raises(LLMCheckError):
        await check_testability(REQS, db_session, project.id)
    assert provider.calls == 2
    assert db_session.query(LLMCache).count() == 0
    assert all(c.status == "invalid_output" for c in db_session.query(LLMCall))


async def test_unknown_usage_keeps_reservation_and_stops_retries(scope, db_session, monkeypatch):
    project, run = scope
    provider = Provider()
    async def fail(*args):
        provider.calls += 1
        raise TimeoutError("private diagnostic")
    provider.complete = fail
    monkeypatch.setattr(engine, "get_provider", lambda: provider)
    monkeypatch.setattr(get_settings(), "LLM_RUN_TOKEN_BUDGET", 3000)
    with pytest.raises(engine.AIError, match="ai_token_budget_exceeded"):
        await engine.call_llm("JSON", "test", db_session, project.id)
    assert provider.calls == 1
    call = db_session.query(LLMCall).one()
    assert call.run_id == run.id and call.usage_source == "reserved_unknown"
    assert call.prompt_tokens is None and call.reserved_tokens > 2048
    # Simulate another attempt using the durable run context, not in-memory counters.
    with pytest.raises(engine.AIError, match="ai_token_budget_exceeded"):
        await engine.call_llm("JSON", "test", db_session, project.id)
    assert provider.calls == 1


async def test_missing_usage_is_unknown_not_zero(scope, db_session, monkeypatch):
    project, _ = scope
    provider = Provider()
    async def missing(*args):
        return LLMResponse('{"ok":true}', None, None, 1, "fixture", "fixture")
    provider.complete = missing
    monkeypatch.setattr(engine, "get_provider", lambda: provider)
    await engine.call_llm("JSON", "test", db_session, project.id)
    call = db_session.query(LLMCall).one()
    assert call.usage_source == "reserved_unknown" and call.prompt_tokens is None


async def test_cache_cleanup_preserves_unexpired_entries_and_accounting(scope, db_session, monkeypatch):
    from app.services.retention import prune_ai_cache
    project, run = scope
    provider = Provider()
    monkeypatch.setattr(engine, "get_provider", lambda: provider)
    await check_testability(REQS, db_session, project.id)
    assert prune_ai_cache(db_session, apply=True)["expired_entries"] == 0
    row = db_session.query(LLMCache).one()
    row.expires_at = utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert prune_ai_cache(db_session)["expired_entries"] == 1
    assert db_session.query(LLMCache).count() == 1
    assert prune_ai_cache(db_session, apply=True)["expired_entries"] == 1
    assert db_session.query(LLMCache).count() == 0
    assert engine.usage_summary(db_session, run.id) == {"provider_calls":1, "cache_hits":0,
        "reported_tokens":20, "unknown_usage_calls":0, "reserved_unknown_tokens":0}


async def test_cache_is_project_scoped_even_for_identical_inputs(scope, client, headers, db_session, monkeypatch):
    project, _ = scope
    provider = Provider()
    monkeypatch.setattr(engine, "get_provider", lambda: provider)
    await check_testability(REQS, db_session, project.id)
    pid = client.post("/projects/", headers=headers, json={"name":"Other project"}).json()["id"]
    other = db_session.get(Project, pid)
    run = start_run(db_session, other, ensure_revision(db_session, other), other.user_id, validate=False)
    db_session.commit()
    token = ai_run.set(run.id)
    try:
        await check_testability(REQS, db_session, pid)
    finally:
        ai_run.reset(token)
    assert provider.calls == 2 and db_session.query(LLMCache).count() == 2
