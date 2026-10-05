import sys

with open('backend/app/pipeline/analyzer.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('from .checks.llm_checks import check_testability, check_conflicts, generate_rewrites', 'from .checks.llm_checks import check_testability, check_conflicts')

with open('backend/app/pipeline/analyzer.py', 'w', encoding='utf-8') as f:
    f.write(text)
