from pathlib import Path
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.models.project import Project
from app.models.history import ProjectRevision
from app.services.history import fork_draft


def config():
    root = Path(__file__).resolve().parents[1]
    value = Config(str(root / 'alembic.ini'))
    value.set_main_option('script_location', str(root / 'alembic'))
    return value


def migrate(engine, target, *, down=False):
    cfg = config()
    with engine.begin() as connection:
        cfg.attributes['connection'] = connection
        (command.downgrade if down else command.upgrade)(cfg, target)


def seed_legacy(engine, file_path='missing-source.docx'):
    migrate(engine, '20261103_evidence')
    with engine.begin() as db:
        uid = db.execute(text("INSERT INTO users (name,email,hashed_password) VALUES ('Existing','existing@example.com','unchanged-hash') RETURNING id")).scalar_one()
        ids = [db.execute(text("INSERT INTO projects(user_id,name,version,status) VALUES (:uid,'Same display name',:version,'done') RETURNING id"), {'uid': uid, 'version': v}).scalar_one() for v in (4, 9)]
        for pid in ids:
            db.execute(text("INSERT INTO artifacts(project_id,artifact_type,file_format,file_path,original_filename) VALUES (:pid,'srs','docx',:path,'source.docx')"), {'pid': pid, 'path': file_path})
            db.execute(text("INSERT INTO findings(project_id,rule_id,severity,explanation) VALUES (:pid,'FR-1','major','Original finding')"), {'pid': pid})
            db.execute(text("INSERT INTO trace_links(project_id,source_type,source_id,target_type,target_id,status) VALUES (:pid,'requirement','FR-1','usecase','Original','confirmed')"), {'pid': pid})
            db.execute(text("INSERT INTO quality_scores(project_id,overall_score) VALUES (:pid,70)"), {'pid': pid})
    return uid, ids


def assert_history(engine, ids):
    with engine.connect() as db:
        projects = db.execute(text('SELECT id,current_revision_id,published_run_id,version FROM projects ORDER BY id')).all()
        assert [p.id for p in projects] == ids
        assert len({p.current_revision_id for p in projects}) == 2
        assert all(p.version == 1 for p in projects)
        assert db.execute(text('SELECT legacy_version FROM project_revisions ORDER BY project_id')).scalars().all() == [4, 9]
        assert db.execute(text('SELECT COUNT(*) FROM run_findings')).scalar_one() == 2
        assert db.execute(text('SELECT COUNT(*) FROM artifacts WHERE revision_id IS NOT NULL')).scalar_one() == 2
        assert db.execute(text('SELECT COUNT(*) FROM review_decisions WHERE actor_id IS NULL AND origin=\'legacy_import\'')).scalar_one() == 2
        assert db.execute(text('SELECT overall_score FROM run_quality_scores')).scalars().all() == [70, 70]
        for report in db.execute(text('SELECT report FROM analysis_runs')).scalars():
            if isinstance(report, str):
                report = json.loads(report)
            assert report['legacy'] and report['findings'][0]['explanation'] == 'Original finding'
        assert db.execute(text('SELECT hashed_password FROM users')).scalar_one() == 'unchanged-hash'
        if engine.dialect.name == 'sqlite':
            assert not db.execute(text('PRAGMA foreign_key_check')).all()


def test_populated_history_upgrade_downgrade_and_restore(tmp_path):
    from scripts.backup_rehearsal import snapshot, rehearse
    upload_root = tmp_path / 'uploads'; upload_root.mkdir()
    document = upload_root / 'original.docx'; document.write_bytes(b'unchanged legacy input')
    database = tmp_path / 'original.db'
    engine = create_engine('sqlite:///' + str(database))
    try:
        _, ids = seed_legacy(engine, str(document))
        before = document.read_bytes()
        backup = tmp_path / 'backup'
        manifest = snapshot(database, upload_root, backup)
        assert manifest['row_counts']['projects'] == 2
        rehearsal = rehearse(backup, tmp_path / 'restored')
        assert rehearsal['migration_and_restore_verified'] and rehearsal['copied_artifacts'] == 2
        assert document.read_bytes() == before
        # Rehearsal does not mutate the real source schema.
        assert 'analysis_runs' not in inspect(engine).get_table_names()
        migrate(engine, 'head'); assert_history(engine, ids)
        migrate(engine, '20261103_evidence', down=True)
        assert 'analysis_runs' not in inspect(engine).get_table_names()
        with engine.connect() as db:
            assert db.execute(text('SELECT COUNT(*) FROM findings')).scalar_one() == 2
        migrate(engine, 'head')
        # Original legacy version labels are preserved before an initial cutover.
        # A schema downgrade after writes is not a historical-data rollback.
        with engine.connect() as db:
            assert db.execute(text('SELECT COUNT(*) FROM run_findings')).scalar_one() == 2
    finally:
        engine.dispose()


@pytest.mark.skipif(not os.environ.get('TEST_POSTGRES_URL'), reason='PostgreSQL integration runs in CI or with TEST_POSTGRES_URL')
def test_postgres_migration_and_concurrent_revision_allocation():
    url = os.environ['TEST_POSTGRES_URL']
    schema = 'srs_test_' + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as db:
        db.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
    try:
        uid, ids = seed_legacy(engine)
        migrate(engine, 'head'); assert_history(engine, ids)
        factory = sessionmaker(bind=engine)
        with factory() as db:
            parent = db.get(Project, ids[0]).current_revision_id
        def fork(_):
            with factory.begin() as db:
                revision = fork_draft(db, db.get(Project, ids[0]), uid, parent)
                return revision.id, revision.number
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(fork, range(4)))
        assert len(set(results)) == 1 and results[0][1] == 2
        with factory() as db:
            assert db.query(ProjectRevision).filter_by(project_id=ids[0]).count() == 2
        migrate(engine, '20261103_evidence', down=True)
        migrate(engine, 'head')
    finally:
        engine.dispose()
        with admin.begin() as db:
            db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
