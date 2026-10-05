import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.pipeline.checks.srs_checks import run_all_srs_checks
from app.pipeline.checks.uml_checks import run_all_uml_checks
from app.pipeline.uml.parser import parse_plantuml

def evaluate():
    print("=" * 65)
    print("  AUTOMATED EVALUATION BENCHMARK (FR-907)")
    print("=" * 65)
    
    with open('eval/dataset.json', 'r') as f:
        dataset = json.load(f)
        
    rule_stats = {}
    
    # We will test each requirement individually (so FR-405 missing sections doesn't interfere)
    # But for FR-410 (duplicate), we need to test the whole list.
    
    all_expected = []
    for req in dataset:
        for rule in req['expected_rules']:
            all_expected.append((req['id'], rule))
            
    findings = run_all_srs_checks({'requirements': dataset, 'sections': []})
    
    # Filter out missing sections from the findings since we are only testing requirements
    findings = [f for f in findings if f['rule_id'] != 'FR-405' and f['rule_id'] != 'FR-305']
    
    detected = [(f['requirement_id'], f['rule_id']) for f in findings]
    
    for rule_id in ['FR-401', 'FR-402', 'FR-409', 'FR-410', 'FR-411']:
        exp = [x for x in all_expected if x[1] == rule_id]
        det = [x for x in detected if x[1] == rule_id]
        
        tp = len(set(exp) & set(det))
        fp = len(set(det) - set(exp))
        fn = len(set(exp) - set(det))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        rule_stats[rule_id] = {'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision, 'recall': recall, 'f1': f1}
        
    # Generate markdown
    md = "# Evaluation Results\n\n"
    md += "| Rule | Precision | Recall | F1-Score |\n"
    md += "|---|---|---|---|\n"
    
    total_tp = total_fp = total_fn = 0
    
    for rule_id, stats in rule_stats.items():
        md += f"| {rule_id} | {stats['precision']:.2f} | {stats['recall']:.2f} | {stats['f1']:.2f} |\n"
        total_tp += stats['tp']
        total_fp += stats['fp']
        total_fn += stats['fn']
        
    ovr_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    ovr_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    ovr_f1 = 2 * (ovr_p * ovr_r) / (ovr_p + ovr_r) if (ovr_p + ovr_r) > 0 else 0.0
    
    md += f"| **Overall** | **{ovr_p:.2f}** | **{ovr_r:.2f}** | **{ovr_f1:.2f}** |\n"
    
    with open('eval/results.md', 'w') as f:
        f.write(md)
        
    print(md)

if __name__ == "__main__":
    evaluate()
