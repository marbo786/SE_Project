"""Rubric v2: applicable evidence, stable denominators, explicit incompleteness."""
from ..core.config import get_yaml_config


def compute_scores(findings, trace_links, req_count, uml_count, trace_count=0, *, profile=None, complete=True, obligations=None):
    # trace_count is retained for old callers, but insertion counts never affect a grade.
    profile = profile or ("architecture" if uml_count else "srs_only")
    architecture = profile == "architecture"
    config = get_yaml_config()
    penalties = config.get("severity_penalty", {"critical": 15, "major": 5, "minor": 2})
    weights = config.get("rubric", {"requirements": 40, "uml": 30, "traceability": 30}) if architecture else {"requirements": 100, "uml": 0, "traceability": 0}
    # This is a machine score. Operational/AI failures and review decisions do not
    # create document penalties; a failed requested stage suppresses the final grade.
    def raw(kind, denominator):
        if not denominator:
            return None
        total = sum(penalties.get(f.get("severity"), 0) for f in findings
            if f.get("artifact_type") == kind and f.get("finding_type", "deterministic") == "deterministic")
        return max(0.0, 100 - total / denominator * 10)

    requirement_raw = raw("srs", req_count)
    uml_raw = raw("uml", uml_count) if architecture else None
    evaluated = obligations or []
    candidate_covered = sum(bool(item["covered"]) for item in evaluated)
    confirmed_covered = sum(bool(item["confirmed"]) for item in evaluated)
    trace_raw = candidate_covered / len(evaluated) * 100 if architecture and evaluated else None
    categories = {}
    for name, percentage, count in [("requirements", requirement_raw, req_count), ("uml", uml_raw, uml_count), ("traceability", trace_raw, len(evaluated))]:
        applicable = name == "requirements" or architecture
        categories[name] = {"applicable": applicable, "eligible_count": count if applicable else 0,
            "percentage": round(percentage, 2) if percentage is not None else None, "weight": weights.get(name, 0),
            "contribution": round(percentage * weights.get(name, 0) / 100, 2) if percentage is not None else None}
    ready = complete and req_count > 0 and all(item["percentage"] is not None for item in categories.values() if item["applicable"])
    overall = round(sum(item["contribution"] or 0 for item in categories.values()), 2) if ready else None
    return {"requirements_score": categories["requirements"]["contribution"],
        "uml_score": categories["uml"]["contribution"], "traceability_score": categories["traceability"]["contribution"],
        "overall_score": overall, "details": {"rubric_version": "2", "profile": profile,
            "complete": ready, "categories": categories, "trace_obligations": len(evaluated),
            "candidate_covered": candidate_covered, "confirmed_covered": confirmed_covered,
            "note": "Machine assessment of the evaluated inputs. Trace coverage includes inferred candidates; reviewer confirmation is reported separately."}}
