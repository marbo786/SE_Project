import os
import sys
import re

with open('backend/app/pipeline/analyzer.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Make the function async
text = text.replace('def run_analysis_pipeline(project_id: int, _db=None) -> None:', 'async def run_analysis_pipeline(project_id: int, _db=None) -> None:')

# Fix the LLM checks block
old_llm_block = '''        has_llm_error = False
        if requirements:
            loop = asyncio.new_event_loop()
            try:
                llm_findings = loop.run_until_complete(
                    check_testability(requirements, db=db, project_id=project_id)
                )
                all_findings += llm_findings
                conflict_findings = loop.run_until_complete(
                    check_conflicts(requirements, db=db, project_id=project_id)
                )
                all_findings += conflict_findings
                
                loop.run_until_complete(
                    generate_rewrites(all_findings, db=db, project_id=project_id)
                )
            except Exception as e:
                has_llm_error = True
                from .checks.llm_checks import LLMCheckError
                import logging
                logging.getLogger(__name__).warning(f"LLM failure: {e}")
                all_findings.append({
                    'rule_id': 'SYS-WARN', 'severity': 'minor', 'quoted_text': None,
                    'explanation': f'Warning: LLM check failed: {e}',
                    'requirement_id': None, 'finding_type': 'system', 'artifact_type': 'srs'
                })
        
            finally:
                loop.close()'''

new_llm_block = '''        has_llm_error = False
        if requirements:
            try:
                llm_findings = await check_testability(requirements, db=db, project_id=project_id)
                all_findings += llm_findings
                conflict_findings = await check_conflicts(requirements, db=db, project_id=project_id)
                all_findings += conflict_findings
                await generate_rewrites(all_findings, db=db, project_id=project_id)
            except Exception as e:
                has_llm_error = True
                import logging
                logging.getLogger(__name__).warning(f"LLM failure: {e}")
                all_findings.append({
                    'rule_id': 'SYS-WARN', 'severity': 'minor', 'quoted_text': None,
                    'explanation': f'Warning: LLM check failed: {e}',
                    'requirement_id': None, 'finding_type': 'system', 'artifact_type': 'srs'
                })'''

text = text.replace(old_llm_block, new_llm_block)

# Add counts to compute_scores
old_scores = "scores = compute_scores(all_findings, trace_link_dicts)"
new_scores = '''
        req_count = len(requirements)
        uml_elements_count = 0
        if usecase_model:
            uml_elements_count += len(usecase_model.get('use_cases', [])) + len(usecase_model.get('actors', []))
        if class_model:
            uml_elements_count += len(class_model.get('classes', []))
        if sequence_model:
            uml_elements_count += len(sequence_model.get('messages', []))
            
        link_count = len(trace_link_dicts)
        
        scores = compute_scores(all_findings, trace_link_dicts, req_count, uml_elements_count, link_count)
'''
text = text.replace(old_scores, new_scores)

with open('backend/app/pipeline/analyzer.py', 'w', encoding='utf-8') as f:
    f.write(text)
