import sys

with open('backend/config.yaml', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('trace_usecase_no_seq:\n    severity: minor', 'trace_usecase_no_seq:\n    severity: minor\n  trace_missing_class:\n    severity: major')
text = text.replace('rubric:', 'trace_jaccard_threshold: 0.3\n\nrubric:')

with open('backend/config.yaml', 'w', encoding='utf-8') as f:
    f.write(text)
