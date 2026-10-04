"""
UML Parser: converts PlantUML text into the internal UML model.
"""
import re
from typing import Dict, List, Optional


def detect_diagram_type(plantuml_text: str) -> str:
    """Detect diagram type from PlantUML source."""
    text_lower = plantuml_text.lower()
    # Check for use case characteristics
    if 'actor ' in text_lower or ':actor:' in text_lower or 'usecase' in text_lower or 'left to right direction' in text_lower:
        return 'usecase'
    # Check for class diagram characteristics
    if 'class ' in text_lower or 'interface ' in text_lower:
        return 'class'
    # Check for sequence diagram characteristics
    if 'participant' in text_lower or 'activate' in text_lower or 'deactivate' in text_lower:
        return 'sequence'
    if '-->' in plantuml_text or '->' in plantuml_text:
        return 'sequence'
    return 'unknown'


def parse_usecase_diagram(text: str) -> Dict:
    """Extract actors, use cases, and relationships."""
    actors = []
    use_cases = []
    relationships = []

    # Actors: lines like 'actor "Name" as X' or 'actor Name' or ':Name:'
    for m in re.finditer(r'actor\s+"?([^"\n\r]+?)"?(?:\s+as\s+(\w+))?$', text, re.MULTILINE | re.IGNORECASE):
        raw_name = m.group(1).strip()
        alias = m.group(2) or raw_name
        if not any(a['name'] == raw_name for a in actors):
            actors.append({"name": raw_name, "alias": alias})

    for m in re.finditer(r':([^:\n\r]+):', text):
        name = m.group(1).strip()
        if not any(a['name'] == name for a in actors):
            actors.append({"name": name, "alias": name})

    # Use cases: (Use Case Name) or usecase "Name" as X or usecase Name
    for m in re.finditer(r'\(([^)\n\r]+)\)', text):
        name = m.group(1).strip()
        if not any(uc['name'] == name for uc in use_cases):
            use_cases.append({"name": name})

    for m in re.finditer(r'usecase\s+"?([^"\n\r]+?)"?(?:\s+as\s+(\w+))?$', text, re.MULTILINE | re.IGNORECASE):
        name = m.group(1).strip()
        if not any(uc['name'] == name for uc in use_cases):
            use_cases.append({"name": name})

    # Relationships: arrows between elements, e.g. Actor --> (Use Case) or Actor -> UC
    # Match element identifier or ("...") or (...)
    elem_pattern = r'(\([^)]+\)|"[^"]+"|[a-zA-Z0-9_]+)'
    arrow_pattern = r'(-->|--|-\.->|\.\.|<--|->|<--)'
    rel_regex = re.compile(rf'{elem_pattern}\s*{arrow_pattern}\s*{elem_pattern}(?:\s*:\s*(.+))?', re.MULTILINE)

    for m in rel_regex.finditer(text):
        raw_source = m.group(1).strip().strip('"').strip('()').strip()
        rel = m.group(2)
        raw_target = m.group(3).strip().strip('"').strip('()').strip()
        label = m.group(4).strip() if m.group(4) else ''

        relationships.append({
            "source": raw_source,
            "relation": rel,
            "target": raw_target,
            "label": label
        })

    return {"type": "usecase", "actors": actors, "use_cases": use_cases, "relationships": relationships}


def parse_class_diagram(text: str) -> Dict:
    """Extract classes, attributes, operations, and associations."""
    classes = []
    associations = []

    # Class blocks
    for m in re.finditer(r'class\s+(\w+)(?:\s+\{([^}]*)\})?', text, re.DOTALL):
        class_name = m.group(1)
        body = m.group(2) or ''
        attributes = []
        operations = []
        for line in body.split('\n'):
            line = line.strip()
            if not line:
                continue
            if '()' in line or re.search(r'\w+\(', line):
                operations.append(line)
            else:
                attributes.append(line)
        classes.append({"name": class_name, "attributes": attributes, "operations": operations})

    # Associations
    for m in re.finditer(
        r'(\w+)\s*("[^"]*")?\s*(--|-->|<--|<-->|\.\.|o--|\*--)\s*("[^"]*")?\s*(\w+)',
        text
    ):
        source = m.group(1)
        src_mult = m.group(2)
        rel = m.group(3)
        tgt_mult = m.group(4)
        target = m.group(5)
        associations.append({
            "source": source,
            "target": target,
            "relation": rel,
            "source_multiplicity": src_mult,
            "target_multiplicity": tgt_mult
        })

    return {"type": "class", "classes": classes, "associations": associations}


def parse_sequence_diagram(text: str) -> Dict:
    """Extract participants and messages."""
    participants = []
    messages = []

    for m in re.finditer(r'participant\s+"?([^"\n]+?)"?(?:\s+as\s+(\w+))?$', text, re.MULTILINE | re.IGNORECASE):
        name = m.group(1).strip()
        alias = m.group(2) or name
        participants.append({"name": name, "alias": alias})

    for m in re.finditer(r'(\w+)\s*(->>?|-->>?|->|-->)\s*(\w+)\s*:\s*(.+)', text):
        source = m.group(1)
        arrow = m.group(2)
        target = m.group(3)
        message = m.group(4).strip()
        # Extract operation name (before parentheses if any)
        op_match = re.match(r'(\w+)\s*\(', message)
        operation = op_match.group(1) if op_match else message
        messages.append({
            "from": source, "to": target,
            "message": message, "operation": operation, "arrow": arrow
        })

    return {"type": "sequence", "participants": participants, "messages": messages}


def parse_plantuml(plantuml_text: str, diagram_type: Optional[str] = None) -> Dict:
    """Main entry: parse PlantUML into internal UML model."""
    if diagram_type is None:
        diagram_type = detect_diagram_type(plantuml_text)
    if diagram_type == 'usecase':
        return parse_usecase_diagram(plantuml_text)
    elif diagram_type == 'class':
        return parse_class_diagram(plantuml_text)
    elif diagram_type == 'sequence':
        return parse_sequence_diagram(plantuml_text)
    return {"type": "unknown", "raw": plantuml_text}
