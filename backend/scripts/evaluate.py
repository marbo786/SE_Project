"""Reproducible occurrence-level results; preserve legacy labels for transparency."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.pipeline.checks.srs_checks import run_all_srs_checks


def evaluate(dataset):
    examples = [{**row, "internal_id": f"example-{index + 1}", "source_ref": f"Example {index + 1}"} for index, row in enumerate(dataset)]
    expected = Counter((row["internal_id"], rule) for row in examples for rule in row["expected_rules"])
    detected = Counter((finding.get("element_id"), finding["rule_id"]) for finding in run_all_srs_checks({"requirements": examples, "sections": []}) if finding["rule_id"] not in {"FR-405", "FR-305"})
    results = {}
    for rule in sorted({rule for _, rule in expected.keys() | detected.keys()}):
        actual = Counter({key: count for key, count in detected.items() if key[1] == rule})
        truth = Counter({key: count for key, count in expected.items() if key[1] == rule})
        tp, fp, fn = sum((truth & actual).values()), sum((actual - truth).values()), sum((truth - actual).values())
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        results[rule] = {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0}
    return {"examples": len(examples), "rules": results,
        "false_negatives": [[*key, count] for key, count in (expected - detected).items()],
        "false_positives": [[*key, count] for key, count in (detected - expected).items()]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval/dataset.json")
    parser.add_argument("--output", type=Path, default=ROOT / "eval/results.md")
    args = parser.parse_args()
    result = evaluate(json.loads(args.dataset.read_text(encoding="utf-8")))
    lines = ["# Deterministic legacy-fixture evaluation", "", f"{result['examples']} authored examples; counts use occurrence IDs, including every missing/duplicate ID.", "",
        "These labels are preserved from the original dataset, not relabelled to match the new code. FR-411 now applies to performance/availability thresholds; legacy labels also required numbers in other NFR subtypes. The resulting disagreements need independent annotation review. This is a development fixture, not a held-out accuracy or AI evaluation.", "",
        "| Rule | TP | FP | FN | Precision | Recall | F1 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for rule, values in result["rules"].items():
        lines.append(f"| {rule} | {values['tp']} | {values['fp']} | {values['fn']} | {values['precision']:.2f} | {values['recall']:.2f} | {values['f1']:.2f} |")
    lines.extend(["", "Mismatch details are recorded in `results.json`. Broader parsing, UML, traceability and scoring cases are integration/regression tests; their pass count is not an accuracy percentage.", ""])
    args.output.write_text("\n".join(lines), encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
