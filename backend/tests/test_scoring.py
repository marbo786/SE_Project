import pytest
from app.pipeline.scoring import compute_scores

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

