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


def store_artifact(db, project, kind, content, format, filename):
    root = Path(get_settings().UPLOAD_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{uuid.uuid4().hex}.{format}"
    from ..models.project import Project
    claimed = db.query(Project).filter_by(id=project.id, status="pending").update({"status": "pending"})
    if not claimed:
        db.rollback()
        raise HTTPException(409, "Analysis has started; the upload was not saved")
    artifact = db.query(Artifact).filter_by(project_id=project.id, artifact_type=kind).first()
    old = Path(artifact.file_path).resolve() if artifact else None
    try:
        with path.open("xb") as output:
            output.write(content)
        if not artifact:
            artifact = Artifact(project_id=project.id, artifact_type=kind)
            db.add(artifact)
        artifact.file_path, artifact.file_format = str(path), format
        artifact.original_filename, artifact.extracted_content = filename, None
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    if old and old != path and old.parent == root:
        try:
            old.unlink(missing_ok=True)
        except OSError:
            pass  # An orphan is safe; never lose the newly committed upload.
