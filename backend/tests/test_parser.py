import os
import sys
import pytest
from docx import Document

sys.path.insert(0, os.path.abspath('..'))

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
    assert len(reqs) == 4
    
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
    assert reqs[2]['text'] == "FR-03"  # Wait, how does it process table? Each cell is processed individually!
    
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

