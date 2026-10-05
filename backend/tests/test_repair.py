import pytest
from unittest.mock import patch, AsyncMock
from app.pipeline.repair import agentic_repair_loop

@pytest.mark.asyncio
async def test_agentic_repair_loop_retries():
    findings = [
        {
            'artifact_type': 'srs',
            'requirement_id': 'REQ-1',
            'quoted_text': 'The system shall be fast.',
            'explanation': 'Ambiguous term(s) found: [\'fast\']'
        }
    ]
    
    # We will mock call_llm to return a bad rewrite first, then a good rewrite.
    # Bad rewrite contains "quick", which is also in the ambiguous_words lexicon.
    # Good rewrite contains "process within 200ms".
    
    mock_responses = [
        '{"rewrite_suggestion": "The system shall be quick."}',
        '{"rewrite_suggestion": "The system shall process requests within 200ms."}'
    ]
    
    async def mock_call_llm(sys_prompt, user_prompt, db, project_id, retry):
        if not mock_responses:
            return '{"rewrite_suggestion": "Fallback"}'
        return mock_responses.pop(0)
        
    with patch('app.pipeline.repair.call_llm', new=mock_call_llm):
        with patch('app.pipeline.repair._get_llm_call_count', return_value=0):
            await agentic_repair_loop(findings, db=None, project_id=1)
            
    f = findings[0]
    assert f['rewrite_attempts'] == 2
    assert f['rewrite_passed'] is True
    assert f['rewrite_suggestion'] == "The system shall process requests within 200ms."

