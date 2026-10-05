import re

with open('backend/app/pipeline/analyzer.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix typo
text = text.replace('if not submission:', 'if not project:')

# 2. Add LLM error handling
# We can find `if requirements:` block easily.
pattern = r'(if requirements:\s*loop = asyncio\.new_event_loop\(\)\s*try:.*?)except Exception:\s*pass\s*# LLM failure is non-fatal(\s*finally:\s*loop\.close\(\))'

replacement = r'''has_llm_error = False
        \1except Exception as e:
                has_llm_error = True
                from .checks.llm_checks import LLMCheckError
                import logging
                logging.getLogger(__name__).warning(f"LLM failure: {e}")
                all_findings.append({
                    'rule_id': 'SYS-WARN', 'severity': 'minor', 'quoted_text': None,
                    'explanation': f'Warning: LLM check failed: {e}',
                    'requirement_id': None, 'finding_type': 'system', 'artifact_type': 'srs'
                })
        \2'''

text = re.sub(pattern, replacement, text, flags=re.DOTALL)

# 3. Fix project status
text = text.replace('project.status = "done"', 'project.status = "partial" if has_llm_error else "done"')

with open('backend/app/pipeline/analyzer.py', 'w', encoding='utf-8') as f:
    f.write(text)
