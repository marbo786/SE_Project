import re
with open('test_e2e_flow.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('bio = io.BytesIO()()', 'bio = io.BytesIO()')
text = text.replace('docx_content = bio.getvalue()()', 'docx_content = bio.getvalue()')

with open('test_e2e_flow.py', 'w', encoding='utf-8') as f:
    f.write(text)
