with open('backend/app/pipeline/checks/traceability_checks.py', 'r', encoding='utf-8') as f:
    text = f.read()

if text.startswith('""\"\\n'):
    text = '"""\n' + text[4:]
elif text.startswith('""\\n'):
    text = '"""\n' + text[3:]
elif text.startswith('"\\"\\"\\n'):
    text = '"""\n' + text[4:]
elif text.startswith('\xef\xbb\xbf'):
    text = text[3:]
    if text.startswith('""\"\\n'):
        text = '"""\n' + text[4:]
    elif text.startswith('"\\"\\"\\n'):
        text = '"""\n' + text[4:]

# Remove BOM just in case it's there
text = text.replace('\ufeff', '')

if text.startswith('""\"'):
    text = '"""' + text[3:]
if text.startswith('"\\"\\"'):
    text = '"""' + text[4:]

with open('backend/app/pipeline/checks/traceability_checks.py', 'w', encoding='utf-8') as f:
    f.write(text)
