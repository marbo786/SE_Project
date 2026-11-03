import pytest
from app.pipeline.scoring import compute_scores


def test_srs_only_and_partial_scores_are_explicit():
    complete = compute_scores([], [], 2, 0)
    assert complete["overall_score"] == 100
    assert complete["uml_score"] is None and complete["traceability_score"] is None
    assert complete["details"]["categories"]["uml"]["applicable"] is False
    partial = compute_scores([], [], 2, 0, complete=False)
    assert partial["overall_score"] is None
    assert partial["requirements_score"] == 100
    assert compute_scores([], [], 0, 0)["overall_score"] is None


def test_inserted_link_count_cannot_change_scores():
    obligations = [{"covered": True, "confirmed": False}, {"covered": False, "confirmed": False}]
    a = compute_scores([], [], 2, 3, 0, profile="architecture", obligations=obligations)
    b = compute_scores([], [], 2, 3, 100, profile="architecture", obligations=obligations)
    assert a == b
    assert a["traceability_score"] == 15
    assert a["details"]["categories"]["traceability"]["percentage"] == 50


def test_security_nfr_does_not_require_arbitrary_number():
    from app.pipeline.checks.srs_checks import run_all_srs_checks
    parsed = {"sections": [], "requirements": [{"id": "NFR-1", "class": "non_functional", "text": "The system shall encrypt passwords before storage."},
        {"id": "NFR-2", "class": "non_functional", "text": "The system shall respond quickly."}]}
    metrics = [finding for finding in run_all_srs_checks(parsed) if finding["rule_id"] == "FR-411"]
    assert [finding["requirement_id"] for finding in metrics] == ["NFR-2"]

def test_scoring_normalization():
    findings = [
        {'artifact_type': 'srs', 'severity': 'critical'}, # penalty 15
        {'artifact_type': 'srs', 'severity': 'major'},    # penalty 5
        {'artifact_type': 'srs', 'severity': 'minor'}     # penalty 2
    ] # Total penalty = 22

    # 10 requirements: density = 22 / 10 = 2.2. Score deduct = 2.2 * 10 = 22. Req score = 100 - 22 = 78
    # Scaled to 40% weight: 78 * 0.4 = 31.2
    scores_10 = compute_scores(findings, [], 10, 10, 10)
    
    # 200 requirements: density = 22 / 200 = 0.11. Score deduct = 1.1. Req score = 98.9
    # Scaled to 40% weight: 98.9 * 0.4 = 39.56
    scores_200 = compute_scores(findings, [], 200, 10, 10)

    assert scores_10['requirements_score'] < scores_200['requirements_score']
    assert scores_10['requirements_score'] > 0
    assert scores_200['requirements_score'] > 0
    
    print("Scores 10:", scores_10)
    print("Scores 200:", scores_200)

