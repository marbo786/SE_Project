import sys

with open('backend/tests/test_compare.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('client = TestClient(app)', '')
text = text.replace('def test_compare_versions():\n    app.dependency_overrides[get_db] = override_get_db', 'def test_compare_versions():\n    app.dependency_overrides[get_db] = override_get_db\n    client = TestClient(app)')

with open('backend/tests/test_compare.py', 'w', encoding='utf-8') as f:
    f.write(text)
