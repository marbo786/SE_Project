from copy import deepcopy
import pytest
from .test_history import create, upload, analyze
from app.models.history import RunFinding, AnalysisRun, SuggestionDecision, ProjectRevision


@pytest.fixture
def suggestion(client,headers,db_session):
    project = create(client,headers)
    revision = upload(client,headers,project)
    run = analyze(client,headers,project,revision)
    stored = db_session.get(AnalysisRun,run["id"])
    row = db_session.query(RunFinding).filter_by(run_id=run["id"],rule_id="FR-401").one()
    # Deterministic provider fixture: put a proposed rewrite in an isolated run.
    row.data = {**row.data,"rewrite_suggestion":"FR-1 The system shall respond within 2 seconds."}
    db_session.commit()
    draft = client.post(f"/v1/projects/{project['id']}/drafts",headers=headers,json={"parent_revision_id":revision["id"]}).json()
    return project,stored,row,draft


@pytest.mark.parametrize("action",["accepted","edited","rejected"])
def test_decisions_are_idempotent_and_leave_report_immutable(suggestion,client,headers,db_session,action):
    project,run,row,draft = suggestion
    before = deepcopy(run.report)
    url = f"/v1/runs/{run.id}/suggestions/{row.id}/decisions"
    auth = {**headers,"Idempotency-Key":"suggestion-once","If-Match":str(draft["edit_version"])}
    data = {"action":action,"draft_id":draft["id"],"confirm_intent":True}
    if action == "edited": data["text"] = "FR-1 The system shall respond within 3 seconds."
    first = client.post(url,headers=auth,json=data)
    assert first.status_code == 201, first.text
    assert client.post(url,headers=auth,json=data).json() == first.json()
    db_session.expire_all()
    assert db_session.get(AnalysisRun,run.id).report == before
    assert db_session.query(SuggestionDecision).count() == 1
    stored = db_session.get(ProjectRevision,draft["id"])
    text = next(req["text"] for extraction in stored.canonical_inputs["artifacts"].values() for req in extraction["requirements"])
    if action == "rejected": assert "fast" in text
    else:
        assert text == (data.get("text") or row.data["rewrite_suggestion"])
        assert not stored.extraction_confirmed and stored.state == "draft"
    replay = client.post(url,headers={**auth,"Idempotency-Key":"different"},json=data)
    assert replay.status_code == 409


def test_suggestion_requires_review_and_rejects_stale_draft(suggestion,client,headers,db_session):
    project,run,row,draft = suggestion
    url = f"/v1/runs/{run.id}/suggestions/{row.id}/decisions"
    data = {"action":"accepted","draft_id":draft["id"]}
    auth = {**headers,"Idempotency-Key":"ack","If-Match":str(draft["edit_version"])}
    assert client.post(url,headers=auth,json=data).status_code == 422
    data["confirm_intent"] = True
    auth["If-Match"] = str(draft["edit_version"]+1)
    assert client.post(url,headers=auth,json=data).status_code == 409
    assert db_session.query(SuggestionDecision).count() == 0


def test_suggestion_never_overwrites_changed_requirement(suggestion,client,headers,db_session):
    project,run,row,draft = suggestion
    stored = db_session.get(ProjectRevision,draft["id"])
    from app.services.extraction import correct_requirement
    req = next(req for ex in stored.canonical_inputs["artifacts"].values() for req in ex["requirements"])
    correct_requirement(db_session,stored,req["internal_id"],{"text":"FR-1 The system shall keep my manual edit."})
    db_session.commit()
    result = client.post(f"/v1/runs/{run.id}/suggestions/{row.id}/decisions",headers={**headers,"Idempotency-Key":"changed","If-Match":str(draft["edit_version"])},json={"action":"accepted","draft_id":draft["id"],"confirm_intent":True})
    assert result.status_code == 409
    assert db_session.query(SuggestionDecision).count() == 0


def test_foreign_user_cannot_read_or_apply_suggestion(suggestion,client,headers):
    _,run,row,draft = suggestion
    registration = client.post("/auth/register",json={"name":"Other","email":"other-suggestion@example.com","password":"other-password-123"})
    assert registration.status_code in (200,201)
    other = {"Authorization":"Bearer " + registration.json()["access_token"],"Idempotency-Key":"foreign"}
    assert client.get(f"/v1/runs/{run.id}/report",headers=other).status_code == 404
    assert client.post(f"/v1/runs/{run.id}/suggestions/{row.id}/decisions",headers=other,json={"action":"rejected"}).status_code == 404
