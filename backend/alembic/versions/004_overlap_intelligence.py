"""Overlap intelligence: institution-level coordination + case attachments.

Revision ID: 004
Revises: 003
Create Date: 2026-10-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('coordination_items', sa.Column('institution_id', sa.Integer(), nullable=True))
    op.add_column('coordination_items', sa.Column('lead_bureau_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_coord_institution', 'coordination_items', 'institutions', ['institution_id'], ['id'])
    op.create_foreign_key('fk_coord_lead_bureau', 'coordination_items', 'bureaus', ['lead_bureau_id'], ['id'])
    op.create_index('ix_coordination_items_institution_id', 'coordination_items', ['institution_id'])

    op.create_table(
        'case_attachments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_id', sa.Integer(), sa.ForeignKey('case_actions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_case_attachments_case_id', 'case_attachments', ['case_id'])


def downgrade():
    op.drop_index('ix_case_attachments_case_id', table_name='case_attachments')
    op.drop_table('case_attachments')
    op.drop_index('ix_coordination_items_institution_id', table_name='coordination_items')
    op.drop_constraint('fk_coord_lead_bureau', 'coordination_items', type_='foreignkey')
    op.drop_constraint('fk_coord_institution', 'coordination_items', type_='foreignkey')
    op.drop_column('coordination_items', 'lead_bureau_id')
    op.drop_column('coordination_items', 'institution_id')
