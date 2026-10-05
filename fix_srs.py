import sys

with open('backend/app/pipeline/checks/srs_checks.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the two checks that don't have 'req' in scope
text = text.replace("'source_ref': req.get('source_ref')\n            })\n    return findings\n\n\ndef check_no_identifier",
"'source_ref': None\n            })\n    return findings\n\n\ndef check_no_identifier")

text = text.replace("'source_ref': req.get('source_ref')\n        }]\n    return []",
"'source_ref': None\n        }]\n    return []")

with open('backend/app/pipeline/checks/srs_checks.py', 'w', encoding='utf-8') as f:
    f.write(text)
