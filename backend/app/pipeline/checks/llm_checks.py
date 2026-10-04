"""
LLM-assisted requirement checks: testability and conflict detection.
"""
import json
import re
from typing import List, Dict, Optional
from ...llm.engine import call_llm
from ...pipeline.redactor import redact_text
from ...core.config import get_yaml_config


TESTABILITY_SYSTEM_PROMPT = """You are an expert software requirements analyst.
Your task is to assess whether each given requirement is testable.
A testable requirement has a clear, specific, measurable expected behavior.
Return a JSON object with a key 'results' containing a list. Each item has:
- 'requirement_id': the ID of the requirement (or null if none)
- 'requirement_text': the text
- 'testable': true or false
- 'reason': brief explanation if not testable
Return ONLY valid JSON, no markdown, no extra text."""

CONFLICT_SYSTEM_PROMPT = """You are an expert software requirements analyst.
Your task is to identify pairs of conflicting requirements.
Two requirements conflict if they cannot both be satisfied simultaneously.
Return a JSON object with a key 'conflicts' containing a list. Each item has:
- 'req_id_1': first requirement ID
- 'req_id_2': second requirement ID
- 'explanation': why they conflict
Return ONLY valid JSON, no markdown, no extra text."""


async def check_testability(requirements: List[Dict], db=None, submission_id: int = None) -> List[Dict]:
    """FR-403: Use LLM to assess testability of each requirement."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('llm_not_testable', {}).get('severity', 'major')
    findings = []

    # Build redacted requirements list for the prompt
    reqs_for_llm = []
    for req in requirements:
        reqs_for_llm.append({
            'requirement_id': req.get('id', 'UNKNOWN'),
            'text': redact_text(req.get('text', ''))
        })

    user_prompt = f"Assess the testability of these requirements:\n\n{json.dumps(reqs_for_llm, indent=2)}"

    try:
        response_text = await call_llm(
            TESTABILITY_SYSTEM_PROMPT, user_prompt,
            db=db, submission_id=submission_id
        )
        # Parse JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            for result in data.get('results', []):
                if not result.get('testable', True):
                    req_id = result.get('requirement_id')
                    original = next((r for r in requirements if r.get('id') == req_id), {})
                    findings.append({
                        'rule_id': 'FR-403',
                        'severity': severity,
                        'quoted_text': original.get('text', result.get('requirement_text', '')),
                        'explanation': f"Requirement is not testable: {result.get('reason', 'vague or unmeasurable')}",
                        'requirement_id': req_id,
                        'finding_type': 'llm',
                        'artifact_type': 'srs',
                        'rewrite_suggestion': None
                    })
    except Exception as e:
        # Log error but don't fail the whole pipeline
        findings.append({
            'rule_id': 'FR-403',
            'severity': 'minor',
            'quoted_text': None,
            'explanation': f'LLM testability check failed: {str(e)}',
            'requirement_id': None,
            'finding_type': 'llm',
            'artifact_type': 'srs',
            'rewrite_suggestion': None
        })
    return findings


async def check_conflicts(requirements: List[Dict], db=None, submission_id: int = None) -> List[Dict]:
    """FR-404: Use LLM to detect conflicting requirements."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('llm_conflict', {}).get('severity', 'critical')
    findings = []

    reqs_for_llm = []
    for req in requirements:
        reqs_for_llm.append({
            'id': req.get('id', 'UNKNOWN'),
            'text': redact_text(req.get('text', ''))
        })

    user_prompt = f"Identify any conflicting requirements in this list:\n\n{json.dumps(reqs_for_llm, indent=2)}"

    try:
        response_text = await call_llm(
            CONFLICT_SYSTEM_PROMPT, user_prompt,
            db=db, submission_id=submission_id
        )
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            for conflict in data.get('conflicts', []):
                findings.append({
                    'rule_id': 'FR-404',
                    'severity': severity,
                    'quoted_text': f"{conflict.get('req_id_1')} vs {conflict.get('req_id_2')}",
                    'explanation': conflict.get('explanation', 'Requirements conflict.'),
                    'requirement_id': conflict.get('req_id_1'),
                    'finding_type': 'llm',
                    'artifact_type': 'srs',
                    'rewrite_suggestion': None
                })
    except Exception as e:
        findings.append({
            'rule_id': 'FR-404',
            'severity': 'minor',
            'quoted_text': None,
            'explanation': f'LLM conflict check failed: {str(e)}',
            'requirement_id': None,
            'finding_type': 'llm',
            'artifact_type': 'srs',
            'rewrite_suggestion': None
        })
    return findings
