"""
Deterministic UML checks (use case, class, sequence diagrams).
"""
from typing import List, Dict
from ...core.config import get_yaml_config


def _sev(rule_key: str) -> str:
    config = get_yaml_config()
    return config.get('rules', {}).get(rule_key, {}).get('severity', 'major')


def check_usecase_diagram(uml_model: Dict) -> List[Dict]:
    findings = []
    actors = uml_model.get('actors', [])
    use_cases = uml_model.get('use_cases', [])
    relationships = uml_model.get('relationships', [])

    # Collect all connected names
    connected = set()
    for rel in relationships:
        connected.add(rel['source'].lower())
        connected.add(rel['target'].lower())

    # FR-601: Actors not connected to any use case
    for actor in actors:
        alias = actor.get('alias', actor['name']).lower()
        name = actor['name'].lower()
        if alias not in connected and name not in connected:
            findings.append({
                'rule_id': 'FR-601',
                'severity': _sev('uml_actor_disconnected'),
                'quoted_text': actor['name'],
                'explanation': f'Actor "{actor["name"]}" is not connected to any use case.',
                'requirement_id': None,
                'finding_type': 'deterministic',
                'artifact_type': 'uml'
            })

    # FR-602: Use cases not connected to any actor
    for uc in use_cases:
        uc_name = uc['name'].lower()
        if not any(uc_name in r['source'].lower() or uc_name in r['target'].lower() for r in relationships):
            findings.append({
                'rule_id': 'FR-602',
                'severity': _sev('uml_usecase_disconnected'),
                'quoted_text': uc['name'],
                'explanation': f'Use case "{uc["name"]}" is not connected to any actor.',
                'requirement_id': None,
                'finding_type': 'deterministic',
                'artifact_type': 'uml'
            })

    # FR-609: Duplicate element names
    names = [uc['name'].lower() for uc in use_cases]
    for i, name in enumerate(names):
        if names.count(name) > 1 and i == names.index(name):
            findings.append({
                'rule_id': 'FR-609',
                'severity': _sev('uml_duplicate_name'),
                'quoted_text': name,
                'explanation': f'Duplicate use case name: "{name}".',
                'requirement_id': None,
                'finding_type': 'deterministic',
                'artifact_type': 'uml'
            })
    return findings


def check_class_diagram(uml_model: Dict) -> List[Dict]:
    findings = []
    classes = uml_model.get('classes', [])
    associations = uml_model.get('associations', [])
    class_names = {c['name'].lower() for c in classes}

    for cls in classes:
        # FR-603: Empty classes
        if not cls.get('attributes') and not cls.get('operations'):
            findings.append({
                'rule_id': 'FR-603',
                'severity': _sev('uml_class_empty'),
                'quoted_text': cls['name'],
                'explanation': f'Class "{cls["name"]}" has no attributes or operations.',
                'requirement_id': None,
                'finding_type': 'deterministic',
                'artifact_type': 'uml'
            })

    for assoc in associations:
        # FR-604: Associations with no multiplicity
        if not assoc.get('source_multiplicity') and not assoc.get('target_multiplicity'):
            findings.append({
                'rule_id': 'FR-604',
                'severity': _sev('uml_assoc_no_multiplicity'),
                'quoted_text': f"{assoc['source']} -- {assoc['target']}",
                'explanation': f'Association between "{assoc["source"]}" and "{assoc["target"]}" has no multiplicity.',
                'requirement_id': None,
                'finding_type': 'deterministic',
                'artifact_type': 'uml'
            })
        # FR-605: Undefined classes in associations
        for endpoint in ['source', 'target']:
            ep = assoc.get(endpoint, '').lower()
            if ep and ep not in class_names:
                findings.append({
                    'rule_id': 'FR-605',
                    'severity': _sev('uml_undefined_class'),
                    'quoted_text': assoc.get(endpoint),
                    'explanation': f'Association refers to class "{assoc.get(endpoint)}" which is not defined in the diagram.',
                    'requirement_id': None,
                    'finding_type': 'deterministic',
                    'artifact_type': 'uml'
                })
    return findings


def check_sequence_diagram(uml_model: Dict, class_uml_model: Dict = None) -> List[Dict]:
    findings = []
    messages = uml_model.get('messages', [])

    # FR-606: Operations not defined in class diagram
    if class_uml_model:
        import re
        all_operations = set()
        for cls in class_uml_model.get('classes', []):
            for op in cls.get('operations', []):
                op_name = re.match(r'\w+', op.strip())
                if op_name:
                    all_operations.add(op_name.group(0).lower())

        for msg in messages:
            op = msg.get('operation', '').lower()
            if op and op not in all_operations:
                findings.append({
                    'rule_id': 'FR-606',
                    'severity': _sev('uml_op_not_in_class'),
                    'quoted_text': msg.get('message'),
                    'explanation': f'Message "{msg["message"]}" calls operation "{msg["operation"]}" which is not defined in the class diagram.',
                    'requirement_id': None,
                    'finding_type': 'deterministic',
                    'artifact_type': 'uml'
                })

    # FR-609: Duplicate participant names
    participants = uml_model.get('participants', [])
    names = [p['name'].lower() for p in participants]
    for i, name in enumerate(names):
        if names.count(name) > 1 and i == names.index(name):
            findings.append({
                'rule_id': 'FR-609',
                'severity': _sev('uml_duplicate_name'),
                'quoted_text': name,
                'explanation': f'Duplicate participant name: "{name}".',
                'requirement_id': None,
                'finding_type': 'deterministic',
                'artifact_type': 'uml'
            })
    return findings


def run_all_uml_checks(uml_model: Dict, class_model: Dict = None) -> List[Dict]:
    diagram_type = uml_model.get('type', 'unknown')
    if diagram_type == 'usecase':
        return check_usecase_diagram(uml_model)
    elif diagram_type == 'class':
        return check_class_diagram(uml_model)
    elif diagram_type == 'sequence':
        return check_sequence_diagram(uml_model, class_model)
    return []
