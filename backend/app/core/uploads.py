"""Private, bounded storage. Validate before publishing a new artifact pointer."""
from io import BytesIO
from pathlib import Path
import re
import uuid
import zipfile
import json
import subprocess
import sys
import os
import sysconfig
import pdfplumber
from docx import Document
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from .config import get_settings
from ..models.artifact import Artifact


async def read_upload(file):
    maximum = get_settings().MAX_UPLOAD_SIZE
    chunks, total = [], 0
    try:
        while chunk := await file.read(64 * 1024):
            total += len(chunk)
            if total > maximum:
                raise HTTPException(413, "File exceeds the 10 MB upload limit")
            chunks.append(chunk)
    finally:
        await file.close()
    if not total:
        raise HTTPException(400, "The uploaded file is empty")
    return b"".join(chunks)


def validate_document(content, filename):
    settings = get_settings()
    suffix = Path(filename or "").suffix.lower()
    try:
        if suffix == ".docx" and content.startswith(b"PK"):
            with zipfile.ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                names = set(archive.namelist())
                if len(entries) > 1000 or sum(e.file_size for e in entries) > settings.MAX_EXPANDED_SIZE:
                    raise ValueError("Document expands beyond the supported size")
                if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                    raise ValueError("Missing DOCX structure")
                for entry in entries:
                    if entry.flag_bits & 1 or entry.filename.lower().endswith(".bin"):
                        raise ValueError("Encrypted or embedded executable content is unsupported")
                    if entry.filename.endswith((".xml", ".rels")):
                        xml = archive.read(entry)
                        if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                            raise ValueError("XML entity declarations are unsupported")
            doc = Document(BytesIO(content))
            text = "\n".join([p.text for p in doc.paragraphs] + [cell.text for table in doc.tables for row in table.rows for cell in row.cells])
            format = "docx"
        elif suffix == ".pdf" and content.startswith(b"%PDF-"):
            with pdfplumber.open(BytesIO(content)) as pdf:
                if len(pdf.pages) > settings.MAX_DOCUMENT_PAGES:
                    raise ValueError("PDF exceeds the supported page count")
                pieces, size = [], 0
                for page in pdf.pages:
                    piece = page.extract_text() or ""
                    size += len(piece)
                    if size > settings.MAX_DOCUMENT_CHARACTERS:
                        raise ValueError("Extracted document text is too large")
                    pieces.append(piece)
                text = "\n".join(pieces)
            format = "pdf"
        else:
            raise ValueError("Upload a valid .docx or text-based .pdf file")
        if not text.strip():
            raise ValueError("No readable text found. Scanned PDFs need OCR before upload")
        if len(text) > settings.MAX_DOCUMENT_CHARACTERS:
            raise ValueError("Extracted document text is too large")
        return format
    except HTTPException:
        raise
    except Exception as exc:
        message = str(exc) if isinstance(exc, ValueError) else "The document is corrupt, encrypted, or unsupported"
        raise HTTPException(400, message) from exc


def validate_uml(content, filename):
    if Path(filename or "").suffix.lower() not in {".puml", ".plantuml", ".txt"}:
        raise HTTPException(400, "Use .puml, .plantuml, or .txt for a diagram")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "PlantUML must be UTF-8 text")
    if not text.strip() or "\x00" in text or len(text) > get_settings().MAX_DOCUMENT_CHARACTERS:
        raise HTTPException(400, "Diagram is empty, binary, or too large")
    if re.search(r"(?im)^\s*!|%(?:getenv|load_json|load_yaml|load_csv|file_exists)\s*\(", text):
        raise HTTPException(400, "PlantUML preprocessing and external resources are unsupported")
    if not re.search(r"\b(actor|usecase|class|participant|interface)\b", text) and "->" not in text and "<-" not in text:
        raise HTTPException(400, "No supported PlantUML elements were found")
    return "puml"


async def accept_upload(file, uml=False):
    filename = (file.filename or "document").replace("\\", "/").split("/")[-1][:200]
    content = await read_upload(file)
    format = await run_in_threadpool(validate_uml, content, filename) if uml else await run_in_threadpool(validate_isolated, content, filename)
    return content, format, filename


def validate_isolated(content, filename, *, extract=False):
    settings = get_settings()
    budgets = {key: getattr(settings, key) for key in ["MAX_DOCUMENT_PAGES", "MAX_DOCUMENT_CHARACTERS", "MAX_EXPANDED_SIZE", "PARSER_MEMORY_MB", "MAX_REQUIREMENTS", "MAX_UML_ELEMENTS"]}
    try:
        # A Windows venv launcher spawns a second interpreter; killing the launcher
        # alone leaves that child running. Execute the base interpreter directly.
        executable = getattr(sys, "_base_executable", sys.executable)
        environment = {**os.environ, "PYTHONPATH": sysconfig.get_path("purelib") + os.pathsep + os.environ.get("PYTHONPATH", "")}
        mode = extract if isinstance(extract, str) else "extract" if extract else "validate"
        result = subprocess.run([executable, "-m", "app.core.validate_document", filename, json.dumps(budgets), mode],
            input=content, capture_output=True, timeout=settings.PARSER_TIMEOUT_SECONDS,
            cwd=str(Path(__file__).resolve().parents[2]), env=environment, check=False)
        if result.returncode != 0:
            raise HTTPException(400, "Document validation exceeded its resource budget or failed")
        parsed = json.loads(result.stdout)
        if "error" in parsed:
            raise HTTPException(400, parsed["error"])
        return parsed["extraction"] if extract else parsed["format"]
    except subprocess.TimeoutExpired:
        raise HTTPException(400, "Document validation took too long. Reduce the document size or complexity")


def remove_unreferenced_file(db, file_path):
    root = Path(get_settings().UPLOAD_DIR).resolve()
    path = Path(file_path).resolve()
    if path.parent == root and not db.query(Artifact).filter_by(file_path=str(path)).first():
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass  # Retention maintenance retries orphan cleanup.


def store_artifact(db, project, kind, content, format, filename, *, revision=None,
                   expected_version=None, replace_id=None, append=False, commit=True):
    import hashlib
    from ..services.history import ensure_revision, edit_draft, audit
    from ..models.history import Requirement, UMLElement
    revision = revision or ensure_revision(db, project)
    expected_version = revision.edit_version if expected_version is None else expected_version
    edit_draft(db, project, revision, expected_version)
    artifacts = db.query(Artifact).filter_by(revision_id=revision.id)
    artifact = artifacts.filter_by(id=replace_id).first() if replace_id else None
    if replace_id and (not artifact or artifact.artifact_type != kind):
        raise HTTPException(404, "Artifact not found in this draft and type")
    if not append and not replace_id:
        artifact = artifacts.filter_by(artifact_type=kind).first()
    if not artifact and kind == "srs" and artifacts.filter_by(artifact_type="srs").first():
        raise HTTPException(409, "This draft already has an SRS. Select it explicitly for replacement.")
    if not artifact and artifacts.count() >= 20:
        raise HTTPException(409, "A revision supports up to 20 input files")
    root = Path(get_settings().UPLOAD_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{uuid.uuid4().hex}.{format}"
    old = artifact.file_path if artifact else None
    try:
        with path.open("xb") as output:
            output.write(content)
        # All derived draft data must be re-extracted after a source change.
        db.query(Requirement).filter_by(revision_id=revision.id).delete()
        db.query(UMLElement).filter_by(revision_id=revision.id).delete()
        revision.canonical_inputs, revision.extraction_confirmed = None, False
        if not artifact:
            artifact = Artifact(project_id=project.id, revision_id=revision.id, artifact_type=kind)
            db.add(artifact)
        # Replacing bytes creates new lineage; edits to extracted requirements use
        # explicit occurrence lineage instead of guessing from authored IDs.
        artifact.lineage_key = uuid.uuid4().hex
        artifact.content_hash, artifact.size_bytes = hashlib.sha256(content).hexdigest(), len(content)
        artifact.file_path, artifact.file_format = str(path), format
        artifact.original_filename, artifact.extracted_content = filename, None
        db.flush()
        audit(db, project, project.user_id, "artifact_uploaded", revision_id=revision.id, artifact_id=artifact.id, sha256=artifact.content_hash)
        if commit:
            db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    if commit and old:
        remove_unreferenced_file(db, old)
    return artifact
