import sys
import re

with open('backend/app/pipeline/checks/llm_checks.py', 'r', encoding='utf-8') as f:
    text = f.read()

# I will just remove it by replacing it with nothing.
# Or better, just delete the function manually with regex or write a simple parser.
# generate_rewrites is the last function in the file.
idx = text.find('async def generate_rewrites')
if idx != -1:
    text = text[:idx]
    
with open('backend/app/pipeline/checks/llm_checks.py', 'w', encoding='utf-8') as f:
    f.write(text)
