"""create_cross_device_sync_tables

Revision ID: a30798731d0a
Revises: 322b6c8a37b0
Create Date: 2026-11-20 12:50:51.797291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a30798731d0a'
down_revision: Union[str, Sequence[str], None] = '322b6c8a37b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include Phase 09 cross-device sync tables."""
    # 1. sync_events table
    op.create_table(
        'sync_events',
        sa.Column('cursor', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('origin_device_id', sa.String(length=36), nullable=True),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('cursor')
    )
    with op.batch_alter_table('sync_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_sync_events_cursor'), ['cursor'], unique=False)
        batch_op.create_index(batch_op.f('ix_sync_events_event_id'), ['event_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_sync_events_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_sync_events_entity_type'), ['entity_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_sync_events_entity_id'), ['entity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_sync_events_origin_device_id'), ['origin_device_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_sync_events_created_at'), ['created_at'], unique=False)
        batch_op.create_index('ix_sync_events_user_cursor', ['user_id', 'cursor'], unique=False)

    # 2. user_sync_settings table
    op.create_table(
        'user_sync_settings',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('sync_mode', sa.String(length=20), nullable=False, server_default='standalone'),
        sa.Column('auto_sync_interval_seconds', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('conflict_resolution', sa.String(length=30), nullable=False, server_default='last_write_wins'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )

    # 3. device_sync_cursors table
    op.create_table(
        'device_sync_cursors',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('device_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('last_acknowledged_cursor', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id', 'user_id', name='uq_device_sync_cursors_dev_user')
    )
    with op.batch_alter_table('device_sync_cursors', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_device_sync_cursors_device_id'), ['device_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_device_sync_cursors_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema by dropping sync tables."""
    with op.batch_alter_table('device_sync_cursors', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_device_sync_cursors_user_id'))
        batch_op.drop_index(batch_op.f('ix_device_sync_cursors_device_id'))
    op.drop_table('device_sync_cursors')

    op.drop_table('user_sync_settings')

    with op.batch_alter_table('sync_events', schema=None) as batch_op:
        batch_op.drop_index('ix_sync_events_user_cursor')
        batch_op.drop_index(batch_op.f('ix_sync_events_created_at'))
        batch_op.drop_index(batch_op.f('ix_sync_events_origin_device_id'))
        batch_op.drop_index(batch_op.f('ix_sync_events_entity_id'))
        batch_op.drop_index(batch_op.f('ix_sync_events_entity_type'))
        batch_op.drop_index(batch_op.f('ix_sync_events_user_id'))
        batch_op.drop_index(batch_op.f('ix_sync_events_event_id'))
        batch_op.drop_index(batch_op.f('ix_sync_events_cursor'))
    op.drop_table('sync_events')
