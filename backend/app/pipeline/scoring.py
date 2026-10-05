"""
Scoring engine: computes weighted quality scores from findings.
"""
from typing import List, Dict
from ..core.config import get_yaml_config

def compute_scores(findings: List[Dict], trace_links: List[Dict], req_count: int, uml_count: int, trace_count: int) -> Dict:
    config = get_yaml_config()
    rubric = config.get('rubric', {'requirements': 40, 'uml': 30, 'traceability': 30})
    severity_penalties = config.get('severity_penalty', {'critical': 15, 'major': 5, 'minor': 2})

    srs_findings = [f for f in findings if f.get('artifact_type') == 'srs']
    uml_findings = [f for f in findings if f.get('artifact_type') == 'uml']
    trace_findings = [f for f in findings if f.get('artifact_type') == 'traceability']

    def penalty(finding_list: List[Dict]) -> float:
        return sum(severity_penalties.get(f.get('severity', 'minor'), 2) for f in finding_list)

    req_penalty = penalty(srs_findings)
    uml_penalty = penalty(uml_findings)
    trace_penalty = penalty(trace_findings)
    
    # Formula: 100 - (Total Penalty / Element Count) * 10
    req_raw = max(0.0, 100.0 - (req_penalty / max(1, req_count)) * 10)
    uml_raw = max(0.0, 100.0 - (uml_penalty / max(1, uml_count)) * 10)
    trace_raw = max(0.0, 100.0 - (trace_penalty / max(1, trace_count)) * 10)

    req_score = (req_raw / 100.0) * rubric.get('requirements', 40)
    uml_score = (uml_raw / 100.0) * rubric.get('uml', 30)
    trace_score = (trace_raw / 100.0) * rubric.get('traceability', 30)
    overall = req_score + uml_score + trace_score

    return {
        'requirements_score': round(req_score, 2),
        'uml_score': round(uml_score, 2),
        'traceability_score': round(trace_score, 2),
        'overall_score': round(overall, 2)
    }
