"""add versioning

Revision ID: 004
Revises: 2ee9e87ede55
Create Date: 2025-01-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '004'
down_revision = '2ee9e87ede55'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('contracts')]
    
    if 'version' not in columns:
        op.add_column('contracts', sa.Column('version', sa.String(20), nullable=True))
        op.execute("UPDATE contracts SET version = '1.0.0' WHERE version IS NULL")
        op.alter_column('contracts', 'version', nullable=False)


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('contracts')]
    
    if 'version' in columns:
        op.drop_column('contracts', 'version')
