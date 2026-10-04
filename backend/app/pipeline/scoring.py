"""
Scoring engine: computes weighted quality scores from findings.
"""
from typing import List, Dict
from ..core.config import get_yaml_config


SEVERITY_PENALTY = {
    'critical': 15,
    'major': 5,
    'minor': 2
}


def compute_scores(findings: List[Dict], trace_links: List[Dict]) -> Dict:
    """
    Compute requirements, UML, traceability, and overall scores.
    Uses rubric weights from config.yaml.
    """
    config = get_yaml_config()
    rubric = config.get('rubric', {'requirements': 40, 'uml': 30, 'traceability': 30})

    # Partition findings by artifact type
    srs_findings = [f for f in findings if f.get('artifact_type') == 'srs']
    uml_findings = [f for f in findings if f.get('artifact_type') == 'uml']
    trace_findings = [f for f in findings if f.get('artifact_type') == 'traceability']

    def penalty(finding_list: List[Dict]) -> float:
        total = 0.0
        for f in finding_list:
            total += SEVERITY_PENALTY.get(f.get('severity', 'minor'), 2)
        return total

    # Scores start at 100 and get deducted by penalties, min 0
    req_raw = max(0.0, 100.0 - penalty(srs_findings))
    uml_raw = max(0.0, 100.0 - penalty(uml_findings))
    trace_raw = max(0.0, 100.0 - penalty(trace_findings))

    # Scale to rubric weights
    req_weight = rubric.get('requirements', 40)
    uml_weight = rubric.get('uml', 30)
    trace_weight = rubric.get('traceability', 30)

    req_score = (req_raw / 100.0) * req_weight
    uml_score = (uml_raw / 100.0) * uml_weight
    trace_score = (trace_raw / 100.0) * trace_weight
    overall = req_score + uml_score + trace_score

    return {
        'requirements_score': round(req_score, 2),
        'uml_score': round(uml_score, 2),
        'traceability_score': round(trace_score, 2),
        'overall_score': round(overall, 2)
    }
