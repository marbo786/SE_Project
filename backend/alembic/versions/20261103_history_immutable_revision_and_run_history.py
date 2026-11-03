"""immutable_revision_and_run_history

Revision ID: 20261103_history
Revises: 20261103_evidence
Create Date: 2026-11-03 22:31:03.984887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import hashlib
import json
from datetime import datetime, timezone


# revision identifiers, used by Alembic.
revision: str = '20261103_history'
down_revision: Union[str, None] = '20261103_evidence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _import_legacy(bind):
    """Frozen, additive import. Never open/move files or infer name-based lineage."""
    meta = sa.MetaData()
    meta.reflect(bind=bind)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    def rows(name, **filters):
        table = meta.tables[name]
        query = sa.select(table)
        for key, value in filters.items():
            query = query.where(table.c[key] == value)
        return [dict(row) for row in bind.execute(query).mappings()]
    def insert(name, **values):
        return bind.execute(meta.tables[name].insert().values(**values)).inserted_primary_key[0]
    def serial(value):
        return json.loads(json.dumps(value, default=lambda item: item.isoformat() + 'Z'))
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()

    for project in rows('projects'):
        pid = project['id']
        artifacts = rows('artifacts', project_id=pid)
        findings = rows('findings', project_id=pid)
        traces = rows('trace_links', project_id=pid)
        scores = rows('quality_scores', project_id=pid)
        has_report = bool(findings or traces or scores)
        sealed = has_report or project['status'] != 'pending'
        rid = insert('project_revisions', project_id=pid, number=1, author_id=project['user_id'],
            state='sealed' if sealed else 'draft', edit_version=1,
            analysis_profile=project['analysis_profile'], analysis_mode=project['analysis_mode'],
            extraction_confirmed=False, legacy_version=project['version'],
            created_at=project['created_at'] or now, sealed_at=now if sealed else None)
        bind.execute(meta.tables['artifacts'].update().where(meta.tables['artifacts'].c.project_id == pid)
            .values(revision_id=rid))
        for artifact in artifacts:
            bind.execute(meta.tables['artifacts'].update().where(meta.tables['artifacts'].c.id == artifact['id'])
                .values(lineage_key=f"artifact-{artifact['id']}"))
        run_id = None
        if sealed:
            run_id = f'legacy-{pid}'
            status = {'done': 'completed', 'partial': 'partial'}.get(project['status'], 'failed')
            report = serial({'findings': findings, 'trace_links': traces, 'score': scores[0] if scores else None,
                'legacy': True, 'provenance': 'Imported unchanged; parser, rules, coverage and original reviewer are unknown.',
                'extractions': [{key: value for key, value in artifact.items() if key != 'file_path'} for artifact in artifacts]})
            insert('analysis_runs', id=run_id, project_id=pid, revision_id=rid, requested_by=project['user_id'],
                status=status, stage='legacy_import', counts={'findings': len(findings), 'trace_links': len(traces)},
                input_snapshot={'legacy_project_id': pid, 'legacy_version': project['version'],
                    'artifacts': [{'id': a['id'], 'filename': a['original_filename'], 'type': a['artifact_type']} for a in artifacts]},
                versions={'parser': 'unknown', 'rules': 'unknown', 'rubric': 'unknown'}, report=report,
                error_code='legacy_interrupted' if project['status'] == 'analyzing' else None,
                error_message='The legacy process stopped without a durable job record.' if project['status'] == 'analyzing' else None,
                created_at=project['created_at'] or now, finished_at=now)
            for finding in findings:
                insert('run_findings', run_id=run_id, fingerprint=digest(finding), rule_id=finding['rule_id'],
                    severity=finding['severity'], element_key=finding.get('element_id'), data=serial(finding))
            # Legacy duplicates are retained in the original snapshot. The normalized
            # endpoint table merges only identical endpoints, recording every decision.
            endpoints = {}
            for trace in traces:
                key = tuple(trace[k] for k in ('source_type', 'source_id', 'target_type', 'target_id'))
                tid = endpoints.get(key)
                if tid is None:
                    tid = insert('run_trace_links', run_id=run_id, fingerprint=digest(key),
                        **dict(zip(('source_type', 'source_id', 'target_type', 'target_id'), key)),
                        data={**serial(trace), 'status': 'suggested'})
                    endpoints[key] = tid
                if trace['status'] != 'suggested':
                    insert('review_decisions', run_id=run_id, trace_id=tid, actor_id=None,
                        status=trace['status'], origin='legacy_import', created_at=now,
                        reason='Imported legacy decision; original reviewer and decision time are unknown.')
            if scores:
                insert('run_quality_scores', run_id=run_id, overall_score=scores[0]['overall_score'],
                    payload=serial(scores[0]), computed_at=scores[0]['computed_at'] or now)
        bind.execute(meta.tables['projects'].update().where(meta.tables['projects'].c.id == pid).values(
            current_revision_id=rid, next_revision_number=2, version=1, latest_run_id=run_id,
            published_run_id=run_id if has_report else None,
            status='error' if project['status'] == 'analyzing' else project['status']))
        insert('audit_events', actor_id=None, project_id=pid, action='legacy_import',
            details={'legacy_project_id': pid, 'legacy_version': project['version'], 'revision_id': rid,
                'artifacts': len(artifacts), 'findings': len(findings), 'trace_links': len(traces)}, created_at=now)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('project_revisions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('state', sa.String(length=16), nullable=False),
    sa.Column('edit_version', sa.Integer(), nullable=False),
    sa.Column('analysis_profile', sa.String(length=32), nullable=False),
    sa.Column('analysis_mode', sa.String(length=32), nullable=False),
    sa.Column('canonical_inputs', sa.JSON(), nullable=True),
    sa.Column('extraction_confirmed', sa.Boolean(), nullable=False),
    sa.Column('legacy_version', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('sealed_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("state IN ('draft', 'sealed')", name='ck_revision_state'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['project_revisions.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'number', name='uq_revision_number')
    )
    with op.batch_alter_table('project_revisions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_project_revisions_project_id'), ['project_id'], unique=False)
        batch_op.create_index('uq_project_open_draft', ['project_id'], unique=True, sqlite_where=sa.text("state = 'draft'"), postgresql_where=sa.text("state = 'draft'"))

    op.create_table('analysis_runs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('revision_id', sa.Integer(), nullable=False),
    sa.Column('requested_by', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('stage', sa.String(length=40), nullable=False),
    sa.Column('counts', sa.JSON(), nullable=False),
    sa.Column('input_snapshot', sa.JSON(), nullable=False),
    sa.Column('input_hash', sa.String(length=64), nullable=True),
    sa.Column('versions', sa.JSON(), nullable=False),
    sa.Column('report', sa.JSON(), nullable=True),
    sa.Column('idempotency_key', sa.String(length=128), nullable=True),
    sa.Column('error_code', sa.String(length=64), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'partial', 'failed', 'cancelled')", name='ck_run_status'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['revision_id'], ['project_revisions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'idempotency_key', name='uq_run_request')
    )
    with op.batch_alter_table('analysis_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analysis_runs_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analysis_runs_revision_id'), ['revision_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analysis_runs_status'), ['status'], unique=False)

    op.create_table('audit_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('details', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_events_project_id'), ['project_id'], unique=False)

    op.create_table('idempotency_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=False),
    sa.Column('scope', sa.String(length=100), nullable=False),
    sa.Column('key', sa.String(length=128), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('response', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('actor_id', 'scope', 'key', name='uq_idempotency_request')
    )
    op.create_table('run_findings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.String(length=36), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('rule_id', sa.String(length=64), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('element_key', sa.String(length=512), nullable=True),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['analysis_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('run_findings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_run_findings_fingerprint'), ['fingerprint'], unique=False)
        batch_op.create_index(batch_op.f('ix_run_findings_run_id'), ['run_id'], unique=False)

    op.create_table('run_quality_scores',
    sa.Column('run_id', sa.String(length=36), nullable=False),
    sa.Column('overall_score', sa.Float(), nullable=True),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('computed_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['analysis_runs.id'], ),
    sa.PrimaryKeyConstraint('run_id')
    )
    op.create_table('run_trace_links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.String(length=36), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('source_type', sa.String(length=32), nullable=False),
    sa.Column('source_id', sa.String(length=512), nullable=False),
    sa.Column('target_type', sa.String(length=32), nullable=False),
    sa.Column('target_id', sa.String(length=512), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['analysis_runs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('run_id', 'source_type', 'source_id', 'target_type', 'target_id', name='uq_run_trace_endpoints')
    )
    with op.batch_alter_table('run_trace_links', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_run_trace_links_fingerprint'), ['fingerprint'], unique=False)
        batch_op.create_index(batch_op.f('ix_run_trace_links_run_id'), ['run_id'], unique=False)

    op.create_table('requirements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('revision_id', sa.Integer(), nullable=False),
    sa.Column('artifact_id', sa.Integer(), nullable=False),
    sa.Column('element_key', sa.String(length=512), nullable=False),
    sa.Column('lineage_key', sa.String(length=64), nullable=False),
    sa.Column('authored_id', sa.Text(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('original_text', sa.Text(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ),
    sa.ForeignKeyConstraint(['revision_id'], ['project_revisions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('revision_id', 'element_key', name='uq_requirement_occurrence')
    )
    with op.batch_alter_table('requirements', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_requirements_revision_id'), ['revision_id'], unique=False)

    op.create_table('review_decisions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.String(length=36), nullable=False),
    sa.Column('finding_id', sa.Integer(), nullable=True),
    sa.Column('trace_id', sa.Integer(), nullable=True),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('origin', sa.String(length=32), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('carried_from_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('(finding_id IS NOT NULL AND trace_id IS NULL) OR (finding_id IS NULL AND trace_id IS NOT NULL)', name='ck_decision_target'),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['carried_from_id'], ['review_decisions.id'], ),
    sa.ForeignKeyConstraint(['finding_id'], ['run_findings.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['analysis_runs.id'], ),
    sa.ForeignKeyConstraint(['trace_id'], ['run_trace_links.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('review_decisions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_review_decisions_run_id'), ['run_id'], unique=False)

    op.create_table('uml_elements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('revision_id', sa.Integer(), nullable=False),
    sa.Column('artifact_id', sa.Integer(), nullable=False),
    sa.Column('element_key', sa.String(length=512), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ),
    sa.ForeignKeyConstraint(['revision_id'], ['project_revisions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('revision_id', 'element_key', name='uq_uml_occurrence')
    )
    with op.batch_alter_table('uml_elements', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_uml_elements_revision_id'), ['revision_id'], unique=False)

    with op.batch_alter_table('artifacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('revision_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('lineage_key', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('content_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('size_bytes', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_artifacts_revision_id'), ['revision_id'], unique=False)
        batch_op.create_foreign_key('fk_artifact_revision', 'project_revisions', ['revision_id'], ['id'])

    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('next_revision_number', sa.Integer(), server_default='2', nullable=False))
        batch_op.add_column(sa.Column('current_revision_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('latest_run_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('published_run_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_project_current_revision', 'project_revisions', ['current_revision_id'], ['id'])
        batch_op.create_foreign_key('fk_project_latest_run', 'analysis_runs', ['latest_run_id'], ['id'])
        batch_op.create_foreign_key('fk_project_published_run', 'analysis_runs', ['published_run_id'], ['id'])

    _import_legacy(op.get_bind())


def downgrade() -> None:
    op.execute(sa.text('UPDATE projects SET version=(SELECT legacy_version FROM project_revisions WHERE project_revisions.id=projects.current_revision_id) '
        'WHERE next_revision_number=2 AND EXISTS (SELECT 1 FROM project_revisions WHERE project_revisions.id=projects.current_revision_id AND legacy_version IS NOT NULL)'))
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_constraint('fk_project_published_run', type_='foreignkey')
        batch_op.drop_constraint('fk_project_latest_run', type_='foreignkey')
        batch_op.drop_constraint('fk_project_current_revision', type_='foreignkey')
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('archived_at')
        batch_op.drop_column('published_run_id')
        batch_op.drop_column('latest_run_id')
        batch_op.drop_column('current_revision_id')
        batch_op.drop_column('next_revision_number')

    with op.batch_alter_table('artifacts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_artifact_revision', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_artifacts_revision_id'))
        batch_op.drop_column('size_bytes')
        batch_op.drop_column('content_hash')
        batch_op.drop_column('lineage_key')
        batch_op.drop_column('revision_id')

    with op.batch_alter_table('uml_elements', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_uml_elements_revision_id'))

    op.drop_table('uml_elements')
    with op.batch_alter_table('review_decisions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_review_decisions_run_id'))

    op.drop_table('review_decisions')
    with op.batch_alter_table('requirements', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_requirements_revision_id'))

    op.drop_table('requirements')
    with op.batch_alter_table('run_trace_links', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_run_trace_links_run_id'))
        batch_op.drop_index(batch_op.f('ix_run_trace_links_fingerprint'))

    op.drop_table('run_trace_links')
    op.drop_table('run_quality_scores')
    with op.batch_alter_table('run_findings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_run_findings_run_id'))
        batch_op.drop_index(batch_op.f('ix_run_findings_fingerprint'))

    op.drop_table('run_findings')
    op.drop_table('idempotency_records')
    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_events_project_id'))

    op.drop_table('audit_events')
    with op.batch_alter_table('analysis_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_analysis_runs_status'))
        batch_op.drop_index(batch_op.f('ix_analysis_runs_revision_id'))
        batch_op.drop_index(batch_op.f('ix_analysis_runs_project_id'))

    op.drop_table('analysis_runs')
    with op.batch_alter_table('project_revisions', schema=None) as batch_op:
        batch_op.drop_index('uq_project_open_draft', sqlite_where=sa.text("state = 'draft'"), postgresql_where=sa.text("state = 'draft'"))
        batch_op.drop_index(batch_op.f('ix_project_revisions_project_id'))

    op.drop_table('project_revisions')
    # ### end Alembic commands ###
