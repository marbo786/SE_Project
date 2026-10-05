"""
Traceability checks: validates links between requirements, use cases, sequence diagrams, and class diagrams.
"""
from typing import List, Dict, Set
import re
from ...core.config import get_yaml_config

STOPWORDS = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were', 'will', 'with', 'system', 'shall', 'must', 'user'}

def _sev(rule_key: str) -> str:
    config = get_yaml_config()
    return config.get('rules', {}).get(rule_key, {}).get('severity', 'major')

def _jaccard(set1: Set[str], set2: Set[str]) -> float:
    if not set1 and not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

def _get_content_words(text: str) -> Set[str]:
    words = re.findall(r'\w+', text.lower())
    return set(w for w in words if w not in STOPWORDS)

def build_trace_links(
    requirements: List[Dict],
    usecase_model: Dict,
    sequence_model: Dict = None,
    class_model: Dict = None
) -> List[Dict]:
    config = get_yaml_config()
    jaccard_threshold = config.get('trace_jaccard_threshold', 0.3)
    
    links = []
    use_cases = usecase_model.get('use_cases', []) if usecase_model else []
    seq_messages = sequence_model.get('messages', []) if sequence_model else []
    seq_participants = sequence_model.get('participants', []) if sequence_model else []
    classes = class_model.get('classes', []) if class_model else []

    # Map seq participants to class
    seq_to_class = {}
    for part in seq_participants:
        part_name = part['name']
        for cls in classes:
            if cls['name'].lower() == part_name.lower():
                seq_to_class[part_name] = cls['name']

    for req in requirements:
        req_text = req.get('text', '')
        req_id = req.get('id', 'UNKNOWN')
        req_words = _get_content_words(req_text)

        # Req -> Use Case
        for uc in use_cases:
            uc_name = uc['name']
            uc_words = _get_content_words(uc_name)
            if req_id in uc_name or _jaccard(req_words, uc_words) >= jaccard_threshold:
                links.append({'source_type': 'requirement', 'source_id': req_id, 'target_type': 'usecase', 'target_id': uc_name, 'status': 'suggested'})

        # Req -> Sequence
        for msg in seq_messages:
            msg_text = msg.get('message', '')
            msg_words = _get_content_words(msg_text)
            if req_id in msg_text or _jaccard(req_words, msg_words) >= jaccard_threshold:
                links.append({'source_type': 'requirement', 'source_id': req_id, 'target_type': 'sequence', 'target_id': msg_text, 'status': 'suggested'})

        # Req -> Class
        for cls in classes:
            cls_name = cls['name']
            cls_texts = cls_name + " " + " ".join(cls.get('attributes', [])) + " " + " ".join(cls.get('operations', []))
            cls_words = _get_content_words(cls_texts)
            if req_id in cls_texts or _jaccard(req_words, cls_words) >= jaccard_threshold:
                links.append({'source_type': 'requirement', 'source_id': req_id, 'target_type': 'class', 'target_id': cls_name, 'status': 'suggested'})

    # Use Case -> Sequence
    for uc in use_cases:
        uc_name = uc['name']
        uc_words = _get_content_words(uc_name)
        for msg in seq_messages:
            msg_text = msg.get('message', '')
            msg_words = _get_content_words(msg_text)
            if _jaccard(uc_words, msg_words) >= jaccard_threshold:
                links.append({'source_type': 'usecase', 'source_id': uc_name, 'target_type': 'sequence', 'target_id': msg_text, 'status': 'suggested'})

    # Sequence -> Class
    for part in seq_participants:
        part_name = part['name']
        for cls in classes:
            cls_name = cls['name']
            cls_words = _get_content_words(cls_name)
            part_words = _get_content_words(part_name)
            if cls_name.lower() == part_name.lower() or _jaccard(cls_words, part_words) >= jaccard_threshold:
                links.append({'source_type': 'sequence', 'source_id': part_name, 'target_type': 'class', 'target_id': cls_name, 'status': 'suggested'})

    msg_to_parts = {}
    for msg in seq_messages:
        msg_to_parts[msg.get('message')] = {msg.get('from'), msg.get('to')}
        
    for l in links:
        if l['source_type'] == 'usecase' and l['target_type'] == 'sequence':
            uc_id = l['source_id']
            msg_id = l['target_id']
            parts = msg_to_parts.get(msg_id, set())
            for part in parts:
                if part in seq_to_class:
                    cls_name = seq_to_class[part]
                    links.append({'source_type': 'usecase', 'source_id': uc_id, 'target_type': 'class', 'target_id': cls_name, 'status': 'suggested'})

    unique_links = []
    seen = set()
    for l in links:
        k = (l['source_type'], l['source_id'], l['target_type'], l['target_id'])
        if k not in seen:
            seen.add(k)
            unique_links.append(l)

    return unique_links

def check_traceability(
    requirements: List[Dict],
    usecase_model: Dict,
    sequence_model: Dict = None,
    class_model: Dict = None,
    existing_links: List[Dict] = None
) -> List[Dict]:
    findings = []
    links = existing_links or []

    use_cases = usecase_model.get('use_cases', []) if usecase_model else []
    seq_messages = sequence_model.get('messages', []) if sequence_model else []
    classes = class_model.get('classes', []) if class_model else []

    req_ids_with_uc = set()
    uc_ids_with_req = set()
    uc_ids_with_seq = set()
    seq_ids_with_uc = set()
    cls_ids_with_req = set()

    for link in links:
        if link.get('status') == 'rejected':
            continue
        
        st, si, tt, ti = link['source_type'], link['source_id'], link['target_type'], link['target_id']
        
        if st == 'requirement' and tt == 'usecase':
            req_ids_with_uc.add(si)
            uc_ids_with_req.add(ti.lower())
        if st == 'usecase' and tt == 'sequence':
            uc_ids_with_seq.add(si.lower())
            seq_ids_with_uc.add(ti.lower())
        if st == 'requirement' and tt == 'class':
            cls_ids_with_req.add(ti.lower())

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
                
    if class_model:
        for cls in classes:
            cls_name = cls['name'].lower()
            if cls_name not in cls_ids_with_req:
                findings.append({
                    'rule_id': 'FR-705',
                    'severity': _sev('trace_missing_class'),
                    'quoted_text': cls['name'],
                    'explanation': f'Class "{cls["name"]}" is not linked to any requirement.',
                    'requirement_id': None,
                    'finding_type': 'deterministic',
                    'artifact_type': 'traceability'
                })

    return findings
