import os
import sys
import pytest
from docx import Document

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.pipeline.srs.parser import parse_srs
from app.pipeline.redactor import Redactor

def test_srs_parser_docx_features(tmp_path):
    # Create a dummy docx
    docx_path = tmp_path / "test.docx"
    doc = Document()
    
    # 1. Heading
    doc.add_paragraph("1. Introduction")
    
    # 2. Wrapped requirement
    doc.add_paragraph("FR-01 The system shall allow users")
    doc.add_paragraph("to login securely using their")
    doc.add_paragraph("email and password.")
    
    # 3. New section
    doc.add_paragraph("2. Requirements")
    
    # 4. ID without shall
    doc.add_paragraph("NFR-02 The system must respond in 500ms.")
    
    # 5. Table requirement
    table = doc.add_table(rows=1, cols=2)
    row = table.rows[0]
    row.cells[0].text = "FR-03"
    row.cells[1].text = "The system shall log out users."
    
    doc.save(docx_path)
    
    result = parse_srs(str(docx_path), "docx")
    
    reqs = result['requirements']
    assert len(reqs) == 3
    
    # FR-01 should be wrapped
    assert reqs[0]['id'] == 'FR-01'
    assert "to login securely" in reqs[0]['text']
    assert "email and password" in reqs[0]['text']
    assert "Paragraph 2" in reqs[0]['source_ref']
    
    # NFR-02 should be captured
    assert reqs[1]['id'] == 'NFR-02'
    assert "must respond" in reqs[1]['text']
    assert "Paragraph 6" in reqs[1]['source_ref']
    
    # Table req should be captured
    assert reqs[2]['id'] == 'FR-03'
    assert reqs[2]['text'] == "FR-03 The system shall log out users."


def test_table_order_headers_and_occurrence_identity(tmp_path):
    doc = Document()
    doc.add_heading("Functional requirements", 1)
    doc.add_paragraph("FR-1 The system shall create records.")
    table = doc.add_table(rows=3, cols=3)
    for cell, text in zip(table.rows[0].cells, ["ID", "Description", "Priority"]):
        cell.text = text
    for row, values in zip(table.rows[1:], [["FR-1", "The system must delete records.", "High"], ["", "The system shall list records.", "Low"]]):
        for cell, text in zip(row.cells, values):
            cell.text = text
    doc.add_heading("Security", 1)
    doc.add_paragraph("NFR-2 The system shall encrypt stored passwords.")
    path = tmp_path / "order.docx"; doc.save(path)
    result = parse_srs(str(path), "docx")
    requirements = result["requirements"]
    assert [r["id"] for r in requirements] == ["FR-1", "FR-1", None, "NFR-2"]
    assert len({r["internal_id"] for r in requirements}) == 4
    assert requirements[1]["section"] == "Functional requirements"
    assert requirements[-1]["section"] == "Security"
    assert "High" not in requirements[1]["text"]
    assert requirements[2]["source_spans"] == [{"kind": "table", "table": 1, "row": 3, "columns": [1, 2]}]
    assert parse_srs(str(path), "docx")["requirements"] == requirements


def test_normative_boundaries_and_independent_prose(tmp_path):
    doc = Document()
    doc.add_paragraph("We will use a shallow hierarchy.")
    doc.add_paragraph("The system must export records.")
    doc.add_paragraph("This paragraph explains the background.")
    doc.add_paragraph("FR-2 Record deletion requires authorization.")
    path = tmp_path / "boundaries.docx"; doc.save(path)
    requirements = parse_srs(str(path), "docx")["requirements"]
    assert len(requirements) == 2
    assert requirements[0]["text"] == "The system must export records."
    assert requirements[0]["id"] is None


def test_referenced_id_is_not_an_authored_id(tmp_path):
    doc = Document()
    doc.add_paragraph("The system shall implement the flow described by FR-10.")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Description"; table.cell(0, 1).text = "ID"
    table.cell(1, 0).text = "The system must save."; table.cell(1, 1).text = "FR-2"
    path = tmp_path / "identifiers.docx"; doc.save(path)
    requirements = parse_srs(str(path), "docx")["requirements"]
    assert [requirement["id"] for requirement in requirements] == [None, "FR-2"]


def test_merged_table_cells_are_not_duplicated(tmp_path):
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "FR-1 The system shall save records."
    path = tmp_path / "merged.docx"; doc.save(path)
    requirements = parse_srs(str(path), "docx")["requirements"]
    assert len(requirements) == 1
    assert requirements[0]["text"].count("FR-1") == 1


def test_requirement_budget(tmp_path, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "MAX_REQUIREMENTS", 1)
    doc = Document()
    doc.add_paragraph("The system shall save.")
    doc.add_paragraph("The system shall delete.")
    path = tmp_path / "many.docx"; doc.save(path)
    with pytest.raises(ValueError, match="requirement count"):
        parse_srs(str(path), "docx")


def test_pdf_page_break_and_repeated_header(tmp_path):
    from tests.pdf_fixture import text_pdf
    path = tmp_path / "pages.pdf"
    path.write_bytes(text_pdf([["Course specification", "FR-1 The system shall allow users", "Page 1"],
        ["Course specification", "to export their records.", "FR-2 The system must delete a record.", "Page 2"]]))
    parsed = parse_srs(str(path), "pdf")
    assert len(parsed["requirements"]) == 2
    assert parsed["requirements"][0]["text"] == "FR-1 The system shall allow users to export their records."
    assert {span["page"] for span in parsed["requirements"][0]["source_spans"]} == {1, 2}


def test_pdf_without_text_is_explicit(tmp_path):
    from tests.pdf_fixture import text_pdf
    path = tmp_path / "blank.pdf"; path.write_bytes(text_pdf([[]]))
    parsed = parse_srs(str(path), "pdf")
    assert parsed["requirements"] == []
    assert any("OCR" in warning for warning in parsed["warnings"])
    
def test_redactor():
    text = "Contact john.doe@example.com or 555-123-4567. ID is 123456789."
    r = Redactor()
    redacted = r.redact(text)
    
    assert "john.doe" not in redacted
    assert "123456789" not in redacted
    assert "555-123-4567" not in redacted
    assert "[EMAIL_1]" in redacted
    assert "[PHONE_3]" in redacted
    assert "[ID_2]" in redacted
    
    unredacted = r.unredact(redacted)
    assert unredacted == text

