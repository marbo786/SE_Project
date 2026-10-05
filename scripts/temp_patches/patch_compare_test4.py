import sys

with open('backend/tests/test_compare.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('app.dependency_overrides[get_db] = override_get_db\n\nclient = TestClient(app)', 'client = TestClient(app)')
text = text.replace('def test_compare_versions():', 'def test_compare_versions():\n    app.dependency_overrides[get_db] = override_get_db')

with open('backend/tests/test_compare.py', 'w', encoding='utf-8') as f:
    f.write(text)
