"""Consistent SQLite snapshot and migration rehearsal, never an in-place restore.

Pause application writes while snapshotting the database and referenced files.
Backups contain private documents and account records; keep them outside Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine, inspect, text
from alembic import command
from alembic.config import Config


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def snapshot(database, upload_dir, destination):
    database, upload_dir, destination = map(lambda p: Path(p).resolve(), (database, upload_dir, destination))
    if not database.is_file():
        raise ValueError('The source database does not exist')
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'uploads').mkdir()
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(destination / 'database.db') as target:
        source.backup(target)
    with sqlite3.connect(destination / 'database.db') as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        counts = {table: db.execute('SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0] for table in tables}
        projects = [dict(zip(('project_id', 'owner_id', 'legacy_version'), row)) for row in db.execute('SELECT id, user_id, version FROM projects ORDER BY id')]
        artifacts = list(db.execute('SELECT id, file_path FROM artifacts ORDER BY id'))
    files = []
    for artifact_id, stored in artifacts:
        path = Path(stored)
        if not path.is_absolute():
            # Stored paths were relative to the application's original working directory.
            candidates = [database.parent / path, upload_dir / path.name]
            path = next((p for p in candidates if p.is_file()), candidates[0])
        path = path.resolve()
        entry = {'artifact_id': artifact_id, 'original_path': stored}
        if path.parent != upload_dir or not path.is_file():
            entry['state'] = 'missing_or_outside_upload_root'
        else:
            checksum = sha256(path)
            copied = destination / 'uploads' / f'{checksum}{path.suffix.lower()}'
            if not copied.exists():
                shutil.copyfile(path, copied)
            if sha256(copied) != checksum or sha256(path) != checksum:
                raise RuntimeError('An input changed while copying; repeat under a write freeze')
            entry.update(state='copied', sha256=checksum, backup_path=copied.relative_to(destination).as_posix())
        files.append(entry)
    manifest = {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(), 'database_sha256': sha256(destination / 'database.db'),
        'row_counts': counts, 'project_mappings': projects, 'files': files}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def rehearse(backup, destination):
    backup, destination = Path(backup).resolve(), Path(destination).resolve()
    manifest = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    if sha256(backup / 'database.db') != manifest['database_sha256']:
        raise ValueError('Backup database checksum mismatch')
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'uploads').mkdir()
    database = destination / 'rehearsal.db'
    shutil.copyfile(backup / 'database.db', database)
    with sqlite3.connect(database) as db:
        before_users = list(db.execute('SELECT id, name, email, hashed_password FROM users ORDER BY id'))
        before_findings = list(db.execute('SELECT id, project_id, rule_id, explanation FROM findings ORDER BY id'))
        for entry in manifest['files']:
            if entry['state'] != 'copied':
                continue
            source = (backup / entry['backup_path']).resolve()
            if source.parent != backup / 'uploads' or sha256(source) != entry['sha256']:
                raise ValueError('Backup file path or checksum mismatch')
            target = destination / 'uploads' / source.name
            if not target.exists():
                shutil.copyfile(source, target)
            db.execute('UPDATE artifacts SET file_path=? WHERE id=?', (str(target), entry['artifact_id']))
        db.commit()
    engine = create_engine('sqlite:///' + str(database))
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    try:
        with engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, 'head')
        with sqlite3.connect(database) as db:
            assert list(db.execute('SELECT id, name, email, hashed_password FROM users ORDER BY id')) == before_users
            assert list(db.execute('SELECT id, project_id, rule_id, explanation FROM findings ORDER BY id')) == before_findings
            after_projects = list(db.execute('SELECT id, user_id FROM projects ORDER BY id'))
            assert after_projects == [(p['project_id'], p['owner_id']) for p in manifest['project_mappings']]
            assert not list(db.execute('PRAGMA foreign_key_check'))
            for table in ('users', 'projects', 'artifacts', 'findings', 'trace_links', 'quality_scores'):
                assert db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == manifest['row_counts'][table]
            mappings = [dict(zip(('project_id', 'revision_id', 'run_id'), row)) for row in db.execute('SELECT id, current_revision_id, published_run_id FROM projects ORDER BY id')]
        result = {'migration_and_restore_verified': True, 'row_counts': manifest['row_counts'], 'mappings': mappings,
            'copied_artifacts': sum(entry['state'] == 'copied' for entry in manifest['files']),
            'unavailable_artifacts': sum(entry['state'] != 'copied' for entry in manifest['files'])}
        (destination / 'reconciliation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        return result
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    backup = subs.add_parser('snapshot')
    backup.add_argument('--database', required=True); backup.add_argument('--uploads', required=True); backup.add_argument('--destination', required=True)
    check = subs.add_parser('rehearse')
    check.add_argument('--backup', required=True); check.add_argument('--destination', required=True)
    args = parser.parse_args()
    if args.command == 'snapshot':
        result = snapshot(args.database, args.uploads, args.destination)
        print(json.dumps({'row_counts': result['row_counts'], 'copied_files': sum(f['state'] == 'copied' for f in result['files']),
            'unavailable_files': sum(f['state'] != 'copied' for f in result['files'])}, indent=2))
    else:
        print(json.dumps(rehearse(args.backup, args.destination), indent=2))


if __name__ == '__main__':
    main()
