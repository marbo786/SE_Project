"""Build a complete result in memory, then publish it in one transaction.

Previous findings survive a failed reanalysis. Immutable run history and durable
dispatch are introduced by the following schema/job milestones.
"""
from collections import defaultdict
import json
import logging
from pathlib import Path
from starlette.concurrency import run_in_threadpool
from ..core.config import get_settings
from ..core.database import SessionLocal
from ..core.uploads import validate_isolated
from ..models.project import Project
from ..models.artifact import Artifact
from ..models.finding import Finding
from ..models.traceability import TraceLink
from ..models.score import QualityScore
from .uml.parser import parse_plantuml
from .checks.srs_checks import run_all_srs_checks
from .checks.uml_checks import run_all_uml_checks
from .checks.llm_checks import check_testability, check_conflicts
from .checks.traceability_checks import build_trace_links, check_traceability, trace_obligations, requirement_key, element_key
from .scoring import compute_scores


def read_bounded(artifact):
    maximum = get_settings().MAX_UPLOAD_SIZE
    with Path(artifact.file_path).open("rb") as stream:
        content = stream.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError("Stored artifact exceeds the upload budget")
    return content


def extract_srs(artifact):
    return validate_isolated(read_bounded(artifact), f"source.{artifact.file_format}", extract=True)


def source_evidence(parsed, artifact):
    collections = ["requirements", "actors", "use_cases", "classes", "participants", "messages"]
    for collection in collections:
        for element in parsed.get(collection, []):
            element["artifact_id"] = artifact.id
            for span in element.get("source_spans", []):
                span["artifact_id"] = artifact.id
    return parsed


def endpoint_map(requirements, models):
    aliases = defaultdict(set)
    def remember(kind, key, labels):
        aliases[(kind, key)].add(key)
        for label in labels:
            if label:
                aliases[(kind, label)].add(key)
    for index, req in enumerate(requirements):
        remember("requirement", requirement_key(req, index), [req.get("id")])
    for model in models.values():
        for collection, kind in [("use_cases", "usecase"), ("classes", "class"), ("messages", "sequence"), ("participants", "sequence")]:
            for element in model.get(collection, []):
                remember(kind, element_key(element, "message" if collection == "messages" else "name"), [element.get("name"), element.get("alias"), element.get("message")])
    return aliases


async def run_analysis_pipeline(project_id, _db=None):
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if not project:
            return
        project.status, project.analysis_error = "analyzing", None
        db.commit()
        artifacts = db.query(Artifact).filter_by(project_id=project_id).all()
        srs = next((artifact for artifact in artifacts if artifact.artifact_type == "srs"), None)
        extracted, models, warnings = {}, {}, []
        parsed = await run_in_threadpool(extract_srs, srs) if srs else {"sections": [], "requirements": [], "warnings": ["Upload an SRS document before analysis."]}
        if srs:
            extracted[srs.id] = source_evidence(parsed, srs)
        warnings.extend(parsed.get("warnings", []))
        requirements = parsed["requirements"]
        if project.analysis_profile == "architecture":
            for kind in ["usecase", "class", "sequence"]:
                artifact = next((item for item in artifacts if item.artifact_type == f"uml_{kind}"), None)
                if not artifact:
                    warnings.append(f"The architecture profile requires a {kind} diagram.")
                    continue
                model = await run_in_threadpool(validate_isolated, read_bounded(artifact), "diagram.puml", extract=f"uml:{kind}:artifact-{artifact.id}")
                models[kind] = source_evidence(model, artifact)
                extracted[artifact.id] = models[kind]
                warnings.extend(f"{artifact.original_filename}: {message}" for message in model.get("warnings", []))
        findings = run_all_srs_checks(parsed)
        for kind, model in models.items():
            findings.extend(run_all_uml_checks(model, models.get("class") if kind == "sequence" else None))
        if project.analysis_mode == "ai" and requirements:
            try:
                findings.extend(await check_testability(requirements, db=db, project_id=project_id))
                findings.extend(await check_conflicts(requirements, db=db, project_id=project_id))
                from .repair import agentic_repair_loop
                await agentic_repair_loop(findings, db=db, project_id=project_id)
            except Exception as error:
                logging.getLogger(__name__).warning("Requested AI analysis failed (%s)", type(error).__name__)
                warnings.append("Requested AI checks did not finish. Deterministic results remain available; retry AI analysis later.")
        for warning in warnings:
            findings.append({"rule_id": "SYS-WARN", "severity": "minor", "explanation": warning,
                "finding_type": "system", "artifact_type": "extraction"})
        usecase, sequence, classes = models.get("usecase"), models.get("sequence"), models.get("class")
        candidates = build_trace_links(requirements, usecase, sequence, classes) if models else []
        findings.extend(check_traceability(requirements, usecase, sequence, classes, candidates))

        # Resolve old display-name endpoints only when the match is unambiguous.
        # Invalid decisions remain visible as stale instead of silently becoming evidence.
        aliases = endpoint_map(requirements, models)
        decisions = db.query(TraceLink).filter(TraceLink.project_id == project_id, TraceLink.status != "suggested").all()
        decision_map = {}
        for decision in decisions:
            source = aliases.get((decision.source_type, decision.source_id), set())
            target = aliases.get((decision.target_type, decision.target_id), set())
            decision.is_stale = len(source) != 1 or len(target) != 1
            if not decision.is_stale:
                decision.source_id, decision.target_id = next(iter(source)), next(iter(target))
                decision_map[(decision.source_type, decision.source_id, decision.target_type, decision.target_id)] = decision
        reviewed = []
        for candidate in candidates:
            key = tuple(candidate[field] for field in ["source_type", "source_id", "target_type", "target_id"])
            decision = decision_map.get(key)
            reviewed.append({**candidate, "status": decision.status if decision else "suggested"})
        obligations = trace_obligations(requirements, usecase, sequence, classes, candidates)
        reviewed_obligations = trace_obligations(requirements, usecase, sequence, classes, reviewed)
        for original, review in zip(obligations, reviewed_obligations):
            original["confirmed"] = review["confirmed"]
        uml_count = sum(len(model.get(collection, [])) for model in models.values() for collection in ["actors", "use_cases", "classes", "messages"])
        scores = compute_scores(findings, candidates, len(requirements), uml_count,
            profile=project.analysis_profile, complete=not warnings, obligations=obligations)
        scores["details"]["analysis_mode"] = project.analysis_mode
        scores["details"]["warnings"] = warnings

        # Publish only after parsing/checks/scoring succeeded. LLM logging may have
        # committed earlier, but it cannot delete or partially publish this report.
        db.query(Finding).filter_by(project_id=project_id).delete()
        db.query(TraceLink).filter_by(project_id=project_id, status="suggested").delete()
        finding_fields = {column.name for column in Finding.__table__.columns} - {"id", "project_id", "created_at"}
        for result in findings:
            if not result.get("source_ref") and result.get("requirement_id"):
                matches = [req for req in requirements if req.get("id") == result["requirement_id"]]
                if len(matches) == 1:
                    result.update(source_ref=matches[0].get("source_ref"), source_spans=matches[0].get("source_spans"), element_id=matches[0].get("internal_id"))
            db.add(Finding(project_id=project_id, **{key: value for key, value in result.items() if key in finding_fields}))
        for candidate in candidates:
            key = tuple(candidate[field] for field in ["source_type", "source_id", "target_type", "target_id"])
            if key in decision_map:
                decision = decision_map[key]
                for field in ["source_label", "target_label", "confidence", "origin", "evidence"]:
                    setattr(decision, field, candidate[field])
            else:
                db.add(TraceLink(project_id=project_id, **candidate))
        for artifact in artifacts:
            if artifact.id in extracted:
                artifact.extracted_content = json.dumps(extracted[artifact.id])
        score = db.query(QualityScore).filter_by(project_id=project_id).first()
        if not score:
            score = QualityScore(project_id=project_id); db.add(score)
        for key, value in scores.items():
            setattr(score, key, value)
        from datetime import datetime, timezone
        score.computed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        project.status = "done" if scores["details"]["complete"] else "partial"
        db.commit()
    except Exception as error:
        db.rollback()
        project = db.get(Project, project_id)
        if project:
            project.status = "error"
            project.analysis_error = "Analysis could not finish. Check the uploaded documents and retry. Previous results have been preserved."
            db.commit()
        logging.getLogger(__name__).warning("Analysis failed (%s)", type(error).__name__)
    finally:
        db.close()
