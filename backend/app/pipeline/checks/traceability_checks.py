"""
Traceability checks: validates links between requirements, use cases, and sequence diagrams.
"""
from typing import List, Dict
from ...core.config import get_yaml_config


def _sev(rule_key: str) -> str:
    config = get_yaml_config()
    return config.get('rules', {}).get(rule_key, {}).get('severity', 'major')


def build_trace_links(
    requirements: List[Dict],
    usecase_model: Dict,
    sequence_model: Dict = None
) -> List[Dict]:
    """
    Auto-generate suggested trace links by keyword matching between
    requirement text and use case names / sequence messages.
    Returns list of trace link dicts.
    """
    links = []
    use_cases = usecase_model.get('use_cases', []) if usecase_model else []
    seq_messages = sequence_model.get('messages', []) if sequence_model else []

    for req in requirements:
        req_text = req.get('text', '').lower()
        req_id = req.get('id', 'UNKNOWN')

        # Match to use cases
        for uc in use_cases:
            uc_name = uc['name'].lower()
            # Simple keyword overlap
            uc_words = set(uc_name.split())
            req_words = set(req_text.split())
            if len(uc_words & req_words) >= 2 or uc_name in req_text:
                links.append({
                    'source_type': 'requirement',
                    'source_id': req_id,
                    'target_type': 'usecase',
                    'target_id': uc['name'],
                    'status': 'suggested'
                })

        # Match to sequence operations
        for msg in seq_messages:
            op = msg.get('operation', '').lower()
            if op and op in req_text:
                links.append({
                    'source_type': 'requirement',
                    'source_id': req_id,
                    'target_type': 'sequence',
                    'target_id': msg.get('message', op),
                    'status': 'suggested'
                })

    return links


def check_traceability(
    requirements: List[Dict],
    usecase_model: Dict,
    sequence_model: Dict = None,
    existing_links: List[Dict] = None
) -> List[Dict]:
    """
    Run traceability checks and return findings.
    Checks FR-701 to FR-706.
    """
    findings = []
    links = existing_links or []

    use_cases = usecase_model.get('use_cases', []) if usecase_model else []
    seq_messages = sequence_model.get('messages', []) if sequence_model else []

    # Build sets of linked source/target IDs
    req_ids_with_uc = set()
    uc_ids_with_req = set()
    uc_ids_with_seq = set()
    seq_ids_with_uc = set()

    for link in links:
        if link['source_type'] == 'requirement' and link['target_type'] == 'usecase':
            req_ids_with_uc.add(link['source_id'])
            uc_ids_with_req.add(link['target_id'].lower())
        if link['source_type'] == 'usecase' and link['target_type'] == 'sequence':
            uc_ids_with_seq.add(link['source_id'].lower())
            seq_ids_with_uc.add(link['target_id'].lower())

    # FR-701: Requirements without any linked use case
    for req in requirements:
        req_id = req.get('id', 'UNKNOWN')
        if req_id not in req_ids_with_uc:
            findings.append({
                'rule_id': 'FR-701',
                'severity': _sev('trace_req_no_usecase'),
                'quoted_text': req.get('text', '')[:200],
                'explanation': f'Requirement "{req_id}" has no linked use case.',
                'requirement_id': req_id,
                'finding_type': 'deterministic',
                'artifact_type': 'traceability'
            })

    # FR-702: Use cases without any linked requirement
    for uc in use_cases:
        uc_name = uc['name'].lower()
        if uc_name not in uc_ids_with_req:
            findings.append({
                'rule_id': 'FR-702',
                'severity': _sev('trace_usecase_no_req'),
                'quoted_text': uc['name'],
                'explanation': f'Use case "{uc["name"]}" is not linked to any requirement.',
                'requirement_id': None,
                'finding_type': 'deterministic',
                'artifact_type': 'traceability'
            })

    # FR-703 / FR-704: Use case <-> sequence diagram traceability
    if sequence_model:
        for uc in use_cases:
            uc_name = uc['name'].lower()
            if uc_name not in uc_ids_with_seq:
                findings.append({
                    'rule_id': 'FR-703',
                    'severity': _sev('trace_usecase_no_seq'),
                    'quoted_text': uc['name'],
                    'explanation': f'Use case "{uc["name"]}" has no corresponding sequence diagram message.',
                    'requirement_id': None,
                    'finding_type': 'deterministic',
                    'artifact_type': 'traceability'
                })

    return findings
