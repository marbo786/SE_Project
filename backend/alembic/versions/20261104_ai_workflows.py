"""AI cost reservations and append-only suggestion decisions."""
from alembic import op
import sqlalchemy as sa
revision = "20261104_ai_workflows"
down_revision = "20261104_ai"
branch_labels = depends_on = None

def upgrade():
    for name in ("reserved_cost_microusd", "reported_cost_microusd", "input_price", "output_price"):
        op.add_column("llm_calls", sa.Column(name, sa.BigInteger()))
    op.create_table("suggestion_decisions", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("analysis_runs.id"), nullable=False),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("run_findings.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("project_revisions.id")),
        sa.Column("replacement_text", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_suggestion_decisions_run_id", "suggestion_decisions", ["run_id"])

def downgrade():
    op.drop_table("suggestion_decisions")
    for name in ("output_price", "input_price", "reported_cost_microusd", "reserved_cost_microusd"):
        op.drop_column("llm_calls", name)
