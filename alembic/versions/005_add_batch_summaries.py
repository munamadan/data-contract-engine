"""add batch summaries

Revision ID: 005
Revises: 004
Create Date: 2025-01-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'batch_summaries',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('batch_id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('total_records', sa.Integer(), nullable=False),
        sa.Column('passed', sa.Integer(), nullable=False),
        sa.Column('failed', sa.Integer(), nullable=False),
        sa.Column('pass_rate', sa.Float(), nullable=False),
        sa.Column('execution_time_ms', sa.Float(), nullable=False),
        sa.Column('errors_summary', sa.JSON(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_batch_summaries_batch_id', 'batch_summaries', ['batch_id'], unique=True)
    op.create_index('ix_batch_summaries_contract_id', 'batch_summaries', ['contract_id'], unique=False)
    op.create_index('ix_batch_summaries_processed_at', 'batch_summaries', ['processed_at'], unique=False)


def downgrade():
    op.drop_index('ix_batch_summaries_processed_at', 'batch_summaries')
    op.drop_index('ix_batch_summaries_contract_id', 'batch_summaries')
    op.drop_index('ix_batch_summaries_batch_id', 'batch_summaries')
    op.drop_table('batch_summaries')