"""
LLM-assisted requirement checks: testability and conflict detection.
"""
import json
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, ValidationError
from ...llm.engine import call_llm
from ...pipeline.redactor import Redactor
from ...core.config import get_yaml_config

class LLMCheckError(Exception):
    pass

class TestabilityResult(BaseModel):
    requirement_id: Optional[str]
    requirement_text: Optional[str] = None
    testable: bool
    reason: Optional[str] = None

class TestabilityResponse(BaseModel):
    results: List[TestabilityResult]

class ConflictResult(BaseModel):
    req_id_1: str
    req_id_2: str
    explanation: str

class ConflictResponse(BaseModel):
    conflicts: List[ConflictResult]

class RewriteResult(BaseModel):
    requirement_id: str
    rewrite_suggestion: str

class RewriteResponse(BaseModel):
    rewrites: List[RewriteResult]

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

REWRITE_SYSTEM_PROMPT = """You are an expert software requirements analyst.
You will be given a list of defective requirements along with an explanation of their flaws (e.g., ambiguity, missing metrics, untestable, conflicts).
Your task is to generate a corrected, professional rewrite for each requirement that resolves the issue while preserving the original intent.
Return a JSON object with a key 'rewrites' containing a list. Each item has:
- 'requirement_id': the ID of the requirement
- 'rewrite_suggestion': the rewritten text
Return ONLY valid JSON, no markdown, no extra text."""

async def _call_and_parse(system_prompt: str, user_prompt: str, model_cls, db=None, project_id=None):
    """Call LLM, parse JSON strictly, and validate with Pydantic. Retries once on invalid output."""
    for attempt in range(2):
        try:
            response_text = await call_llm(
                system_prompt, user_prompt,
                db=db, project_id=project_id, retry=3
            )
            # Remove any markdown code blocks if the LLM leaked them
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            data = json.loads(response_text)
            validated = model_cls(**data)
            return validated
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == 1:
                raise LLMCheckError(f"LLM output validation failed: {str(e)}")
            # On first attempt failure, continue and retry (we rely on call_llm retries internally, 
            # but to bypass a bad cache we should ideally clear it, but here we just try one more time)
            pass
    raise LLMCheckError("LLM output validation failed after 2 attempts")


async def check_testability(requirements: List[Dict], db=None, project_id: int = None) -> List[Dict]:
    """FR-403: Use LLM to assess testability of each requirement."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('llm_not_testable', {}).get('severity', 'major')
    findings = []

    redactor = Redactor()
    reqs_for_llm = []
    for req in requirements:
        reqs_for_llm.append({
            'requirement_id': req.get('id', 'UNKNOWN'),
            'text': redactor.redact(req.get('text', ''))
        })

    user_prompt = f"Assess the testability of these requirements:\n\n{json.dumps(reqs_for_llm, indent=2)}"

    validated = await _call_and_parse(TESTABILITY_SYSTEM_PROMPT, user_prompt, TestabilityResponse, db, project_id)
    
    for result in validated.results:
        if not result.testable:
            req_id = result.requirement_id
            original = next((r for r in requirements if r.get('id') == req_id), {})
            findings.append({
                'rule_id': 'FR-403',
                'severity': severity,
                'quoted_text': original.get('text', result.requirement_text or ''),
                'explanation': f"Requirement is not testable: {redactor.unredact(result.reason) if result.reason else 'vague or unmeasurable'}",
                'requirement_id': req_id,
                'finding_type': 'llm',
                'artifact_type': 'srs',
                'rewrite_suggestion': None
            })
    return findings


async def check_conflicts(requirements: List[Dict], db=None, project_id: int = None) -> List[Dict]:
    """FR-404: Use LLM to detect conflicting requirements."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('llm_conflict', {}).get('severity', 'critical')
    findings = []

    redactor = Redactor()
    reqs_for_llm = []
    for req in requirements:
        reqs_for_llm.append({
            'id': req.get('id', 'UNKNOWN'),
            'text': redactor.redact(req.get('text', ''))
        })

    user_prompt = f"Identify any conflicting requirements in this list:\n\n{json.dumps(reqs_for_llm, indent=2)}"

    validated = await _call_and_parse(CONFLICT_SYSTEM_PROMPT, user_prompt, ConflictResponse, db, project_id)
    
    for conflict in validated.conflicts:
        findings.append({
            'rule_id': 'FR-404',
            'severity': severity,
            'quoted_text': f"{conflict.req_id_1} vs {conflict.req_id_2}",
            'explanation': redactor.unredact(conflict.explanation) if conflict.explanation else 'Requirements conflict.',
            'requirement_id': conflict.req_id_1,
            'finding_type': 'llm',
            'artifact_type': 'srs',
            'rewrite_suggestion': None
        })
    return findings

