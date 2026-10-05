import re

with open('backend/app/llm/engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'["`\\]+Call LLM with caching, logging, and retry.["`\\]+', '"""Call LLM with caching, logging, and retry."""', text)

with open('backend/app/llm/engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
