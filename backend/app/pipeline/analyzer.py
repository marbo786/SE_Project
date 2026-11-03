"""Compute from a sealed input snapshot and atomically publish immutable history."""
from copy import deepcopy
import logging
from starlette.concurrency import run_in_threadpool
from ..core.config import run_config
from ..core.database import SessionLocal
from ..core.time import utcnow
from ..models.project import Project
from ..models.artifact import Artifact
from ..models.history import AnalysisRun
from ..services.history import ensure_revision, start_run, audit
from ..services.extraction import extract_artifact, source_evidence, read_bounded, merge_models
from ..services.publication import publish_run
from .checks.srs_checks import run_all_srs_checks
from .checks.uml_checks import run_all_uml_checks
from .checks.llm_checks import check_testability, check_conflicts
from .checks.traceability_checks import build_trace_links, check_traceability, trace_obligations
from .scoring import compute_scores


def extract_srs(artifact):
    return extract_artifact(artifact)


async def run_analysis_pipeline(project_id, _db=None, *, run_id=None):
    db = SessionLocal()
    context_token = None
    run = None
    try:
        project = db.get(Project, project_id)
        if not project or project.deleted_at:
            return
        if run_id:
            run = db.query(AnalysisRun).filter_by(id=run_id, project_id=project_id).first()
            if not run or run.status != 'queued':
                return
        else:
            # Compatibility for scripts/tests. HTTP callers persist the run first.
            revision = ensure_revision(db, project)
            run = start_run(db, project, revision, project.user_id, validate=False)
            db.commit()
        claimed = db.query(AnalysisRun).filter_by(id=run.id, status='queued').update(
            {'status': 'running', 'stage': 'extracting', 'started_at': utcnow()}, synchronize_session=False)
        if not claimed:
            db.rollback(); return
        project.status, project.analysis_error = 'analyzing', None
        db.commit(); db.refresh(run)
        context_token = run_config.set(run.input_snapshot.get('rules_config'))
        manifest = run.input_snapshot.get('artifacts', [])
        artifacts = db.query(Artifact).filter(Artifact.id.in_([a['id'] for a in manifest]), Artifact.revision_id == run.revision_id).all()
        if len(artifacts) != len(manifest):
            raise ValueError('Run input manifest is incomplete')
        canonical = (run.input_snapshot.get('canonical') or {}).get('artifacts', {})
        extracted, warnings = {}, []
        for artifact in artifacts:
            expected = next(a for a in manifest if a['id'] == artifact.id)
            if artifact.content_hash != expected['sha256']:
                raise ValueError('Artifact no longer matches the sealed input manifest')
            if str(artifact.id) in canonical:
                await run_in_threadpool(read_bounded, artifact)
                parsed = source_evidence(deepcopy(canonical[str(artifact.id)]), artifact)
            elif artifact.artifact_type == 'srs':
                parsed = await run_in_threadpool(extract_srs, artifact)
            elif run.input_snapshot['profile'] == 'architecture':
                parsed = await run_in_threadpool(extract_artifact, artifact)
            else:
                continue
            extracted[str(artifact.id)] = parsed
            warnings.extend(f"{artifact.original_filename}: {warning}" for warning in parsed.get('warnings', []))
        srs = next((a for a in artifacts if a.artifact_type == 'srs'), None)
        parsed = extracted.get(str(srs.id), {}) if srs else {}
        requirements = parsed.get('requirements', [])
        if not requirements:
            warnings.append('No requirements were extracted. Check and correct the draft before analysis.')
        models = merge_models(extracted, artifacts) if run.input_snapshot['profile'] == 'architecture' else {}
        if run.input_snapshot['profile'] == 'architecture':
            for kind in ('usecase', 'class', 'sequence'):
                if kind not in models:
                    warnings.append(f'The architecture profile requires a {kind} diagram.')
        run.stage, run.counts = 'checking', {'requirements': len(requirements)}
        db.commit()
        findings = run_all_srs_checks(parsed)
        # Checks are diagram-local; cross-diagram operation lookups use all classes.
        for artifact in artifacts:
            if artifact.artifact_type.startswith('uml_') and str(artifact.id) in extracted and models:
                findings.extend(run_all_uml_checks(extracted[str(artifact.id)], models.get('class')))
        if run.input_snapshot['mode'] == 'ai' and requirements:
            run.stage = 'ai_checks'; db.commit()
            try:
                findings.extend(await check_testability(requirements, db=db, project_id=project_id))
                findings.extend(await check_conflicts(requirements, db=db, project_id=project_id))
                from .repair import agentic_repair_loop
                await agentic_repair_loop(findings, db=db, project_id=project_id)
            except Exception as error:
                logging.getLogger(__name__).warning('Requested AI analysis failed (%s)', type(error).__name__)
                warnings.append('Requested AI checks did not finish. Deterministic results remain available; retry AI analysis later.')
        for warning in warnings:
            findings.append({'rule_id': 'SYS-WARN', 'severity': 'minor', 'explanation': warning,
                'finding_type': 'system', 'artifact_type': 'extraction'})
        usecase, sequence, classes = models.get('usecase'), models.get('sequence'), models.get('class')
        candidates = build_trace_links(requirements, usecase, sequence, classes) if models else []
        findings.extend(check_traceability(requirements, usecase, sequence, classes, candidates))
        obligations = trace_obligations(requirements, usecase, sequence, classes, candidates)
        uml_count = sum(len(model.get(key, [])) for model in models.values() for key in ('actors', 'use_cases', 'classes', 'messages'))
        scores = compute_scores(findings, candidates, len(requirements), uml_count,
            profile=run.input_snapshot['profile'], complete=not warnings, obligations=obligations)
        scores['details'].update(analysis_mode=run.input_snapshot['mode'], warnings=warnings)
        for finding in findings:
            if not finding.get('source_ref') and finding.get('requirement_id'):
                matches = [req for req in requirements if req.get('id') == finding['requirement_id']]
                if len(matches) == 1:
                    finding.update(source_ref=matches[0].get('source_ref'), source_spans=matches[0].get('source_spans'), element_id=matches[0].get('internal_id'))
        # The project row serializes publishing and lifecycle changes.
        from ..services.history import lock_project
        lock_project(db, project)
        publish_run(db, project, run, findings, candidates, scores, extracted, artifacts)
        db.commit()
    except Exception as error:
        db.rollback()
        project = db.get(Project, project_id)
        if project:
            project.status = 'error'
            project.analysis_error = 'Analysis could not finish. Check the uploaded documents and retry. Previous results have been preserved.'
            if run:
                run = db.get(AnalysisRun, run.id)
                if run and run.status in {'queued', 'running'}:
                    run.status, run.stage, run.finished_at = 'failed', 'failed', utcnow()
                    run.error_code, run.error_message = 'analysis_failed', project.analysis_error
                    audit(db, project, run.requested_by, 'analysis_failed', run_id=run.id)
            db.commit()
        logging.getLogger(__name__).warning('Analysis failed (%s)', type(error).__name__)
    finally:
        if context_token is not None:
            run_config.reset(context_token)
        db.close()
