"""harden_database_indexes

Revision ID: c0e81b379d42
Revises: a30798731d0a
Create Date: 2026-11-20 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0e81b379d42'
down_revision: Union[str, Sequence[str], None] = 'a30798731d0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply performance composite indexes and verify sync_events user_cursor index."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1. messages (conversation_id, created_at)
    existing_msg_indexes = [idx['name'] for idx in insp.get_indexes('messages')]
    if 'ix_messages_conv_created' not in existing_msg_indexes:
        op.create_index(
            'ix_messages_conv_created',
            'messages',
            ['conversation_id', 'created_at'],
            unique=False
        )

    # 2. tasks (user_id, status)
    existing_task_indexes = [idx['name'] for idx in insp.get_indexes('tasks')]
    if 'ix_tasks_user_status' not in existing_task_indexes:
        op.create_index(
            'ix_tasks_user_status',
            'tasks',
            ['user_id', 'status'],
            unique=False
        )

    # 3. memories (user_id, is_archived)
    existing_mem_indexes = [idx['name'] for idx in insp.get_indexes('memories')]
    if 'ix_memories_user_archived' not in existing_mem_indexes:
        op.create_index(
            'ix_memories_user_archived',
            'memories',
            ['user_id', 'is_archived'],
            unique=False
        )

    # 4. sync_events (user_id, cursor) - idempotent safeguard
    existing_sync_indexes = [idx['name'] for idx in insp.get_indexes('sync_events')]
    if 'ix_sync_events_user_cursor' not in existing_sync_indexes:
        op.create_index(
            'ix_sync_events_user_cursor',
            'sync_events',
            ['user_id', 'cursor'],
            unique=False
        )


def downgrade() -> None:
    """Drop performance composite indexes."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    existing_mem_indexes = [idx['name'] for idx in insp.get_indexes('memories')]
    if 'ix_memories_user_archived' in existing_mem_indexes:
        op.drop_index('ix_memories_user_archived', table_name='memories')

    existing_task_indexes = [idx['name'] for idx in insp.get_indexes('tasks')]
    if 'ix_tasks_user_status' in existing_task_indexes:
        op.drop_index('ix_tasks_user_status', table_name='tasks')

    existing_msg_indexes = [idx['name'] for idx in insp.get_indexes('messages')]
    if 'ix_messages_conv_created' in existing_msg_indexes:
        op.drop_index('ix_messages_conv_created', table_name='messages')
