"""Build and verify the two recording specifications with the application's parser."""
from pathlib import Path
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def build(version):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(.65)
    section.left_margin = section.right_margin = Inches(.8)
    normal = doc.styles['Normal']
    normal.font.name, normal.font.size = 'Calibri', Pt(11)
    normal.paragraph_format.space_after = Pt(5)
    for name in ['Title', 'Heading 1', 'Heading 2']:
        doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)
    doc.add_paragraph('Library lending specification', 'Title')
    doc.add_paragraph(f'Revision {version} | Recording example | Library lending team')
    headings = yaml.safe_load((ROOT / 'backend/config.yaml').read_text())['expected_sections']
    descriptions = {
        '1. Introduction': 'This specification covers catalog search and librarian-led lending. It supports review of requirements, design consistency and revision history.',
        '1.1': 'Purpose: define the behavior of the lending service for a small library.',
        '1.2': 'Scope: search the catalog, check a book, authenticate a session and record a loan. Returns and payments are outside this example.',
        '1.3': 'Terms: a book without a current loan is eligible for lending; a session identifies the signed-in librarian.',
        '2. Overall description': 'Members search titles. Librarians create loans. Catalog, LoanService, AuthService, Book and Loan are the design components.',
        '3. Use cases': 'Search catalog; record loan for an available book; authenticate user; reject unauthenticated loan request.',
        '6. External interface requirements': 'The librarian submits book and member identifiers. LoanService uses the session token and returns a loan record or a rejection.',
        '7. Data requirements': 'Book stores title, lending status and current loan identifier. Loan stores the book, librarian and due date.',
    }
    functional = [
        'FR-1 The Catalog shall search catalog entries by book title.',
        'FR-2 The LoanService shall record a loan for a book whose current loan identifier is empty.',
        'FR-3 The system shall authenticate user sessions.',
        'FR-4 The AuthService shall reject an unauthenticated loan request.',
        'FR-5 The Catalog shall search catalog titles and shall return identifiers.' if version == 1 else 'FR-5 The Catalog shall return search catalog titles with identifiers.',
        'FR-6 The system shall record loan due dates.',
    ]
    quality = [
        'NFR-1 The Catalog shall respond fast.' if version == 1 else 'NFR-1 The Catalog shall respond to search requests within 2 seconds for 20 concurrent users.',
        'NFR-2 The Catalog shall maintain service uptime.' if version == 1 else 'NFR-2 The Catalog shall maintain service uptime of 99% per calendar month.',
        'NFR-3 The AuthService shall encrypt stored session tokens using AES-256.',
    ]
    for heading in headings:
        if heading == '4. Functional requirements':
            doc.add_page_break()
        doc.add_heading(heading, level=2 if heading in {'1.1', '1.2', '1.3'} else 1)
        if heading == '4. Functional requirements':
            for requirement in functional:
                doc.add_paragraph(requirement)
        elif heading == '5. Non-functional requirements':
            for requirement in quality:
                doc.add_paragraph(requirement)
        else:
            doc.add_paragraph(descriptions[heading])
    target = ROOT / f'demo/library-srs-v{version}.docx'
    doc.save(target)
    return target


def verify():
    from app.pipeline.srs.parser import extract_from_docx
    from app.pipeline.checks.srs_checks import run_all_srs_checks
    from app.pipeline.uml.parser import parse_plantuml
    from app.pipeline.checks.uml_checks import run_all_uml_checks
    for version in (1, 2):
        extraction = extract_from_docx(str(build(version)))
        findings = run_all_srs_checks(extraction)
        assert not extraction['warnings'], extraction['warnings']
        assert len(extraction['requirements']) == 9
        assert all(req['class'] == 'functional' for req in extraction['requirements'] if req['id'].startswith('FR-'))
        assert not any(f['rule_id'] == 'FR-405' for f in findings)
        assert len(findings) == (4 if version == 1 else 0), findings
        print(f'v{version}: {len(extraction["requirements"])} requirements, {len(findings)} SRS findings')
        for finding in findings:
            print(f'  {finding["rule_id"]} {finding["requirement_id"]}: {finding["explanation"]}')
    models = {}
    for filename, kind in [('library_usecase', 'usecase'), ('library_class', 'class'), ('library_sequence', 'sequence'), ('library_sequence_fixed', 'sequence')]:
        model = parse_plantuml((ROOT / 'demo/diagrams' / (filename + '.puml')).read_text(), kind)
        assert not model.get('warnings'), (filename, model.get('warnings'))
        models[filename] = model
    for filename in ['library_usecase', 'library_class', 'library_sequence', 'library_sequence_fixed']:
        findings = run_all_uml_checks(models[filename], models['library_class'])
        print(filename, [(f['rule_id'], f['explanation']) for f in findings])
        assert len(findings) == (1 if filename == 'library_sequence' else 0), findings


if __name__ == '__main__':
    verify()
