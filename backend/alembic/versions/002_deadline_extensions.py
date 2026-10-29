"""Add deadline_extension_requests table.

Revision ID: 002
Revises: 001
Create Date: 2026-10-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'deadline_extension_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('requested_by_id', sa.Integer(), nullable=False),
        sa.Column('original_due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requested_due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_deadline_extension_requests_case_id',
        'deadline_extension_requests',
        ['case_id']
    )


def downgrade():
    op.drop_index('ix_deadline_extension_requests_case_id',
                  table_name='deadline_extension_requests')
    op.drop_table('deadline_extension_requests')
