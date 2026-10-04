"""
SRS Parser: extracts section hierarchy and requirements from DOCX and PDF.
"""
import re
import json
from typing import List, Dict, Optional, Tuple


def _is_section_heading(text: str) -> bool:
    """Detect lines like '4.3 Something' or '1. Introduction'."""
    return bool(re.match(r'^\d+(\.\d+)*\.?\s+\S', text.strip()))


def _extract_req_id(text: str) -> Optional[str]:
    """Find requirement identifiers like FR-101, NFR-05, REQ-001."""
    m = re.search(r'\b(FR|NFR|REQ|UC|R)-?\d+\b', text, re.IGNORECASE)
    return m.group(0).upper() if m else None


def _has_shall(text: str) -> bool:
    return 'shall' in text.lower()


def _classify_requirement(text: str, section: str) -> str:
    """Classify as functional or non-functional based on section and keywords."""
    nfr_keywords = ['performance', 'security', 'usability', 'reliability', 'maintainability',
                    'portability', 'compatibility', 'availability', 'scalab', 'cost']
    section_lower = section.lower()
    if 'non-functional' in section_lower or any(k in section_lower for k in nfr_keywords):
        return 'non_functional'
    if any(k in text.lower() for k in nfr_keywords):
        return 'non_functional'
    return 'functional'


def extract_from_docx(file_path: str) -> Dict:
    """Parse a DOCX and return section hierarchy + requirements."""
    from docx import Document
    doc = Document(file_path)
    sections = []
    requirements = []
    current_section = "Unknown"

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if _is_section_heading(text):
            current_section = text
            sections.append(text)
        if _has_shall(text):
            req_id = _extract_req_id(text)
            req_class = _classify_requirement(text, current_section)
            requirements.append({
                "id": req_id,
                "text": text,
                "section": current_section,
                "class": req_class
            })

    return {"sections": sections, "requirements": requirements}


def extract_from_pdf(file_path: str) -> Dict:
    """Parse a PDF and return section hierarchy + requirements."""
    import pdfplumber
    sections = []
    requirements = []
    current_section = "Unknown"

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if _is_section_heading(line):
                    current_section = line
                    sections.append(line)
                if _has_shall(line):
                    req_id = _extract_req_id(line)
                    req_class = _classify_requirement(line, current_section)
                    requirements.append({
                        "id": req_id,
                        "text": line,
                        "section": current_section,
                        "class": req_class
                    })

    return {"sections": sections, "requirements": requirements}


def parse_srs(file_path: str, file_format: str) -> Dict:
    if file_format == "pdf":
        return extract_from_pdf(file_path)
    return extract_from_docx(file_path)
