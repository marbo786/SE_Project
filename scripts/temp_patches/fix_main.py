import sys

with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('
', '\n')

with open('backend/app/main.py', 'w', encoding='utf-8') as f:
    f.write(text)
