"""Preview expired AI cache cleanup; --apply deletes expired entries only."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app  # register models
from app.core.database import SessionLocal
from app.services.retention import prune_ai_cache

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps(prune_ai_cache(db, apply=args.apply)))
