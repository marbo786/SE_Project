import os
import sys
import io

# Setup path
sys.path.insert(0, os.path.abspath('backend'))
os.chdir(os.path.abspath('backend'))

from fastapi.testclient import TestClient
from app.main import app
from app.pipeline.analyzer import run_analysis_pipeline

client = TestClient(app)

print("--- Starting End-to-End System Test ---")

# 1. Health check
res = client.get('/health')
assert res.status_code == 200, f'Health failed: {res.text}'
print('[OK] 1. Health check passed')

# 2. Register Student
student_email = 'student_demo@test.com'
res = client.post('/auth/register', json={
    'name': 'Test Student',
    'email': student_email,
    'password': 'password123',
    'role': 'student'
})
if res.status_code == 400 and 'Email already registered' in res.text:
    print('  Student already registered')
else:
    assert res.status_code == 201, f'Student register failed: {res.text}'
    print('[OK] 2. Student registered')

# 3. Register Instructor
instructor_email = 'instructor_demo@test.com'
res = client.post('/auth/register', json={
    'name': 'Test Instructor',
    'email': instructor_email,
    'password': 'password123',
    'role': 'instructor'
})
if res.status_code == 400 and 'Email already registered' in res.text:
    print('  Instructor already registered')
else:
    assert res.status_code == 201, f'Instructor register failed: {res.text}'
    print('[OK] 3. Instructor registered')

# 4. Login Student
res = client.post('/auth/login', json={'email': student_email, 'password': 'password123'})
assert res.status_code == 200, f'Student login failed: {res.text}'
student_token = res.json()['access_token']
student_headers = {'Authorization': f'Bearer {student_token}'}
print('[OK] 4. Student login passed')

# 5. Login Instructor
res = client.post('/auth/login', json={'email': instructor_email, 'password': 'password123'})
assert res.status_code == 200, f'Instructor login failed: {res.text}'
instructor_token = res.json()['access_token']
instructor_headers = {'Authorization': f'Bearer {instructor_token}'}
print('[OK] 5. Instructor login passed')

# 6. Test /auth/me
res = client.get('/auth/me', headers=student_headers)
assert res.status_code == 200, f'/auth/me failed: {res.text}'
assert res.json()['email'] == student_email
print('[OK] 6. /auth/me passed')

# 7. Create Assignment (Instructor)
res = client.post('/assignments', headers=instructor_headers, json={
    'title': 'Semester Project Milestone 1',
    'course_code': 'CS325',
})
assert res.status_code in (200, 201), f'Create assignment failed: {res.text}'
assignment_id = res.json()['id']
print(f'âœ“ 7. Assignment created (ID: {assignment_id})')

# 8. Create Submission (Student)
res = client.post('/submissions', headers=student_headers, data={
    'assignment_id': assignment_id,
    'team_name': 'Alpha Squad',
    'member_names': '["Mohsin", "Hamza"]'
})
assert res.status_code == 201, f'Create submission failed: {res.text}'
submission_id = res.json()['id']
print(f'âœ“ 8. Submission created (ID: {submission_id})')

# 9. Upload SRS (.docx format)
from docx import Document
doc = Document()
doc.add_heading('1. Introduction', level=1)
doc.add_paragraph('This is a test SRS for quality analysis.')
doc.add_heading('4. Functional requirements', level=1)
doc.add_paragraph('FR-101: The system shall provide fast and user-friendly login capabilities.')
doc.add_paragraph('FR-102: The system shall authenticate users and shall notify admins.')
doc_stream = io.BytesIO()
doc.save(doc_stream)
doc_stream.seek(0)

res = client.post(
    f'/submissions/{submission_id}/upload-srs',
    headers=student_headers,
    files={'file': ('test_srs.docx', doc_stream.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
)
assert res.status_code == 200, f'Upload SRS failed: {res.text}'
print('[OK] 9. SRS uploaded successfully')

# 10. Upload UML Use Case Diagram
uml_content = '''@startuml
left to right direction
actor Student
actor Instructor
(Login)
(Submit SRS)
(Review Report)
Student --> (Login)
Student --> (Submit SRS)
Instructor --> (Login)
Instructor --> (Review Report)
@enduml'''

res = client.post(
    f'/submissions/{submission_id}/upload-uml',
    headers=student_headers,
    data={'diagram_type': 'usecase'},
    files={'file': ('usecase.puml', uml_content.encode('utf-8'), 'text/plain')}
)
assert res.status_code == 200, f'Upload UML failed: {res.text}'
print('[OK] 10. PlantUML use case uploaded successfully')

# 11. Run Analysis Pipeline
run_analysis_pipeline(submission_id)
print('[OK] 11. Analysis pipeline executed to completion')

# 12. Check Scores
res = client.get(f'/submissions/{submission_id}/score', headers=student_headers)
assert res.status_code == 200, f'Get score failed: {res.text}'
scores = res.json()
print(f'[OK] 12. Quality Scores: Overall={scores.get("overall_score")}, Req={scores.get("requirements_score")}, UML={scores.get("uml_score")}, Traceability={scores.get("traceability_score")}')

# 13. Check Findings
res = client.get(f'/findings/submission/{submission_id}', headers=student_headers)
assert res.status_code == 200, f'Get findings failed: {res.text}'
findings = res.json()
print(f'[OK] 13. Findings detected: {len(findings)} findings')

# 14. Check Traceability
res = client.get(f'/traceability/submission/{submission_id}', headers=student_headers)
assert res.status_code == 200, f'Get traceability failed: {res.text}'
links = res.json()
print(f'[OK] 14. Traceability links: {len(links)} links suggested')

# 15. Instructor makes decision on finding
if findings:
    finding_id = findings[0]['id']
    res = client.post(
        f'/findings/{finding_id}/decision',
        headers=instructor_headers,
        json={'status': 'accepted', 'comment': 'Valid finding, ambiguous language confirmed.'}
    )
    assert res.status_code == 201, f'Make decision failed: {res.text}'
    print('[OK] 15. Instructor decision recorded on finding')

# 16. Instructor updates trace link
if links:
    link_id = links[0]['id']
    res = client.patch(
        f'/traceability/{link_id}',
        headers=instructor_headers,
        json={'status': 'confirmed'}
    )
    assert res.status_code == 200, f'Update trace link failed: {res.text}'
    print('[OK] 16. Instructor confirmed trace link')

print('\nALL 16 INTEGRATION VERIFICATION STEPS PASSED SUCCESSFULLY!')

