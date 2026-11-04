"""Durable dispatch, fenced worker attempts, cancellation and stage checkpoints."""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = '20261104_jobs'
down_revision = '20261103_history'
branch_labels = depends_on = None


def upgrade():
    for column in [sa.Column('attempt_id', sa.String(36)), sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('heartbeat_at', sa.DateTime()), sa.Column('lease_expires_at', sa.DateTime()),
        sa.Column('cancel_requested', sa.Boolean(), nullable=False, server_default=sa.false())]:
        op.add_column('analysis_runs', column)
    op.create_index('ix_analysis_runs_lease_expires_at', 'analysis_runs', ['lease_expires_at'])
    op.create_table('outbox_events', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('analysis_runs.id'), nullable=False, unique=True),
        sa.Column('available_at', sa.DateTime(), nullable=False), sa.Column('published_at', sa.DateTime()),
        sa.Column('dispatch_attempts', sa.Integer(), nullable=False), sa.Column('last_error', sa.String(64)))
    op.create_index('ix_outbox_events_available_at', 'outbox_events', ['available_at'])
    op.create_table('run_stages', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('analysis_runs.id'), nullable=False),
        sa.Column('stage', sa.String(80), nullable=False), sa.Column('attempt_id', sa.String(36), nullable=False),
        sa.Column('output_hash', sa.String(64), nullable=False), sa.Column('output', sa.JSON(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False), sa.UniqueConstraint('run_id', 'stage', name='uq_run_stage'))
    op.create_index('ix_run_stages_run_id', 'run_stages', ['run_id'])
    # A write freeze must stop old workers before migration. Persist queued work
    # from the prior dispatch mechanism instead of invalidating every project.
    bind = op.get_bind()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for run_id in bind.execute(sa.text("SELECT id FROM analysis_runs WHERE status IN ('queued','running')")).scalars():
        bind.execute(sa.text("UPDATE analysis_runs SET status='queued',stage='queued' WHERE id=:id"), {'id': run_id})
        bind.execute(sa.text('INSERT INTO outbox_events (run_id,available_at,dispatch_attempts) VALUES (:id,:now,0)'), {'id': run_id, 'now': now})


def downgrade():
    op.drop_table('run_stages')
    op.drop_table('outbox_events')
    op.drop_index('ix_analysis_runs_lease_expires_at', table_name='analysis_runs')
    for column in ['cancel_requested', 'lease_expires_at', 'heartbeat_at', 'attempt_count', 'attempt_id']:
        op.drop_column('analysis_runs', column)
