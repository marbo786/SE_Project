import re

with open('backend/app/pipeline/checks/llm_checks.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace any malformed docstrings
text = text.replace('"\\"\\"FR-407: Generate rewrite suggestions for defective requirements."\\"\\"', '"""FR-407: Generate rewrite suggestions for defective requirements."""')
text = text.replace('`"\\"\\"FR-407: Generate rewrite suggestions for defective requirements.`"\\"\\"', '"""FR-407: Generate rewrite suggestions for defective requirements."""')
# Just blindly replace if the above exact match failed
text = re.sub(r'".*?FR-407.*?defective requirements.*?"', '"""FR-407: Generate rewrite suggestions for defective requirements."""', text)

with open('backend/app/pipeline/checks/llm_checks.py', 'w', encoding='utf-8') as f:
    f.write(text)
