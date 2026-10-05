import sys

with open('backend/tests/test_compare.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('test@ex.com', 'test_compare@ex.com')

with open('backend/tests/test_compare.py', 'w', encoding='utf-8') as f:
    f.write(text)
