"""Separate AI accounting from validated, expiring response cache."""
from alembic import op
import sqlalchemy as sa

revision = "20261104_ai"
down_revision = "20261104_jobs"
branch_labels = depends_on = None


def upgrade():
    op.create_table("llm_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("analysis_runs.id")),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("usage_source", sa.String(30), nullable=False),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer()), sa.Column("completion_tokens", sa.Integer()),
        sa.Column("latency_ms", sa.Float()), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_llm_calls_project_id", "llm_calls", ["project_id"])
    op.create_index("ix_llm_calls_run_id", "llm_calls", ["run_id"])
    op.create_table("llm_cache", sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_llm_cache_project_id", "llm_cache", ["project_id"])
    op.create_index("ix_llm_cache_expires_at", "llm_cache", ["expires_at"])


def downgrade():
    op.drop_table("llm_cache")
    op.drop_table("llm_calls")
