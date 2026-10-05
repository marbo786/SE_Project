"""
Main analysis pipeline: orchestrates parsing, checking, traceability, scoring.
Runs as a background task with its own database session.
"""
import json
import asyncio
from typing import List, Dict
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.project import Project
from ..models.artifact import Artifact
from ..models.finding import Finding
from ..models.traceability import TraceLink
from ..models.score import QualityScore
from ..models.llm_log import LLMLog

from .srs.parser import parse_srs
from .uml.parser import parse_plantuml
from .checks.srs_checks import run_all_srs_checks
from .checks.uml_checks import run_all_uml_checks
from .checks.llm_checks import check_testability, check_conflicts, generate_rewrites
from .checks.traceability_checks import build_trace_links, check_traceability
from .scoring import compute_scores


def run_analysis_pipeline(project_id: int, _db=None) -> None:
    """
    Full analysis pipeline for a submission.
    Creates its own DB session so it works correctly as a BackgroundTask.
    The _db parameter is ignored (kept for backward compat with callers).
    """
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        project.status = "analyzing"
        db.commit()

        # Delete existing analysis data to prevent duplication on re-analysis
        db.query(Finding).filter(Finding.project_id == project_id).delete()
        db.query(TraceLink).filter(TraceLink.project_id == project_id, TraceLink.status == 'suggested').delete()
        db.query(LLMLog).filter(LLMLog.project_id == project_id).delete()
        db.query(QualityScore).filter(QualityScore.project_id == project_id).delete()
        db.commit()

        artifacts = db.query(Artifact).filter(Artifact.project_id == project_id).all()

        # Group artifacts by type
        srs_artifact = next((a for a in artifacts if a.artifact_type == 'srs'), None)
        usecase_artifact = next((a for a in artifacts if a.artifact_type == 'uml_usecase'), None)
        class_artifact = next((a for a in artifacts if a.artifact_type == 'uml_class'), None)
        sequence_artifact = next((a for a in artifacts if a.artifact_type == 'uml_sequence'), None)

        # ── Parse SRS ──────────────────────────────────────────────────────
        srs_parsed = {"sections": [], "requirements": []}
        if srs_artifact:
            srs_parsed = parse_srs(srs_artifact.file_path, srs_artifact.file_format)
            srs_artifact.extracted_content = json.dumps(srs_parsed)
            db.commit()

        requirements = srs_parsed.get('requirements', [])

        # ── Parse UML artifacts ────────────────────────────────────────────
        usecase_model = None
        class_model = None
        sequence_model = None

        if usecase_artifact:
            content = _read_artifact_content(usecase_artifact)
            usecase_model = parse_plantuml(content, 'usecase')
            usecase_artifact.extracted_content = json.dumps(usecase_model)
            db.commit()

        if class_artifact:
            content = _read_artifact_content(class_artifact)
            class_model = parse_plantuml(content, 'class')
            class_artifact.extracted_content = json.dumps(class_model)
            db.commit()

        if sequence_artifact:
            content = _read_artifact_content(sequence_artifact)
            sequence_model = parse_plantuml(content, 'sequence')
            sequence_artifact.extracted_content = json.dumps(sequence_model)
            db.commit()

        # ── Deterministic checks ──────────────────────────────────────────
        all_findings: List[Dict] = []
        all_findings += run_all_srs_checks(srs_parsed)

        if usecase_model:
            all_findings += run_all_uml_checks(usecase_model)
        if class_model:
            all_findings += run_all_uml_checks(class_model)
        if sequence_model:
            all_findings += run_all_uml_checks(sequence_model, class_model)

        # ── LLM checks (run async checks from sync context) ──────────────
        has_llm_error = False
        if requirements:
            loop = asyncio.new_event_loop()
            try:
                llm_findings = loop.run_until_complete(
                    check_testability(requirements, db=db, project_id=project_id)
                )
                all_findings += llm_findings
                conflict_findings = loop.run_until_complete(
                    check_conflicts(requirements, db=db, project_id=project_id)
                )
                all_findings += conflict_findings
                
                loop.run_until_complete(
                    generate_rewrites(all_findings, db=db, project_id=project_id)
                )
            except Exception as e:
                has_llm_error = True
                from .checks.llm_checks import LLMCheckError
                import logging
                logging.getLogger(__name__).warning(f"LLM failure: {e}")
                all_findings.append({
                    'rule_id': 'SYS-WARN', 'severity': 'minor', 'quoted_text': None,
                    'explanation': f'Warning: LLM check failed: {e}',
                    'requirement_id': None, 'finding_type': 'system', 'artifact_type': 'srs'
                })
        
            finally:
                loop.close()

        # ── Traceability ──────────────────────────────────────────────────
        trace_link_dicts: List[Dict] = []

        if usecase_model:
            trace_link_dicts = build_trace_links(requirements, usecase_model, sequence_model, class_model)
            
            # Fetch persistent links from DB (confirmed/rejected)
            persistent_links = db.query(TraceLink).filter(TraceLink.project_id == project_id).all()
            persistent_keys = {(l.source_type, l.source_id, l.target_type, l.target_id): l.status for l in persistent_links}
            
            final_links_for_check = []
            final_links_to_save = []
            
            # Incorporate newly suggested links if they don't exist
            for tl in trace_link_dicts:
                k = (tl['source_type'], tl['source_id'], tl['target_type'], tl['target_id'])
                if k not in persistent_keys:
                    final_links_for_check.append(tl)
                    final_links_to_save.append(tl)
                    
            # Incorporate persistent links for checking
            for l in persistent_links:
                final_links_for_check.append({
                    'source_type': l.source_type,
                    'source_id': l.source_id,
                    'target_type': l.target_type,
                    'target_id': l.target_id,
                    'status': l.status
                })
                
            trace_link_dicts = final_links_to_save  # Only save new ones
                
            trace_findings = check_traceability(requirements, usecase_model, sequence_model, class_model, final_links_for_check)
            all_findings += trace_findings

        # ── Save findings ─────────────────────────────────────────────────
        for fd in all_findings:
            finding = Finding(
                project_id=project_id,
                rule_id=fd['rule_id'],
                severity=fd['severity'],
                quoted_text=fd.get('quoted_text'),
                explanation=fd['explanation'],
                artifact_type=fd.get('artifact_type'),
                requirement_id=fd.get('requirement_id'),
                finding_type=fd.get('finding_type', 'deterministic'),
                rewrite_suggestion=fd.get('rewrite_suggestion')
            )
            db.add(finding)

        # ── Save trace links ──────────────────────────────────────────────
        for tl in trace_link_dicts:
            link = TraceLink(
                project_id=project_id,
                source_type=tl['source_type'],
                source_id=tl['source_id'],
                target_type=tl['target_type'],
                target_id=tl['target_id'],
                status='suggested'
            )
            db.add(link)

        db.commit()

        # ── Compute and save score ────────────────────────────────────────
        scores = compute_scores(all_findings, trace_link_dicts)
        existing_score = db.query(QualityScore).filter(QualityScore.project_id == project_id).first()
        if existing_score:
            existing_score.requirements_score = scores['requirements_score']
            existing_score.uml_score = scores['uml_score']
            existing_score.traceability_score = scores['traceability_score']
            existing_score.overall_score = scores['overall_score']
        else:
            score_obj = QualityScore(
                project_id=project_id,
                **scores
            )
            db.add(score_obj)

        project.status = "partial" if has_llm_error else "done"
        db.commit()

    except Exception as e:
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "error"
                db.commit()
        except Exception:
            pass
        raise e
    finally:
        db.close()


def _read_artifact_content(artifact: Artifact) -> str:
    """Read raw text content from an artifact file."""
    with open(artifact.file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

