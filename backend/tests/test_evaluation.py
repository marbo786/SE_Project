from scripts.evaluate import evaluate


def test_missing_ids_are_counted_as_separate_examples():
    result = evaluate([{"id": None, "text": "The system shall save.", "class": "functional", "expected_rules": ["FR-409"]},
        {"id": None, "text": "The system shall delete.", "class": "functional", "expected_rules": ["FR-409"]}])
    assert result["rules"]["FR-409"]["tp"] == 2


def test_duplicate_occurrences_each_have_evidence():
    result = evaluate([{"id": "FR-1", "text": "The system shall save.", "class": "functional", "expected_rules": ["FR-410"]},
        {"id": "FR-1", "text": "The system shall delete.", "class": "functional", "expected_rules": ["FR-410"]}])
    assert result["rules"]["FR-410"]["tp"] == 2
