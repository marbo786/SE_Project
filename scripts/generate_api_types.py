"""Generate dependency-free TypeScript schema types from this application's OpenAPI.
Run with .venv313/Scripts/python.exe scripts/generate_api_types.py [--check].
"""
from pathlib import Path
import json
import sys
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'backend'))
from app.main import app

def ts(schema):
    if '$ref' in schema:
        return schema['$ref'].split('/')[-1]
    if 'enum' in schema:
        return ' | '.join(json.dumps(value) for value in schema['enum'])
    if 'const' in schema:
        return json.dumps(schema['const'])
    for variant, join in [('anyOf', ' | '), ('oneOf', ' | '), ('allOf', ' & ')]:
        if variant in schema:
            return '(' + join.join(ts(s) for s in schema[variant]) + ')'
    kind = schema.get('type')
    if kind == 'array':
        return f'Array<{ts(schema.get("items", {}))}>'
    if kind == 'object' or 'properties' in schema:
        props = schema.get('properties', {})
        if not props:
            extra = schema.get('additionalProperties', {})
            return 'Record<string, ' + (ts(extra) if isinstance(extra, dict) else 'unknown') + '>'
        return '{\n' + '\n'.join('  ' + json.dumps(k) + ('' if k in schema.get('required', []) else '?') + ': ' + ts(v) + ';' for k, v in props.items()) + '\n}'
    return {'string': 'string', 'integer': 'number', 'number': 'number', 'boolean': 'boolean', 'null': 'null'}.get(kind, 'unknown')

schemas = app.openapi()['components']['schemas']
content = '// Generated from FastAPI OpenAPI by scripts/generate_api_types.py. Do not edit.\n\n'
content += '\n\n'.join(f'export type {name} = {ts(schema)}' for name, schema in sorted(schemas.items())) + '\n'
target = root / 'frontend/src/lib/generated-api.ts'
if '--check' in sys.argv:
    if not target.exists() or target.read_text(encoding='utf-8') != content:
        raise SystemExit('Generated API types are stale; run scripts/generate_api_types.py')
else:
    target.write_text(content, encoding='utf-8')
