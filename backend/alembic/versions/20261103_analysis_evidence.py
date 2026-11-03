"""Add evidence, explicit analysis scope and a versioned score projection."""
from alembic import op
import sqlalchemy as sa

revision = "20261103_evidence"
down_revision = "20261102_security"
branch_labels = depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("analysis_profile", sa.String(), nullable=False, server_default="srs_only"))
    op.add_column("projects", sa.Column("analysis_mode", sa.String(), nullable=False, server_default="deterministic"))
    op.add_column("projects", sa.Column("analysis_error", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("source_spans", sa.JSON(), nullable=True))
    op.add_column("findings", sa.Column("element_id", sa.String(), nullable=True))
    op.create_index("ix_findings_element_id", "findings", ["element_id"])
    for column in [sa.Column("source_label", sa.String()), sa.Column("target_label", sa.String()),
        sa.Column("confidence", sa.Float()), sa.Column("origin", sa.String(), nullable=False, server_default="legacy"),
        sa.Column("evidence", sa.JSON()), sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.false())]:
        op.add_column("trace_links", column)
    op.add_column("quality_scores", sa.Column("details", sa.JSON(), nullable=True))
    # Existing numbers remain untouched and have no v2 details: they are legacy,
    # not retrospectively relabelled as measurements from the new rubric.


def downgrade():
    op.drop_column("quality_scores", "details")
    for name in ["source_label", "target_label", "confidence", "origin", "evidence", "is_stale"]:
        op.drop_column("trace_links", name)
    op.drop_index("ix_findings_element_id", table_name="findings")
    op.drop_column("findings", "element_id")
    op.drop_column("findings", "source_spans")
    for name in ["analysis_profile", "analysis_mode", "analysis_error"]:
        op.drop_column("projects", name)
