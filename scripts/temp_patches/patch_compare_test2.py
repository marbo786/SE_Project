import sys

with open('backend/tests/test_compare.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('print("Login failed:", res.json())', 'print("Login failed:", res.json(), db.query(User).all())')

with open('backend/tests/test_compare.py', 'w', encoding='utf-8') as f:
    f.write(text)
