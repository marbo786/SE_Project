"""
Evaluation Script (FR-907):
Evaluates deterministic SRS and UML defect detection algorithms against
a benchmark ground-truth dataset and computes Precision, Recall, and F1-Score.

Usage:
    python backend/scripts/evaluate.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.pipeline.checks.srs_checks import run_all_srs_checks
from app.pipeline.checks.uml_checks import run_all_uml_checks
from app.pipeline.uml.parser import parse_plantuml

ALL_STANDARD_SECTIONS = [
    "1. Introduction", "1.1", "1.2", "1.3",
    "2. Overall description", "3. Use cases",
    "4. Functional requirements", "5. Non-functional requirements",
    "6. External interface requirements", "7. Data requirements"
]

BENCHMARK_SRS_TEST_CASES = [
    {
        "id": "TC-SRS-01",
        "description": "Requirement with ambiguous terms (fast, user-friendly)",
        "input": {
            "sections": ALL_STANDARD_SECTIONS,
            "requirements": [
                {"id": "FR-01", "text": "The portal shall be fast and user-friendly.", "section": "4. Functional requirements", "class": "functional"}
            ]
        },
        "expected_rules": ["FR-401"]
    },
    {
        "id": "TC-SRS-02",
        "description": "Non-atomic requirement with multiple shalls",
        "input": {
            "sections": ALL_STANDARD_SECTIONS,
            "requirements": [
                {"id": "FR-02", "text": "The system shall validate credentials and shall record an audit log.", "section": "4. Functional requirements", "class": "functional"}
            ]
        },
        "expected_rules": ["FR-402"]
    },
    {
        "id": "TC-SRS-03",
        "description": "Non-functional requirement without quantifiable metric",
        "input": {
            "sections": ALL_STANDARD_SECTIONS,
            "requirements": [
                {"id": "NFR-01", "text": "The database shall be highly responsive.", "section": "5. Non-functional requirements", "class": "non_functional"}
            ]
        },
        "expected_rules": ["FR-411"]
    },
    {
        "id": "TC-SRS-04",
        "description": "Requirement with missing identifier",
        "input": {
            "sections": ALL_STANDARD_SECTIONS,
            "requirements": [
                {"id": None, "text": "The system shall generate weekly status reports.", "section": "4. Functional requirements", "class": "functional"}
            ]
        },
        "expected_rules": ["FR-409"]
    },
    {
        "id": "TC-SRS-05",
        "description": "Duplicate requirement identifiers",
        "input": {
            "sections": ALL_STANDARD_SECTIONS,
            "requirements": [
                {"id": "FR-10", "text": "The system shall authenticate admins.", "section": "4. Functional requirements", "class": "functional"},
                {"id": "FR-10", "text": "The system shall reset passwords.", "section": "4. Functional requirements", "class": "functional"}
            ]
        },
        "expected_rules": ["FR-410"]
    },
    {
        "id": "TC-SRS-06",
        "description": "Missing expected IEEE sections",
        "input": {
            "sections": ["1. Introduction", "4. Functional requirements"],
            "requirements": [
                {"id": "FR-20", "text": "The system shall process orders.", "section": "4. Functional requirements", "class": "functional"}
            ]
        },
        "expected_rules": ["FR-405"]
    }
]

BENCHMARK_UML_TEST_CASES = [
    {
        "id": "TC-UML-01",
        "description": "Disconnected actor in use case diagram",
        "puml": """@startuml
actor Student
actor Observer
(Enroll Course)
Student --> (Enroll Course)
@enduml""",
        "expected_rules": ["FR-601"]
    },
    {
        "id": "TC-UML-02",
        "description": "Disconnected usecase without actor association",
        "puml": """@startuml
actor Student
(Enroll Course)
(Orphan Feature)
Student --> (Enroll Course)
@enduml""",
        "expected_rules": ["FR-602"]
    },
    {
        "id": "TC-UML-03",
        "description": "Empty class without attributes or operations",
        "puml": """@startuml
class EmptyEntity {
}
@enduml""",
        "expected_rules": ["FR-603"]
    },
    {
        "id": "TC-UML-04",
        "description": "Association referring to undefined class without multiplicity",
        "puml": """@startuml
class User {
  +name: string
}
User -- Order
@enduml""",
        "expected_rules": ["FR-604", "FR-605"]
    }
]

def evaluate():
    print("=" * 65)
    print("  AUTOMATED EVALUATION BENCHMARK (FR-907)")
    print("=" * 65)

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    print("\n--- Evaluating SRS Defect Rules (FR-401 through FR-411) ---")
    for tc in BENCHMARK_SRS_TEST_CASES:
        findings = run_all_srs_checks(tc["input"])
        detected_rules = set(f["rule_id"] for f in findings)
        expected_rules = set(tc["expected_rules"])

        tp = len(detected_rules & expected_rules)
        fp = len(detected_rules - expected_rules)
        fn = len(expected_rules - detected_rules)

        true_positives += tp
        false_positives += fp
        false_negatives += fn

        status = "PASS" if fn == 0 else "FAIL"
        print(f"[{status}] {tc['id']}: {tc['description']}")
        print(f"       Expected: {list(expected_rules)} | Detected: {list(detected_rules)}")

    print("\n--- Evaluating UML Defect Rules (FR-601 through FR-609) ---")
    for tc in BENCHMARK_UML_TEST_CASES:
        model = parse_plantuml(tc["puml"])
        findings = run_all_uml_checks(model)
        detected_rules = set(f["rule_id"] for f in findings)
        expected_rules = set(tc["expected_rules"])

        tp = len(detected_rules & expected_rules)
        fp = len(detected_rules - expected_rules)
        fn = len(expected_rules - detected_rules)

        true_positives += tp
        false_positives += fp
        false_negatives += fn

        status = "PASS" if fn == 0 else "FAIL"
        print(f"[{status}] {tc['id']}: {tc['description']}")
        print(f"       Expected: {list(expected_rules)} | Detected: {list(detected_rules)}")

    # Metrics calculation
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print("\n" + "=" * 65)
    print("  BENCHMARK EVALUATION RESULTS")
    print("=" * 65)
    print(f"  True Positives  (TP) : {true_positives}")
    print(f"  False Positives (FP) : {false_positives}")
    print(f"  False Negatives (FN) : {false_negatives}")
    print(f"  Precision            : {precision * 100:.2f}%")
    print(f"  Recall               : {recall * 100:.2f}%")
    print(f"  F1-Score             : {f1 * 100:.2f}%")
    print("=" * 65)

    if f1 >= 0.90:
        print(">> BENCHMARK PASSED: Defect detection exceeds performance criteria (F1 >= 90%)")
    else:
        print(">> BENCHMARK WARNING: F1-score below standard threshold")

if __name__ == "__main__":
    evaluate()
