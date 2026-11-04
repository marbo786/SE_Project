"""Offline AI contract benchmark; live fixture-only evaluation requires two opt-in flags."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--allow-external-fixtures", action="store_true")
    args = parser.parse_args()
    if args.live and not args.allow_external_fixtures:
        parser.error("Live evaluation sends the synthetic fixtures to the configured provider; add --allow-external-fixtures")
    fixtures = json.loads((Path(__file__).resolve().parents[1]/"evaluation"/"ai_cases.json").read_text(encoding="utf-8"))
    # Set the isolated database BEFORE importing application configuration.
    with tempfile.TemporaryDirectory(prefix="srs-ai-eval-") as directory:
        os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(directory)/"evaluation.db")
        from app.pipeline.checks.llm_checks import conflict_pairs, check_testability, check_conflicts
        from app.pipeline.repair import rewrite_checks
        pairs = {frozenset((int(p["left"]["id"][1:]),int(p["right"]["id"][1:]))) for p in conflict_pairs([r["text"] for r in fixtures["requirements"]])}
        labels = [frozenset(pair) for pair in fixtures["conflicting_pairs"]]
        rejected = sum(not all(rewrite_checks(case["original"],case["proposal"],"R")[0].values()) for case in fixtures["unsafe_rewrites"])
        result = {"candidate_pairs":len(pairs),"labelled_conflicts":len(labels),
                  "candidate_pair_recall":sum(pair in pairs for pair in labels)/len(labels),
                  "unsafe_rewrites_blocked":rejected,"unsafe_rewrites_total":len(fixtures["unsafe_rewrites"]),
                  "limitation":"Candidate enumeration and lexical guards only; not model accuracy or production validation."}
        if args.live:
            from app.main import app
            from app.core.database import Base, engine, SessionLocal
            from app.core.config import ai_run, get_settings
            from app.models.user import User
            from app.services.history import new_project, ensure_revision, start_run, digest
            from app.llm.engine import usage_summary, AIError
            if get_settings().LLM_PROVIDER == "mock":
                parser.error("Configure a real provider and model pricing for live evaluation")
            Base.metadata.create_all(engine)  # disposable fixture database only
            try:
                with SessionLocal() as db:
                    user = User(name="Evaluation",email="fixture@example.com",hashed_password="unused")
                    db.add(user); db.flush()
                    project = new_project(db,user.id,{"name":"Synthetic AI evaluation","analysis_mode":"ai"})
                    run = start_run(db,project,ensure_revision(db,project),user.id,validate=False)
                    run.input_hash = digest(fixtures)
                    db.commit()
                    token = ai_run.set(run.id)
                    coverage, findings = {}, []
                    async def evaluate():
                        await check_testability(fixtures["requirements"],db,project.id,coverage=coverage,output=findings)
                        await check_conflicts(fixtures["requirements"],db,project.id,coverage=coverage,output=findings)
                    try:
                        asyncio.run(evaluate())
                        result["live_status"] = "completed"
                    except Exception as error:
                        result["live_status"] = "partial"
                        result["error"] = str(error) if isinstance(error,AIError) else type(error).__name__
                    finally:
                        ai_run.reset(token)
                    found = {frozenset((int(f["requirement_id"].split("-")[-1])-1,int(f["related_requirement"]["id"].split("-")[-1])-1)) for f in findings if f["rule_id"] == "FR-404"}
                    result.update(coverage=coverage,usage=usage_summary(db,run.id),finding_count=len(findings),
                        live_conflict_recall=len(found & set(labels))/len(labels),
                        live_conflict_precision=len(found & set(labels))/len(found) if found else None)
            finally:
                engine.dispose()
        print(json.dumps(result,indent=2))
        if args.live and result.get("live_status") != "completed":
            return 2
        return 0 if rejected == len(fixtures["unsafe_rewrites"]) and all(p in pairs for p in labels) else 1


if __name__ == "__main__":
    raise SystemExit(main())
