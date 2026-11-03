"""Conservative extraction with occurrence identities and source spans.

Supported: DOCX body paragraphs/rows and single-column text PDFs. Unknown layouts
produce warnings; independent prose is never silently appended to a requirement.
"""
from collections import Counter
import hashlib
import re
from ...core.config import get_settings

REQ_ID = re.compile(r"\b(?:NFR|FR|REQ|UC|R)-?\d+\b", re.I)
NORMATIVE = re.compile(r"\b(?:shall|must)\b", re.I)


def _extract_req_id(text):
    match = REQ_ID.match(text.lstrip(" \t["))
    return match.group().upper() if match else None


def _starts_with_req_id(text):
    return bool(REQ_ID.match(text.lstrip(" \t[")))


def _is_section_heading(text):
    return bool(re.match(r"^\d+(?:\.\d+)*\.?\s+\S", text.strip())) and not NORMATIVE.search(text)


def _has_shall(text):
    return bool(NORMATIVE.search(text))


def classification(text, section):
    context = f"{section} {text}".lower()
    subtypes = {
        "performance": r"\b(performance|latency|throughput|response time|respond|concurrent|capacity)\b",
        "availability": r"\b(availability|uptime|available|recovery time|reliability)\b",
        "security": r"\b(security|encrypt|encryption|authorization|authentication|access control)\b",
        "usability": r"\b(usability|accessible|accessibility)\b",
        "maintainability": r"\b(maintainability|portability|compatibility)\b",
    }
    subtype = next((name for name, pattern in subtypes.items() if re.search(pattern, context)), None)
    authored = _extract_req_id(text) or ""
    explicit = authored.startswith("NFR") or bool(re.search(r"non[- ]functional", section, re.I))
    kind = "non_functional" if explicit or subtype else "functional"
    reason = "NFR identifier or section" if explicit else f"{subtype} vocabulary" if subtype else "Normative behavior statement"
    return {"class": kind, "subtype": subtype, "classification_reason": reason,
        "classification_confidence": "high" if explicit else "medium"}


def _classify_requirement(text, section):
    return classification(text, section)["class"]


class Extractor:
    def __init__(self):
        self.sections, self.requirements, self.warnings = [], [], []
        self.section, self.current = "Unknown", None
        self.characters = 0

    def accept(self, text, source_ref, span, *, heading=False, allow_wrap=False):
        text = " ".join(text.split())
        self.characters += len(text)
        if self.characters > get_settings().MAX_DOCUMENT_CHARACTERS:
            raise ValueError("Document exceeds the supported text budget")
        if not text:
            self.current = None
            return
        if heading or _is_section_heading(text):
            self.section = text
            self.sections.append(text)
            self.current = None
            return
        starts = _starts_with_req_id(text) or bool(NORMATIVE.search(text))
        continuation = (allow_wrap and self.current and not _starts_with_req_id(text)
            and not re.search(r"[.!?;:]$", self.current["text"])
            and (text[0].islower() or re.match(r"^(and|or|to|using|within)\b", text, re.I)))
        if continuation and (not starts or re.match(r"^(and|or)\b", text, re.I)):
            self.current["text"] += " " + text
            self.current["source_spans"].append(span)
            self.current.update(classification(self.current["text"], self.section))
            return
        if starts:
            identity = hashlib.sha256(f"{len(self.requirements)}:{source_ref}:{text}".encode()).hexdigest()[:16]
            self.current = {"id": _extract_req_id(text), "internal_id": f"req-{identity}",
                "text": text, "section": self.section, "source_ref": source_ref,
                "source_spans": [span], **classification(text, self.section)}
            self.requirements.append(self.current)
            if len(self.requirements) > get_settings().MAX_REQUIREMENTS:
                raise ValueError("Document exceeds the supported requirement count")
        else:
            self.current = None

    def result(self):
        if not self.requirements:
            self.warnings.append("No requirements found. Use shall/must statements or explicit requirement identifiers.")
        return {"parser_version": "srs-2", "sections": self.sections,
            "requirements": self.requirements, "warnings": list(dict.fromkeys(self.warnings))}


def extract_from_docx(file_path):
    from docx import Document
    from docx.text.paragraph import Paragraph
    from docx.table import Table
    document, out = Document(file_path), Extractor()
    paragraph_number = table_number = 0
    for block in document.element.body:
        if block.tag.endswith("}p"):
            paragraph_number += 1
            paragraph = Paragraph(block, document)
            style = paragraph.style.name.lower() if paragraph.style else ""
            out.accept(paragraph.text, f"Paragraph {paragraph_number}",
                {"kind": "paragraph", "paragraph": paragraph_number},
                heading=style.startswith("heading") or style == "title", allow_wrap=True)
        elif block.tag.endswith("}tbl"):
            table_number += 1
            out.current = None
            table = Table(block, document)
            id_column = statement_column = None
            for row_number, row in enumerate(table.rows, 1):
                cells, seen = [], set()
                for column, cell in enumerate(row.cells):
                    if cell._tc not in seen:
                        cells.append((column, cell.text.strip()))
                        seen.add(cell._tc)
                if row_number == 1:
                    for column, value in cells:
                        label = re.sub(r"[^a-z ]", "", value.lower()).strip()
                        if label in {"id", "identifier", "requirement id", "req id"}:
                            id_column = column
                        elif label in {"requirement", "statement", "description", "requirement description", "requirement statement"}:
                            statement_column = column
                    if statement_column is not None:
                        continue
                selected = [(column, value) for column, value in cells if statement_column is None or column in {id_column, statement_column}]
                if id_column is not None:
                    selected.sort(key=lambda item: item[0] != id_column)
                text = " ".join(value for _, value in selected if value)
                out.current = None  # Rows are independent records, including missing IDs.
                out.accept(text, f"Table {table_number}, Row {row_number}",
                    {"kind": "table", "table": table_number, "row": row_number,
                        "columns": [column + 1 for column, _ in selected]})
                if statement_column is None and len(cells) > 2 and out.current:
                    out.warnings.append(f"Table {table_number} has no recognized statement column; review its extracted rows.")
            out.current = None
    return out.result()


def extract_from_pdf(file_path):
    import pdfplumber
    out = Extractor()
    with pdfplumber.open(file_path) as pdf:
        if len(pdf.pages) > get_settings().MAX_DOCUMENT_PAGES:
            raise ValueError("PDF exceeds the supported page count")
        pages = [(page.extract_text() or "").splitlines() for page in pdf.pages]
        edges = Counter(line.strip() for lines in pages if lines for line in [lines[0], lines[-1]])
        for page_number, (page, lines) in enumerate(zip(pdf.pages, pages), 1):
            if not any(line.strip() for line in lines):
                out.warnings.append(f"Page {page_number} has no readable text; image-only content needs OCR.")
                continue
            words = page.extract_words()
            rows = {}
            for word in words:
                rows.setdefault(round(word["top"] / 4), []).append(word)
            wide_gaps = 0
            for row in rows.values():
                ordered = sorted(row, key=lambda word: word["x0"])
                if any(right["x0"] - left["x1"] > page.width * .15 for left, right in zip(ordered, ordered[1:])):
                    wide_gaps += 1
            if wide_gaps >= 4:
                out.warnings.append(f"Page {page_number} may contain columns or a table; verify reading order before relying on this analysis.")
            for line_number, line in enumerate(lines, 1):
                if line_number in {1, len(lines)} and re.fullmatch(r"(?:page\s+)?\d+(?:\s+of\s+\d+)?", line.strip(), re.I):
                    continue
                if (line_number in {1, len(lines)} and edges[line.strip()] > len(pages) / 2
                    and len(pages) > 1 and not _starts_with_req_id(line) and not NORMATIVE.search(line)):
                    continue
                out.accept(line, f"Page {page_number}, Line {line_number}",
                    {"kind": "pdf", "page": page_number, "line": line_number}, allow_wrap=True)
    return out.result()


def parse_srs(file_path, file_format):
    if file_format == "pdf":
        return extract_from_pdf(file_path)
    if file_format == "docx":
        return extract_from_docx(file_path)
    raise ValueError("Unsupported SRS format")
