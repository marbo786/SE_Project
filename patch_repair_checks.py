import sys

with open('backend/app/pipeline/repair.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_check = '''                # Re-run deterministic checks on the rewrite
                dummy_req = [{'id': rid, 'text': rewrite, 'class': 'unknown', 'section': 'unknown'}]
                new_findings = run_all_srs_checks({'requirements': dummy_req, 'sections': []})
                
                # Filter out missing identifier or multiple shall if we want, 
                # but it's better to force the LLM to fix them.
                
                if not new_findings:'''

new_check = '''                # Re-run deterministic checks on the rewrite
                dummy_req = [{'id': rid, 'text': rewrite, 'class': 'unknown', 'section': 'unknown'}]
                new_findings = run_all_srs_checks({'requirements': dummy_req, 'sections': []})
                
                # Keep only requirement-level findings that apply to this req
                new_findings = [f for f in new_findings if f.get('requirement_id') == rid]
                
                if not new_findings:'''

text = text.replace(old_check, new_check)

with open('backend/app/pipeline/repair.py', 'w', encoding='utf-8') as f:
    f.write(text)
