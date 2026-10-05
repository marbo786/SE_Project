import sys

with open('backend/app/pipeline/srs/parser.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the broken string literals
text = text.replace('""\"', '\"\"\"')
text = text.replace('"\"\"', '\"\"\"')
text = text.replace('\"\"\"', '\"\"\"') # Just ensure they are """ 

# Wait, let's just do it directly:
if text.startswith('""\"\\n'):
    text = '"""\n' + text[4:]
if text.startswith('""\\n'):
    text = '"""\n' + text[3:]
if text.startswith('"\\"\\"\\n'):
    text = '"""\n' + text[4:]

text = text.replace('""\"Detect lines', '\"\"\"Detect lines')
text = text.replace('\'.""\"', '\'\"\"\"')

text = text.replace('""\"Find requirement', '\"\"\"Find requirement')
text = text.replace('REQ-001.""\"', 'REQ-001.\"\"\"')

with open('backend/app/pipeline/srs/parser.py', 'w', encoding='utf-8') as f:
    f.write(text)
