import os
import sys

with open('backend/app/pipeline/analyzer.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the deletion of ALL TraceLinks
old_del = "db.query(TraceLink).filter(TraceLink.project_id == project_id).delete()"
new_del = "db.query(TraceLink).filter(TraceLink.project_id == project_id, TraceLink.status == 'suggested').delete()"
text = text.replace(old_del, new_del)

# Inject fetching of existing persistent links and merging them
old_trace = '''        if usecase_model:
            trace_link_dicts = build_trace_links(requirements, usecase_model, sequence_model, class_model)
            existing_links = [
                {
                    'source_type': tl['source_type'],
                    'source_id': tl['source_id'],
                    'target_type': tl['target_type'],
                    'target_id': tl['target_id']
                }
                for tl in trace_link_dicts
            ]
            trace_findings = check_traceability(requirements, usecase_model, sequence_model, class_model, existing_links)
            all_findings += trace_findings

        # ── Save findings ─────────────────────────────────────────────────'''

new_trace = '''        if usecase_model:
            trace_link_dicts = build_trace_links(requirements, usecase_model, sequence_model, class_model)
            
            # Fetch persistent links from DB (confirmed/rejected)
            persistent_links = db.query(TraceLink).filter(TraceLink.project_id == project_id).all()
            persistent_keys = {(l.source_type, l.source_id, l.target_type, l.target_id): l.status for l in persistent_links}
            
            final_links_for_check = []
            final_links_to_save = []
            
            # Incorporate newly suggested links if they don't exist
            for tl in trace_link_dicts:
                k = (tl['source_type'], tl['source_id'], tl['target_type'], tl['target_id'])
                if k not in persistent_keys:
                    final_links_for_check.append(tl)
                    final_links_to_save.append(tl)
                    
            # Incorporate persistent links for checking
            for l in persistent_links:
                final_links_for_check.append({
                    'source_type': l.source_type,
                    'source_id': l.source_id,
                    'target_type': l.target_type,
                    'target_id': l.target_id,
                    'status': l.status
                })
                
            trace_link_dicts = final_links_to_save  # Only save new ones
                
            trace_findings = check_traceability(requirements, usecase_model, sequence_model, class_model, final_links_for_check)
            all_findings += trace_findings

        # ── Save findings ─────────────────────────────────────────────────'''

text = text.replace(old_trace, new_trace)

with open('backend/app/pipeline/analyzer.py', 'w', encoding='utf-8') as f:
    f.write(text)
