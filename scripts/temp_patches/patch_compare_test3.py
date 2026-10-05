import sys

with open('backend/tests/test_compare.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('db.close()', 'db.close()\n    app.dependency_overrides.clear()')

with open('backend/tests/test_compare.py', 'w', encoding='utf-8') as f:
    f.write(text)
