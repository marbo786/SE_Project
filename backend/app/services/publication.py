"""One transaction publishes a run; previous run data is never deleted."""
from copy import deepcopy
import json
from ..core.time import utcnow, iso_utc
from ..models.history import AnalysisRun, ProjectRevision, Requirement, UMLElement, RunFinding, RunTraceLink, RunQualityScore, ReviewDecision
from ..models.finding import Finding
from ..models.traceability import TraceLink
from ..models.score import QualityScore
from .history import finding_fingerprint, trace_fingerprint, latest_decisions, audit, persist_elements


def publish_run(db, project, run, findings, candidates, scores, extractions, artifacts):
    previous = db.get(AnalysisRun, project.published_run_id) if project.published_run_id else None
    compatible = previous and previous.input_hash == run.input_hash and previous.versions == run.versions
    prior_decisions = latest_decisions(db, previous.id) if previous else {}
    carry = {}
    if compatible:
        for model, kind in [(RunFinding, 'finding'), (RunTraceLink, 'trace')]:
            for target in db.query(model).filter_by(run_id=previous.id):
                decision = prior_decisions.get((kind, target.id))
                if decision:
                    carry[(kind, target.fingerprint)] = decision
    lineages = {req['internal_id']: req['lineage_key'] for extracted in extractions.values() for req in extracted.get('requirements', [])}
    immutable_findings, immutable_links = [], []
    for finding in findings:
        fingerprint = finding_fingerprint(finding, lineages)
        row = RunFinding(run_id=run.id, fingerprint=fingerprint, rule_id=finding['rule_id'],
            severity=finding['severity'], element_key=finding.get('element_id'), data=deepcopy(finding))
        db.add(row); db.flush()
        immutable_findings.append({**finding, 'id': row.id, 'fingerprint': fingerprint})
        if decision := carry.get(('finding', fingerprint)):
            db.add(ReviewDecision(run_id=run.id, finding_id=row.id, actor_id=decision.actor_id, status=decision.status,
                origin='carried', reason=decision.reason, carried_from_id=decision.id))
    effective_links = []
    for candidate in candidates:
        fingerprint = trace_fingerprint(candidate)
        row = RunTraceLink(run_id=run.id, fingerprint=fingerprint,
            **{key: candidate[key] for key in ('source_type', 'source_id', 'target_type', 'target_id')}, data=deepcopy(candidate))
        db.add(row); db.flush()
        immutable_links.append({**candidate, 'id': row.id, 'fingerprint': fingerprint})
        decision = carry.get(('trace', fingerprint))
        # Temporary compatibility for integrations that wrote the old table. The
        # original actor is unknown and is never attributed to the project owner.
        legacy = None
        if compatible and not decision:
            legacy = db.query(TraceLink).filter_by(project_id=project.id,
                **{key: candidate[key] for key in ('source_type', 'source_id', 'target_type', 'target_id')}).first()
        status = decision.status if decision else legacy.status if legacy and not legacy.is_stale else 'suggested'
        if decision or status != 'suggested':
            db.add(ReviewDecision(run_id=run.id, trace_id=row.id, actor_id=decision.actor_id if decision else None,
                status=status, origin='carried' if decision else 'legacy_adapter',
                reason=decision.reason if decision else 'Legacy adapter decision; original reviewer unknown.',
                carried_from_id=decision.id if decision else None))
        effective_links.append({**candidate, 'status': status})
    now = utcnow()
    revision = db.get(ProjectRevision, run.revision_id)
    if not db.query(Requirement).filter_by(revision_id=revision.id).first() and not db.query(UMLElement).filter_by(revision_id=revision.id).first():
        persist_elements(db, revision, {'artifacts': extractions})
    score_payload = {**scores, 'computed_at': iso_utc(now)}
    db.add(RunQualityScore(run_id=run.id, overall_score=scores['overall_score'], payload=score_payload, computed_at=now))
    run.status = 'completed' if scores['details']['complete'] else 'partial'
    run.stage, run.finished_at = 'finished', now
    run.counts = {'requirements': len(lineages), 'findings': len(findings), 'trace_links': len(candidates)}
    from ..llm.engine import usage_summary
    run.report = {'ai_usage': usage_summary(db, run.id), 'schema_version': '1', 'run_id': run.id, 'revision_id': run.revision_id,
        'versions': run.versions, 'input_hash': run.input_hash, 'score': score_payload,
        'findings': immutable_findings, 'trace_links': immutable_links, 'extractions': deepcopy(extractions),
        'warnings': scores['details'].get('warnings', []),
        'review_carry': {'compatible': bool(compatible), 'previous_run_id': previous.id if previous else None,
            'stale_decisions': len(prior_decisions) if previous and not compatible else 0}}
    publish = run.status == 'completed' or not previous or previous.status != 'completed'
    if publish:
        # Only the legacy projection is replaced. Its source run remains available.
        db.query(Finding).filter_by(project_id=project.id).delete()
        stale = [dict((col.name, getattr(link, col.name)) for col in TraceLink.__table__.columns if col.name not in {'id', 'project_id', 'created_at'})
            for link in db.query(TraceLink).filter(TraceLink.project_id == project.id, TraceLink.status != 'suggested')] if previous and not compatible else []
        db.query(TraceLink).filter_by(project_id=project.id).delete()
        fields = {c.name for c in Finding.__table__.columns} - {'id', 'project_id', 'created_at'}
        for finding in findings:
            db.add(Finding(project_id=project.id, **{k: v for k, v in finding.items() if k in fields}))
        for link in effective_links:
            db.add(TraceLink(project_id=project.id, **link))
        for link in stale:
            db.add(TraceLink(project_id=project.id, **{**link, 'is_stale': True}))
        score = db.query(QualityScore).filter_by(project_id=project.id).first()
        if not score:
            score = QualityScore(project_id=project.id); db.add(score)
        for key, value in scores.items():
            setattr(score, key, value)
        score.computed_at = now
        project.published_run_id = run.id
    for artifact in artifacts:
        if str(artifact.id) in extractions:
            artifact.extracted_content = json.dumps(extractions[str(artifact.id)], ensure_ascii=False)
    project.status, project.analysis_error = ('done' if run.status == 'completed' else 'partial'), None
    audit(db, project, run.requested_by, 'analysis_finished', run_id=run.id, status=run.status, published=publish)
