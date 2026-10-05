import json
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from ..llm.engine import call_llm
from ..models.llm_log import LLMLog
from ..core.config import get_yaml_config
from pydantic import BaseModel
from .checks.srs_checks import run_all_srs_checks

class SingleRewriteResponse(BaseModel):
    rewrite_suggestion: str

REPAIR_SYSTEM_PROMPT = '''
You are an expert Requirements Engineer. Your job is to rewrite a single defective software requirement so that it perfectly resolves all listed flaws.
Output valid JSON only with this exact schema:
{
  "rewrite_suggestion": "The rewritten requirement text"
}
'''

def _get_llm_call_count(db: Session, project_id: int) -> int:
    if not db:
        return 0
    return db.query(LLMLog).filter(LLMLog.project_id == project_id, LLMLog.cache_hit == 'false').count()

async def agentic_repair_loop(findings: List[Dict], db: Session = None, project_id: int = None) -> None:
    config = get_yaml_config()
    repair_conf = config.get('agentic_repair', {})
    if not repair_conf.get('enabled', False):
        return
        
    max_calls = repair_conf.get('max_llm_calls_per_project', 50)
    
    srs_findings = [f for f in findings if f.get('artifact_type') == 'srs' and f.get('requirement_id')]
    
    # Group by requirement
    req_map = {}
    for f in srs_findings:
        rid = f['requirement_id']
        if rid not in req_map:
            req_map[rid] = {
                'original_text': f.get('quoted_text', ''),
                'flaws': [],
                'findings': []
            }
        req_map[rid]['flaws'].append(f['explanation'])
        req_map[rid]['findings'].append(f)
        
    for rid, data in req_map.items():
        if _get_llm_call_count(db, project_id) >= max_calls:
            import logging
            logging.getLogger(__name__).warning(f"Project {project_id} reached max LLM calls ({max_calls}). Stopping repair.")
            break
            
        current_text = data['original_text']
        current_flaws = list(data['flaws'])
        
        attempts = 0
        passed = False
        final_rewrite = None
        
        while attempts < 3:
            if _get_llm_call_count(db, project_id) >= max_calls:
                break
                
            attempts += 1
            
            user_prompt = f"Original Requirement: {current_text}\nFlaws to fix:\n"
            for flaw in current_flaws:
                user_prompt += f"- {flaw}\n"
                
            try:
                resp_text = await call_llm(REPAIR_SYSTEM_PROMPT, user_prompt, db, project_id, retry=1)
                parsed = json.loads(resp_text)
                rewrite = parsed.get("rewrite_suggestion", "").strip()
                if not rewrite:
                    raise ValueError("Empty rewrite suggestion")
                    
                final_rewrite = rewrite
                
                # Re-run deterministic checks on the rewrite
                dummy_req = [{'id': rid, 'text': rewrite, 'class': 'unknown', 'section': 'unknown'}]
                new_findings = run_all_srs_checks({'requirements': dummy_req, 'sections': []})
                
                # Keep only requirement-level findings that apply to this req
                new_findings = [f for f in new_findings if f.get('requirement_id') == rid]
                
                if not new_findings:
                    passed = True
                    break
                else:
                    # Feed the new findings back as flaws for the next iteration
                    current_text = rewrite
                    current_flaws = [f['explanation'] for f in new_findings]
                    
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Repair loop failed for {rid}: {e}")
                break
                
        # Update findings with the result
        for f in data['findings']:
            f['rewrite_suggestion'] = final_rewrite
            f['rewrite_attempts'] = attempts
            f['rewrite_passed'] = passed
