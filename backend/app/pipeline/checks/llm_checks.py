"""
LLM-assisted requirement checks: testability and conflict detection.
"""
import json
from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict
from ...llm.engine import call_llm, OutputValidationError
from ...pipeline.redactor import Redactor
from ...core.config import get_yaml_config

class LLMCheckError(ValueError):
    pass

class StrictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class TestabilityResult(StrictResponse):
    requirement_id: str
    requirement_text: Optional[str] = None
    testable: bool
    reason: Optional[str] = None

class TestabilityResponse(StrictResponse):
    results: List[TestabilityResult]

class ConflictResult(StrictResponse):
    req_id_1: str
    req_id_2: str
    explanation: str

class ConflictResponse(StrictResponse):
    conflicts: List[ConflictResult]

class RewriteResult(StrictResponse):
    requirement_id: str
    rewrite_suggestion: str

class RewriteResponse(StrictResponse):
    rewrites: List[RewriteResult]

TESTABILITY_SYSTEM_PROMPT = """You are an expert software requirements analyst.
Your task is to assess whether each given requirement is testable.
A testable requirement has a clear, specific, measurable expected behavior.
Return a JSON object with a key 'results' containing a list. Each item has:
- 'requirement_id': the exact supplied occurrence ID; return every supplied ID exactly once
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

async def _call_and_parse(system_prompt, user_prompt, model_cls, db=None, project_id=None, validate_refs=None):
    """Only cache responses that pass schema and occurrence validation."""
    def validate(text):
        parsed = model_cls.model_validate_json(text)
        if validate_refs:
            validate_refs(parsed)
        return parsed
    for attempt in range(2):
        try:
            response = await call_llm(system_prompt, user_prompt, db=db, project_id=project_id,
                retry=3, validator=validate, schema_version=f"{model_cls.__name__}:3")
            return validate(response)
        except (ValueError, OutputValidationError):
            if attempt == 1:
                raise LLMCheckError("ai_output_validation_failed") from None
    raise LLMCheckError("ai_output_validation_failed")


async def check_testability(requirements: List[Dict], db=None, project_id: int = None) -> List[Dict]:
    """FR-403: Use LLM to assess testability of each requirement."""
    config = get_yaml_config()
    severity = config.get('rules', {}).get('llm_not_testable', {}).get('severity', 'major')
    findings = []

    redactor = Redactor()
    reqs_for_llm = []
    for req in requirements:
        reqs_for_llm.append({
            'requirement_id': f'R{len(reqs_for_llm)}',
            'text': redactor.redact(req.get('text', ''))
        })

    user_prompt = f"Assess the testability of these requirements:\n\n{json.dumps(reqs_for_llm, indent=2)}"

    expected = {f"R{i}": req for i, req in enumerate(requirements)}
    def validate_refs(parsed):
        received = [result.requirement_id for result in parsed.results]
        if len(received) != len(expected) or set(received) != set(expected):
            raise LLMCheckError("ai_requirement_coverage_invalid")
    validated = await _call_and_parse(TESTABILITY_SYSTEM_PROMPT, user_prompt, TestabilityResponse,
                                      db, project_id, validate_refs)
    for result in validated.results:
        if not result.testable:
            req_id = result.requirement_id
            original = expected[req_id]
            findings.append({
                'rule_id': 'FR-403',
                'severity': severity,
                'quoted_text': original.get('text', result.requirement_text or ''),
                'explanation': f"Requirement is not testable: {redactor.unredact(result.reason) if result.reason else 'vague or unmeasurable'}",
                'requirement_id': original.get('id'),
                'source_ref': original.get('source_ref'),
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
            'id': f'R{len(reqs_for_llm)}',
            'text': redactor.redact(req.get('text', ''))
        })

    user_prompt = f"Identify any conflicting requirements in this list:\n\n{json.dumps(reqs_for_llm, indent=2)}"

    expected = {f"R{i}": req for i, req in enumerate(requirements)}
    def validate_refs(parsed):
        seen = set()
        for conflict in parsed.conflicts:
            pair = tuple(sorted((conflict.req_id_1, conflict.req_id_2)))
            if any(key not in expected for key in pair) or pair[0] == pair[1] or pair in seen:
                raise LLMCheckError("ai_conflict_reference_invalid")
            seen.add(pair)
    validated = await _call_and_parse(CONFLICT_SYSTEM_PROMPT, user_prompt, ConflictResponse,
                                      db, project_id, validate_refs)
    for conflict in validated.conflicts:
        findings.append({
            'rule_id': 'FR-404',
            'severity': severity,
            'quoted_text': expected[conflict.req_id_1].get('text', ''),
            'explanation': redactor.unredact(conflict.explanation) if conflict.explanation else 'Requirements conflict.',
            'requirement_id': expected[conflict.req_id_1].get('id'),
            'source_ref': expected[conflict.req_id_1].get('source_ref'),
            'finding_type': 'llm',
            'artifact_type': 'srs',
            'rewrite_suggestion': None
        })
    return findings

