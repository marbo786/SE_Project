import re

with open('backend/app/pipeline/analyzer.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Completely regex it out
text = re.sub(r'["`\\]+Full analysis pipeline for a project.["`\\]+', '"""Full analysis pipeline for a project."""', text)

with open('backend/app/pipeline/analyzer.py', 'w', encoding='utf-8') as f:
    f.write(text)
