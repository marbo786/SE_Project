import sys

with open('backend/app/pipeline/checks/llm_checks.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('from ...pipeline.redactor import redact_text', 'from ...pipeline.redactor import Redactor')

# Fix testability
old_test_loop = '''    reqs_for_llm = []
    for req in requirements:
        reqs_for_llm.append({
            'requirement_id': req.get('id', 'UNKNOWN'),
            'text': redact_text(req.get('text', ''))
        })'''
new_test_loop = '''    redactor = Redactor()
    reqs_for_llm = []
    for req in requirements:
        reqs_for_llm.append({
            'requirement_id': req.get('id', 'UNKNOWN'),
            'text': redactor.redact(req.get('text', ''))
        })'''
text = text.replace(old_test_loop, new_test_loop)

# Fix unredact testability
text = text.replace('explanation=res.reason,', 'explanation=redactor.unredact(res.reason),')

# Fix conflict
old_conf_loop = '''    reqs_for_llm = []
    for req in requirements:
        reqs_for_llm.append({
            'id': req.get('id', 'UNKNOWN'),
            'text': redact_text(req.get('text', ''))
        })'''
new_conf_loop = '''    redactor = Redactor()
    reqs_for_llm = []
    for req in requirements:
        reqs_for_llm.append({
            'id': req.get('id', 'UNKNOWN'),
            'text': redactor.redact(req.get('text', ''))
        })'''
text = text.replace(old_conf_loop, new_conf_loop)

# Fix unredact conflict
text = text.replace('explanation=conflict.description,', 'explanation=redactor.unredact(conflict.description),')

with open('backend/app/pipeline/checks/llm_checks.py', 'w', encoding='utf-8') as f:
    f.write(text)
