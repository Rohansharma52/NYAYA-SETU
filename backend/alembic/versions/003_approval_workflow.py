"""Add approval workflow tables (applications, stage_history, evc_tasks, undertakings, document_records).

Revision ID: 003
Revises: 002
Create Date: 2026-10-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # 1. applications
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_number', sa.String(length=50), nullable=False, unique=True),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column(
            'application_type',
            sa.Enum(
                'new_institution', 'program_approval', 'intake_increase',
                'program_closure', 'conversion', 'renewal',
                name='applicationtype',
            ),
            nullable=False,
        ),
        sa.Column(
            'current_stage',
            sa.Enum(
                'submitted', 'scrutiny', 'deficiency_raised', 'deficiency_rectified',
                'evc_eligible', 'evc_scheduled', 'evc_completed', 'sac_shc',
                'approved', 'rejected', 'withdrawn',
                name='applicationstage',
            ),
            nullable=False,
        ),
        sa.Column('applied_year', sa.Integer(), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('assigned_officer_id', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_stage_change_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('blocks_workflow', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('escalation_flag', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('priority_score', sa.Integer(), nullable=True, server_default=sa.text('5')),
        sa.Column('data_note', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id']),
        sa.ForeignKeyConstraint(['assigned_officer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_applications_id', 'applications', ['id'])
    op.create_index('ix_applications_application_number', 'applications', ['application_number'], unique=True)
    op.create_index('ix_applications_institution_id', 'applications', ['institution_id'])
    op.create_index('ix_applications_current_stage', 'applications', ['current_stage'])

    # 2. stage_history
    op.create_table(
        'stage_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column(
            'from_stage',
            sa.Enum(
                'submitted', 'scrutiny', 'deficiency_raised', 'deficiency_rectified',
                'evc_eligible', 'evc_scheduled', 'evc_completed', 'sac_shc',
                'approved', 'rejected', 'withdrawn',
                name='applicationstage', create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            'to_stage',
            sa.Enum(
                'submitted', 'scrutiny', 'deficiency_raised', 'deficiency_rectified',
                'evc_eligible', 'evc_scheduled', 'evc_completed', 'sac_shc',
                'approved', 'rejected', 'withdrawn',
                name='applicationstage', create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('performed_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stage_history_id', 'stage_history', ['id'])
    op.create_index('ix_stage_history_application_id', 'stage_history', ['application_id'])

    # 3. evc_tasks
    op.create_table(
        'evc_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'scheduled', 'completed', 'cancelled', 'rescheduled', name='evcstatus'),
            nullable=False,
        ),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expert_names', sa.JSON(), nullable=True),
        sa.Column('visit_report_summary', sa.Text(), nullable=True),
        sa.Column('outcome', sa.String(length=100), nullable=True),
        sa.Column('rescheduled_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rescheduled_reason', sa.Text(), nullable=True),
        sa.Column('assigned_coordinator_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id']),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id']),
        sa.ForeignKeyConstraint(['assigned_coordinator_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evc_tasks_id', 'evc_tasks', ['id'])
    op.create_index('ix_evc_tasks_application_id', 'evc_tasks', ['application_id'])
    op.create_index('ix_evc_tasks_institution_id', 'evc_tasks', ['institution_id'])
    op.create_index('ix_evc_tasks_status', 'evc_tasks', ['status'])

    # 4. undertakings
    op.create_table(
        'undertakings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=True),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column('undertaking_type', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by_id', sa.Integer(), nullable=True),
        sa.Column(
            'status',
            sa.Enum(
                'active', 'pending_submission', 'submitted', 'verified', 'returned', 'expired',
                name='undertakingstatus',
            ),
            nullable=False,
        ),
        sa.Column('submission_notes', sa.Text(), nullable=True),
        sa.Column('return_reason', sa.Text(), nullable=True),
        sa.Column('evidence_filename', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id']),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id']),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_undertakings_id', 'undertakings', ['id'])
    op.create_index('ix_undertakings_application_id', 'undertakings', ['application_id'])
    op.create_index('ix_undertakings_institution_id', 'undertakings', ['institution_id'])
    op.create_index('ix_undertakings_status', 'undertakings', ['status'])

    # 5. document_records
    op.create_table(
        'document_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=True),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column(
            'category',
            sa.Enum(
                'lease', 'noc', 'affidavit', 'inspection_report',
                'approval_letter', 'compliance_certificate', 'other',
                name='documentcategory',
            ),
            nullable=False,
        ),
        sa.Column('document_name', sa.String(length=500), nullable=False),
        sa.Column('issuing_authority', sa.String(length=300), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('is_expired', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('renewal_pending', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('verified', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('verified_by_id', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('filename', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id']),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id']),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_document_records_id', 'document_records', ['id'])
    op.create_index('ix_document_records_application_id', 'document_records', ['application_id'])
    op.create_index('ix_document_records_institution_id', 'document_records', ['institution_id'])
    op.create_index('ix_document_records_category', 'document_records', ['category'])


def downgrade():
    # Drop in reverse order
    op.drop_index('ix_document_records_category', table_name='document_records')
    op.drop_index('ix_document_records_institution_id', table_name='document_records')
    op.drop_index('ix_document_records_application_id', table_name='document_records')
    op.drop_index('ix_document_records_id', table_name='document_records')
    op.drop_table('document_records')

    op.drop_index('ix_undertakings_status', table_name='undertakings')
    op.drop_index('ix_undertakings_institution_id', table_name='undertakings')
    op.drop_index('ix_undertakings_application_id', table_name='undertakings')
    op.drop_index('ix_undertakings_id', table_name='undertakings')
    op.drop_table('undertakings')

    op.drop_index('ix_evc_tasks_status', table_name='evc_tasks')
    op.drop_index('ix_evc_tasks_institution_id', table_name='evc_tasks')
    op.drop_index('ix_evc_tasks_application_id', table_name='evc_tasks')
    op.drop_index('ix_evc_tasks_id', table_name='evc_tasks')
    op.drop_table('evc_tasks')

    op.drop_index('ix_stage_history_application_id', table_name='stage_history')
    op.drop_index('ix_stage_history_id', table_name='stage_history')
    op.drop_table('stage_history')

    op.drop_index('ix_applications_current_stage', table_name='applications')
    op.drop_index('ix_applications_institution_id', table_name='applications')
    op.drop_index('ix_applications_application_number', table_name='applications')
    op.drop_index('ix_applications_id', table_name='applications')
    op.drop_table('applications')

    # Drop named enum types (PostgreSQL keeps them after table drop)
    op.execute('DROP TYPE IF EXISTS applicationstage')
    op.execute('DROP TYPE IF EXISTS applicationtype')
    op.execute('DROP TYPE IF EXISTS evcstatus')
    op.execute('DROP TYPE IF EXISTS undertakingstatus')
    op.execute('DROP TYPE IF EXISTS documentcategory')
