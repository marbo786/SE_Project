from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from app.core.config import get_settings


def test_additive_security_migration_preserves_user(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    url = "sqlite:///" + str(tmp_path / "migration.db")
    monkeypatch.setattr(get_settings(), "DATABASE_URL", url)
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(config, "499a4929ff0e")
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO users (id, name, email, hashed_password) VALUES (1, 'Existing', 'existing@example.com', 'preserved-hash')"))
        db.execute(text("INSERT INTO projects (id, user_id, name, version, status) VALUES (1, 1, 'Legacy', 1, 'done')"))
        db.execute(text("INSERT INTO quality_scores (project_id, requirements_score, uml_score, traceability_score, overall_score) VALUES (1, 30, 20, 20, 70)"))
    command.upgrade(config, "head")
    with engine.connect() as db:
        assert db.execute(text("SELECT hashed_password, email_verified FROM users WHERE id=1")).one() == ("preserved-hash", 0)
        assert db.execute(text("SELECT COUNT(*) FROM auth_sessions")).scalar() == 0
        assert db.execute(text("SELECT overall_score, details FROM quality_scores WHERE project_id=1")).one() == (70, None)
        assert db.execute(text("SELECT analysis_profile, analysis_mode FROM projects WHERE id=1")).one() == ("srs_only", "deterministic")
    engine.dispose()
