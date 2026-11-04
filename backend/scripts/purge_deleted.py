"""Preview expired project deletion; --apply permanently purges eligible records."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app  # register all metadata
from app.core.database import SessionLocal
from app.services.retention import purge_expired


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps(purge_expired(db, apply=args.apply), indent=2))
