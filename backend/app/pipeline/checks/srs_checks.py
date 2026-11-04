"""
Deterministic SRS requirement checks.
Each check returns a list of finding dicts.
"""
import re
from collections import Counter
from typing import List, Dict
from ...core.config import get_yaml_config
from ..srs.parser import classification


def check_ambiguous_words(requirements: List[Dict]) -> List[Dict]:
    """FR-401: Flag requirements with ambiguous terms."""
    config = get_yaml_config()
    lexicon = config.get('rules', {}).get('ambiguous_words', {}).get('lexicon', [])
    severity = config.get('rules', {}).get('ambiguous_words', {}).get('severity', 'major')
    findings = []
    for req in requirements:
        text = req.get('text', '')
        found = [w for w in lexicon if re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', text, re.IGNORECASE)]
        if found:
            findings.append({
                'rule_id': 'FR-401',
                'severity': severity,
                'quoted_text': text,
                'explanation': f'Ambiguous term(s) found: {found}. Use measurable, specific language.',
                'requirement_id': req.get('id'),
                'finding_type': 'deterministic',
                'artifact_type': 'srs',
                'source_ref': req.get('source_ref')
            })
    return findings


def check_multiple_shall(requirements: List[Dict]) -> List[Dict]:
    """FR-402: Flag requirements with more than one 'shall' (non-atomic)."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('multiple_shall', {}).get('severity', 'major')
    findings = []
    for req in requirements:
        text = req.get('text', '')
        count = len(re.findall(r'\b(?:shall|must)\b', text, re.IGNORECASE))
        if count > 1:
            findings.append({
                'rule_id': 'FR-402',
                'severity': severity,
                'quoted_text': text,
                'explanation': f'Requirement contains {count} normative verbs (shall/must). Review whether it describes separate obligations.',
                'requirement_id': req.get('id'),
                'finding_type': 'deterministic',
                'artifact_type': 'srs',
                'source_ref': req.get('source_ref')
            })
    return findings


def check_missing_sections(sections: List[str]) -> List[Dict]:
    """FR-405: Flag missing IEEE-template sections."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('missing_section', {}).get('severity', 'minor')
    expected = config.get('expected_sections', [])
    findings = []
    sections_lower = [s.lower() for s in sections]
    for expected_section in expected:
        expected_name = re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', expected_section.lower())
        matched = any(expected_name in re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', s) for s in sections_lower) if expected_name else any(re.match(re.escape(expected_section.lower()) + r'(?![\d.])', s) for s in sections_lower)
        if not matched:
            findings.append({
                'rule_id': 'FR-405',
                'severity': severity,
                'quoted_text': None,
                'explanation': f'Missing expected SRS section: "{expected_section}".',
                'requirement_id': None,
                'finding_type': 'deterministic',
                'artifact_type': 'srs',
                'source_ref': None
            })
    return findings


def check_no_identifier(requirements: List[Dict]) -> List[Dict]:
    """FR-409: Flag requirements without identifiers."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('no_identifier', {}).get('severity', 'major')
    findings = []
    for req in requirements:
        if not req.get('id'):
            findings.append({
                'rule_id': 'FR-409',
                'severity': severity,
                'quoted_text': req.get('text', '')[:200],
                'explanation': 'Requirement has no identifier (e.g., FR-101, NFR-01).',
                'requirement_id': None,
                'finding_type': 'deterministic',
                'artifact_type': 'srs',
                'source_ref': req.get('source_ref')
            })
    return findings


def check_duplicate_identifiers(requirements: List[Dict]) -> List[Dict]:
    """FR-410: Flag duplicate requirement identifiers."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('duplicate_identifier', {}).get('severity', 'critical')
    findings = []
    counts = Counter(req['id'].casefold() for req in requirements if req.get('id'))
    for req in requirements:
        req_id = req.get('id')
        if req_id:
            if counts[req_id.casefold()] > 1:
                findings.append({
                    'rule_id': 'FR-410',
                    'severity': severity,
                    'quoted_text': req.get('text', '')[:200],
                    'explanation': f'Requirement identifier "{req_id}" is used more than once.',
                    'requirement_id': req_id,
                    'finding_type': 'deterministic',
                    'artifact_type': 'srs',
                    'source_ref': req.get('source_ref'),
                    'source_spans': req.get('source_spans', []),
                    'element_id': req.get('internal_id')
                })
    return findings


def check_nfr_no_metric(requirements: List[Dict]) -> List[Dict]:
    """FR-411: Flag NFRs without numeric thresholds or units."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('nfr_no_metric', {}).get('severity', 'major')
    unit_pattern = re.compile(
        r'\d+(?:\.\d+)?\s*(?:milliseconds?|ms\b|seconds?|s\b|minutes?|hours?|days?|%|MB\b|GB\b|KB\b|TB\b|requests?|users?|concurrent|per\b|times?)', re.IGNORECASE
    )
    findings = []
    for req in requirements:
        subtype = req.get('subtype') or classification(req.get('text', ''), req.get('section', ''))['subtype']
        if req.get('class') == 'non_functional' and subtype in {'performance', 'availability'}:
            text = req.get('text', '')
            if not unit_pattern.search(text):
                findings.append({
                    'rule_id': 'FR-411',
                    'severity': severity,
                    'quoted_text': text,
                    'explanation': f'This {subtype} requirement needs a measurable acceptance threshold. Obtain the target from a stakeholder; do not invent it.',
                    'requirement_id': req.get('id'),
                    'finding_type': 'deterministic',
                    'artifact_type': 'srs',
                    'source_ref': req.get('source_ref'),
                    'source_spans': req.get('source_spans', []),
                    'element_id': req.get('internal_id')
                })
    return findings


def check_warn_no_shall(requirements: List[Dict]) -> List[Dict]:
    """FR-305: Warn if no 'shall' statements found."""
    if not requirements:
        return [{
            'rule_id': 'FR-305',
            'severity': 'major',
            'quoted_text': None,
            'explanation': 'No requirements were detected. Use shall/must statements or explicit identifiers, then verify the extracted text.',
            'requirement_id': None,
            'finding_type': 'deterministic',
            'artifact_type': 'srs'
        }]
    return []


def run_all_srs_checks(parsed: Dict) -> List[Dict]:
    """Run all deterministic SRS checks and return combined findings."""
    sections = parsed.get('sections', [])
    requirements = parsed.get('requirements', [])
    findings = []
    findings += check_warn_no_shall(requirements)
    findings += check_ambiguous_words(requirements)
    findings += check_multiple_shall(requirements)
    findings += check_missing_sections(sections)
    findings += check_no_identifier(requirements)
    findings += check_duplicate_identifiers(requirements)
    findings += check_nfr_no_metric(requirements)
    for finding in findings:
        matches = [req for req in requirements if finding.get('source_ref') and req.get('source_ref') == finding['source_ref']]
        if len(matches) == 1:
            finding['source_spans'] = matches[0].get('source_spans', [])
            finding['element_id'] = matches[0].get('internal_id')
    return findings
