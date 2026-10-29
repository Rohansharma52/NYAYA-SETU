"""Initial schema — core NYAYA SETU tables.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='bureau_officer'),
        sa.Column('account_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('bureau_id', sa.Integer(), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('designation', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)

    # bureaus
    op.create_table(
        'bureaus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('head_name', sa.String(length=255), nullable=True),
        sa.Column('head_email', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bureaus_code', 'bureaus', ['code'], unique=True)
    op.create_index('ix_bureaus_id', 'bureaus', ['id'], unique=False)

    # institutions
    op.create_table(
        'institutions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical_name', sa.String(length=500), nullable=False),
        sa.Column('short_name', sa.String(length=100), nullable=True),
        sa.Column('institution_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('pincode', sa.String(length=10), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('data_source', sa.String(length=100), nullable=True),
        sa.Column('source_last_synced', sa.DateTime(timezone=True), nullable=True),
        sa.Column('import_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_institutions_canonical_name', 'institutions', ['canonical_name'], unique=False)
    op.create_index('ix_institutions_id', 'institutions', ['id'], unique=False)
    op.create_index('ix_institutions_region', 'institutions', ['region'], unique=False)
    op.create_index('ix_institutions_state', 'institutions', ['state'], unique=False)

    # institution_identifiers
    op.create_table(
        'institution_identifiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column('id_type', sa.String(length=50), nullable=False),
        sa.Column('id_value', sa.String(length=255), nullable=False),
        sa.Column('source_system', sa.String(length=100), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('verified_by_id', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_institution_identifiers_id', 'institution_identifiers', ['id'], unique=False)

    # import_jobs  (column names match app/models/import_job.py)
    op.create_table(
        'import_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('import_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('total_rows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('valid_rows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_rows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('skipped_rows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('imported_rows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_summary', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('imported_by_id', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['imported_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_import_jobs_id', 'import_jobs', ['id'], unique=False)

    # cases
    op.create_table(
        'cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_number', sa.String(length=50), nullable=False),
        sa.Column('source_case_id', sa.String(length=255), nullable=True),
        sa.Column('source_system', sa.String(length=100), nullable=True),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column('bureau_id', sa.Integer(), nullable=True),
        sa.Column('assigned_officer_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=200), nullable=False),
        sa.Column('sub_category', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='received'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('complainant_name', sa.String(length=255), nullable=True),
        sa.Column('complainant_email', sa.String(length=255), nullable=True),
        sa.Column('complainant_phone', sa.String(length=20), nullable=True),
        sa.Column('received_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('disposed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_action_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_action', sa.Text(), nullable=True),
        sa.Column('next_action_owner_id', sa.Integer(), nullable=True),
        sa.Column('source_last_synced', sa.DateTime(timezone=True), nullable=True),
        sa.Column('import_job_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_officer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['bureau_id'], ['bureaus.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['import_job_id'], ['import_jobs.id']),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id']),
        sa.ForeignKeyConstraint(['next_action_owner_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cases_bureau_id', 'cases', ['bureau_id'], unique=False)
    op.create_index('ix_cases_case_number', 'cases', ['case_number'], unique=True)
    op.create_index('ix_cases_category', 'cases', ['category'], unique=False)
    op.create_index('ix_cases_id', 'cases', ['id'], unique=False)
    op.create_index('ix_cases_institution_id', 'cases', ['institution_id'], unique=False)
    op.create_index('ix_cases_source_case_id', 'cases', ['source_case_id'], unique=False)
    op.create_index('ix_cases_status', 'cases', ['status'], unique=False)

    # case_actions
    op.create_table(
        'case_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('old_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=True),
        sa.Column('performed_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_case_actions_id', 'case_actions', ['id'], unique=False)

    # case_assignments
    op.create_table(
        'case_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('assigned_to_id', sa.Integer(), nullable=False),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column('bureau_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id']),
        sa.ForeignKeyConstraint(['bureau_id'], ['bureaus.id']),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_case_assignments_id', 'case_assignments', ['id'], unique=False)

    # case_relationships
    op.create_table(
        'case_relationships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_a_id', sa.Integer(), nullable=False),
        sa.Column('case_b_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('reasons', sa.JSON(), nullable=True),
        sa.Column('matching_evidence', sa.JSON(), nullable=True),
        sa.Column('algorithm_version', sa.String(length=50), nullable=True, server_default='v1.0'),
        sa.Column('review_status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['case_a_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['case_b_id'], ['cases.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_case_relationships_case_a_id', 'case_relationships', ['case_a_id'], unique=False)
    op.create_index('ix_case_relationships_case_b_id', 'case_relationships', ['case_b_id'], unique=False)
    op.create_index('ix_case_relationships_id', 'case_relationships', ['id'], unique=False)
    op.create_index('ix_case_relationships_review_status', 'case_relationships', ['review_status'], unique=False)

    # relationship_reviews
    op.create_table(
        'relationship_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('relationship_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('corrected_type', sa.String(length=50), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['relationship_id'], ['case_relationships.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_relationship_reviews_id', 'relationship_reviews', ['id'], unique=False)
    op.create_index('ix_relationship_reviews_relationship_id', 'relationship_reviews', ['relationship_id'], unique=False)

    # coordination_items
    op.create_table(
        'coordination_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reference_number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_relationship_id', sa.Integer(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='detected'),
        sa.Column('decision', sa.String(length=50), nullable=True),
        sa.Column('decision_rationale', sa.Text(), nullable=True),
        sa.Column('decision_by_id', sa.Integer(), nullable=True),
        sa.Column('decision_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledge_by', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closure_notes', sa.Text(), nullable=True),
        sa.Column('closed_by_id', sa.Integer(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_exception_closure', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('exception_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['closed_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['decision_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['source_relationship_id'], ['case_relationships.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_coordination_items_id', 'coordination_items', ['id'], unique=False)
    op.create_index('ix_coordination_items_reference_number', 'coordination_items', ['reference_number'], unique=True)
    op.create_index('ix_coordination_items_status', 'coordination_items', ['status'], unique=False)

    # coordination_participants
    op.create_table(
        'coordination_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('coordination_item_id', sa.Integer(), nullable=False),
        sa.Column('bureau_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('role_in_coordination', sa.String(length=100), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['bureau_id'], ['bureaus.id']),
        sa.ForeignKeyConstraint(['coordination_item_id'], ['coordination_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_coordination_participants_id', 'coordination_participants', ['id'], unique=False)

    # coordination_tasks
    op.create_table(
        'coordination_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('coordination_item_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assigned_to_id', sa.Integer(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by_id', sa.Integer(), nullable=True),
        sa.Column('completion_notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id']),
        sa.ForeignKeyConstraint(['completed_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['coordination_item_id'], ['coordination_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_coordination_tasks_coordination_item_id', 'coordination_tasks', ['coordination_item_id'], unique=False)
    op.create_index('ix_coordination_tasks_id', 'coordination_tasks', ['id'], unique=False)

    # transfer_requests  (column names match app/models/transfer.py)
    op.create_table(
        'transfer_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('from_bureau_id', sa.Integer(), nullable=True),
        sa.Column('to_bureau_id', sa.Integer(), nullable=True),
        sa.Column('from_officer_id', sa.Integer(), nullable=True),
        sa.Column('to_officer_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='requested'),
        sa.Column('response_notes', sa.Text(), nullable=True),
        sa.Column('requested_by_id', sa.Integer(), nullable=True),
        sa.Column('responded_by_id', sa.Integer(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id']),
        sa.ForeignKeyConstraint(['from_bureau_id'], ['bureaus.id']),
        sa.ForeignKeyConstraint(['from_officer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['responded_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['to_bureau_id'], ['bureaus.id']),
        sa.ForeignKeyConstraint(['to_officer_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transfer_requests_id', 'transfer_requests', ['id'], unique=False)

    # notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('notification_type', sa.String(length=100), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=True, server_default='medium'),
        sa.Column('is_read', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('link_url', sa.String(length=500), nullable=True),
        sa.Column('related_case_id', sa.Integer(), nullable=True),
        sa.Column('related_coordination_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['related_case_id'], ['cases.id']),
        sa.ForeignKeyConstraint(['related_coordination_id'], ['coordination_items.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_id', 'notifications', ['id'], unique=False)
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)

    # audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=200), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('old_data', sa.JSON(), nullable=True),
        sa.Column('new_data', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_events_action', 'audit_events', ['action'], unique=False)
    op.create_index('ix_audit_events_id', 'audit_events', ['id'], unique=False)
    op.create_index('ix_audit_events_resource_id', 'audit_events', ['resource_id'], unique=False)
    op.create_index('ix_audit_events_resource_type', 'audit_events', ['resource_type'], unique=False)

    # deadline_rules  (column names match app/models/deadline.py)
    op.create_table(
        'deadline_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('applies_to', sa.String(length=100), nullable=False),
        sa.Column('applies_to_value', sa.String(length=200), nullable=True),
        sa.Column('days_to_resolve', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('escalation_after_days', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_deadline_rules_id', 'deadline_rules', ['id'], unique=False)

    # case_deadlines  (column names match app/models/deadline.py)
    op.create_table(
        'case_deadlines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('deadline_rule_id', sa.Integer(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_overdue', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_extended', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('extension_reason', sa.Text(), nullable=True),
        sa.Column('extended_by_id', sa.Integer(), nullable=True),
        sa.Column('extended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['deadline_rule_id'], ['deadline_rules.id']),
        sa.ForeignKeyConstraint(['extended_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_case_deadlines_id', 'case_deadlines', ['id'], unique=False)

    # import_rows  (column names match app/models/import_job.py)
    op.create_table(
        'import_rows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('created_resource_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['import_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_import_rows_id', 'import_rows', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('import_rows')
    op.drop_table('case_deadlines')
    op.drop_table('deadline_rules')
    op.drop_table('audit_events')
    op.drop_table('notifications')
    op.drop_table('transfer_requests')
    op.drop_table('coordination_tasks')
    op.drop_table('coordination_participants')
    op.drop_table('coordination_items')
    op.drop_table('relationship_reviews')
    op.drop_table('case_relationships')
    op.drop_table('case_assignments')
    op.drop_table('case_actions')
    op.drop_table('cases')
    op.drop_table('import_jobs')
    op.drop_table('institution_identifiers')
    op.drop_table('institutions')
    op.drop_table('bureaus')
    op.drop_table('users')
