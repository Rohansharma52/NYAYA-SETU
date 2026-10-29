"""Remove the legacy approval-workflow tables (applications, EVC, undertakings, documents).

They belonged to an earlier prototype direction and are not part of PS 26264.

Revision ID: 005
Revises: 004
"""
import importlib.util
import os

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def _migration_003():
    path = os.path.join(os.path.dirname(__file__), '003_approval_workflow.py')
    spec = importlib.util.spec_from_file_location('migration_003', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upgrade():
    _migration_003().downgrade()


def downgrade():
    _migration_003().upgrade()
