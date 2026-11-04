"""Append-only human decisions; accepting edits a draft, never a published run."""
from fastapi import HTTPException
from ..models.history import RunFinding, SuggestionDecision
from . import history
from .extraction import correct_requirement
from ..core.time import iso_utc


def view(row):
    return {"id":row.id,"run_id":row.run_id,"finding_id":row.finding_id,"actor_id":row.actor_id,
            "status":row.status,"draft_id":row.draft_id,"replacement_text":row.replacement_text,
            "created_at":iso_utc(row.created_at)}


def decide(db, project, run, finding_id, actor_id, data, version):
    history.require_writable(project)
    history.lock_project(db, project)
    finding = db.query(RunFinding).filter_by(id=finding_id,run_id=run.id).first()
    if not finding or not finding.data.get("rewrite_suggestion"):
        raise HTTPException(404, "Suggestion not found")
    latest = db.query(SuggestionDecision).filter_by(run_id=run.id,finding_id=finding.id).order_by(SuggestionDecision.id.desc()).first()
    if (latest.id if latest else 0) != data.expected_decision_id:
        raise HTTPException(409, "This suggestion decision changed. Refresh before saving.")
    draft, text = None, None
    if data.action != "rejected":
        if not data.confirm_intent:
            raise HTTPException(422, "Confirm that you reviewed the intent, quantities and exceptions")
        if not data.draft_id or version is None:
            raise HTTPException(428, "Select a draft and send its edit_version in If-Match")
        draft = history.revision_for(db, project, data.draft_id)
        if draft.parent_id != run.revision_id:
            raise HTTPException(409, "Use a draft based on this report's revision")
        history.edit_draft(db, project, draft, version)
        proposed = finding.data["rewrite_suggestion"]
        if data.action == "accepted":
            if data.text is not None and data.text != proposed:
                raise HTTPException(422, "Use edited when changing the proposal")
            text = proposed
        else:
            text = data.text
        if not text or not text.strip():
            raise HTTPException(422, "Replacement text cannot be empty")
        source = [req for extraction in (run.report or {}).get("extractions", {}).values()
                  for req in extraction.get("requirements", [])
                  if req.get("text") == finding.data.get("quoted_text")
                  and (not finding.data.get("element_id") or req.get("internal_id") == finding.data["element_id"])
                  and (not finding.data.get("source_ref") or req.get("source_ref") == finding.data["source_ref"])]
        if len(source) != 1 or not source[0].get("lineage_key"):
            raise HTTPException(409, "Cannot identify one original requirement; edit the draft manually")
        targets = [req for extraction in (draft.canonical_inputs or {}).get("artifacts", {}).values()
                   for req in extraction.get("requirements", []) if req.get("lineage_key") == source[0]["lineage_key"]]
        if len(targets) != 1 or targets[0]["text"] != source[0]["text"]:
            raise HTTPException(409, "This requirement changed in the draft; review it before applying a suggestion")
        correct_requirement(db, draft, targets[0]["internal_id"], {"text":text})
    row = SuggestionDecision(run_id=run.id,finding_id=finding.id,actor_id=actor_id,
            status=data.action,draft_id=draft.id if draft else None,replacement_text=text)
    db.add(row); db.flush()
    history.audit(db, project, actor_id, "suggestion_decided", decision_id=row.id, run_id=run.id,
                  finding_id=finding.id, action_taken=data.action, draft_id=row.draft_id)
    return {"decision":view(row),"draft_id":row.draft_id,"edit_version":draft.edit_version if draft else None}
