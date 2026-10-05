import sys

with open('backend/app/pipeline/analyzer.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_save = '''        # ── Save findings ─────────────────────────────────────────────────
        for fd in all_findings:
            finding = Finding(
                project_id=project_id,
                rule_id=fd['rule_id'],
                severity=fd['severity'],
                quoted_text=fd.get('quoted_text'),
                explanation=fd['explanation'],
                artifact_type=fd.get('artifact_type'),
                requirement_id=fd.get('requirement_id'),
                finding_type=fd.get('finding_type', 'deterministic'),
                rewrite_suggestion=fd.get('rewrite_suggestion')
            )
            db.add(finding)'''

new_save = '''        # ── Save findings ─────────────────────────────────────────────────
        for fd in all_findings:
            finding = Finding(
                project_id=project_id,
                rule_id=fd['rule_id'],
                severity=fd['severity'],
                quoted_text=fd.get('quoted_text'),
                explanation=fd['explanation'],
                artifact_type=fd.get('artifact_type'),
                requirement_id=fd.get('requirement_id'),
                finding_type=fd.get('finding_type', 'deterministic'),
                rewrite_suggestion=fd.get('rewrite_suggestion'),
                rewrite_attempts=fd.get('rewrite_attempts', 0),
                rewrite_passed=fd.get('rewrite_passed', False)
            )
            db.add(finding)'''

text = text.replace(old_save, new_save)

with open('backend/app/pipeline/analyzer.py', 'w', encoding='utf-8') as f:
    f.write(text)
