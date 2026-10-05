import os
import glob
import re

for filepath in glob.glob('backend/app/pipeline/checks/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple regex to inject source_ref into findings dicts
    # Look for 'artifact_type': 'srs' and replace with 'artifact_type': 'srs', 'source_ref': req.get('source_ref')
    # Be careful though, some checks don't have 'req' in scope (like check_missing_sections)
    
    # Manual replacements:
    if 'srs_checks.py' in filepath:
        content = content.replace(
            "'artifact_type': 'srs'\n            })",
            "'artifact_type': 'srs',\n                'source_ref': req.get('source_ref')\n            })"
        )
    elif 'llm_checks.py' in filepath:
        content = content.replace(
            "'artifact_type': 'srs',\n            }",
            "'artifact_type': 'srs',\n                'source_ref': original.get('source_ref')\n            }"
        )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
