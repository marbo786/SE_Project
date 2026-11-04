"""Canonical extraction is editable only before sealing a revision."""
from copy import deepcopy
from fastapi import HTTPException
from ..core.uploads import validate_isolated
from ..models.artifact import Artifact
from .history import artifact_manifest, digest, persist_elements


def read_bounded(artifact):
    from pathlib import Path
    from ..core.config import get_settings
    maximum = get_settings().MAX_UPLOAD_SIZE
    with Path(artifact.file_path).open('rb') as stream:
        content = stream.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError('Stored artifact exceeds the upload budget')
    if artifact.content_hash:
        import hashlib
        if hashlib.sha256(content).hexdigest() != artifact.content_hash:
            raise ValueError('Stored artifact checksum mismatch')
    return content


def source_evidence(parsed, artifact):
    for collection in ('requirements', 'actors', 'use_cases', 'classes', 'participants', 'messages'):
        for element in parsed.get(collection, []):
            element['artifact_id'] = artifact.id
            for span in element.get('source_spans', []):
                span['artifact_id'] = artifact.id
            if collection == 'requirements':
                element.setdefault('lineage_key', digest([artifact.lineage_key or f'artifact-{artifact.id}', element['internal_id']]))
                element.setdefault('original_text', element['text'])
    return parsed


def extract_artifact(artifact):
    kind = artifact.artifact_type
    mode = True if kind == 'srs' else f"uml:{kind.removeprefix('uml_')}:{artifact.lineage_key or f'artifact-{artifact.id}'}"
    return source_evidence(validate_isolated(read_bounded(artifact), f'source.{artifact.file_format}', extract=mode), artifact)


def extract_draft(db, revision):
    inputs = {'artifacts': {}, 'edits': []}
    for artifact in db.query(Artifact).filter_by(revision_id=revision.id).order_by(Artifact.id):
        artifact_manifest(artifact)
        inputs['artifacts'][str(artifact.id)] = extract_artifact(artifact)
    revision.canonical_inputs, revision.extraction_confirmed = inputs, False
    persist_elements(db, revision)
    return inputs


def correct_requirement(db, revision, element_key, changes):
    inputs = deepcopy(revision.canonical_inputs)
    if not inputs:
        raise HTTPException(409, 'Extract this draft before correcting requirements')
    matches = [req for extraction in inputs['artifacts'].values() for req in extraction.get('requirements', []) if req['internal_id'] == element_key]
    if len(matches) != 1:
        raise HTTPException(404, 'Requirement occurrence not found')
    requirement = matches[0]
    for field, value in changes.items():
        if field == 'text' and not value.strip():
            raise HTTPException(422, 'Requirement text cannot be empty')
        requirement[field] = value
    # Keep a minimal effective-change list, independent of artifact database IDs.
    edits = {item['lineage_key']: item for item in inputs.get('edits', [])}
    edits[requirement['lineage_key']] = {k: requirement.get(k) for k in ('lineage_key', 'text', 'id', 'class', 'subtype')}
    inputs['edits'] = sorted(edits.values(), key=lambda item: item['lineage_key'])
    revision.canonical_inputs, revision.extraction_confirmed = inputs, False
    persist_elements(db, revision)
    return requirement


def merge_models(extractions, artifacts):
    """Preserve scoped diagram IDs when more than one diagram has the same type."""
    models = {}
    for artifact in artifacts:
        if not artifact.artifact_type.startswith('uml_'):
            continue
        model = extractions.get(str(artifact.id))
        if not model:
            continue
        kind = artifact.artifact_type.removeprefix('uml_')
        target = models.setdefault(kind, {'type': kind, 'diagram_type': kind, 'warnings': []})
        for key, value in model.items():
            if isinstance(value, list):
                target.setdefault(key, []).extend(value)
    return models
