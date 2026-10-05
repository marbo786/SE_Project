import sys

with open('frontend/src/pages/ReportPage.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('className={px-2 py-0.5 text-xs rounded-full \}>', 'className={px-2 py-0.5 text-xs rounded-full \}>')

with open('frontend/src/pages/ReportPage.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
