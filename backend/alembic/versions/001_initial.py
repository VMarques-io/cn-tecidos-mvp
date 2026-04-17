"""Initial migration - create users, messages, fashion_flow_states tables"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users', sa.Column('id', UUID(as_uuid=True), nullable=False), sa.Column('remote_jid', sa.String(length=255), nullable=False), sa.Column('profile_type', sa.String(length=50), nullable=False), sa.Column('body_measurements', JSONB, nullable=True), sa.Column('created_at', sa.DateTime(), nullable=False), sa.Column('last_seen', sa.DateTime(), nullable=False), sa.PrimaryKeyConstraint('id'))
    op.create_index('ix_users_remote_jid', 'users', ['remote_jid'], unique=True)

    op.create_table('fashion_flow_states', sa.Column('id', UUID(as_uuid=True), nullable=False), sa.Column('user_id', UUID(as_uuid=True), nullable=False), sa.Column('current_step', sa.String(length=50), nullable=False), sa.Column('fabric_url', sa.String(length=500), nullable=True), sa.Column('fabric_name', sa.String(length=255), nullable=True), sa.Column('client_measurements', JSONB, nullable=True), sa.Column('garment_specs', JSONB, nullable=True), sa.Column('is_human_active', sa.Boolean(), nullable=False), sa.Column('updated_at', sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'), sa.PrimaryKeyConstraint('id'), sa.UniqueConstraint('user_id'))
    op.create_index('ix_fashion_flow_states_user_id', 'fashion_flow_states', ['user_id'], unique=False)

    op.create_table('messages', sa.Column('id', UUID(as_uuid=True), nullable=False), sa.Column('user_id', UUID(as_uuid=True), nullable=False), sa.Column('role', sa.String(length=20), nullable=False), sa.Column('message_type', sa.String(length=20), nullable=False), sa.Column('content', sa.Text(), nullable=False), sa.Column('media_url', sa.String(length=500), nullable=True), sa.Column('media_mime', sa.String(length=100), nullable=True), sa.Column('evolution_message_id', sa.String(length=255), nullable=True), sa.Column('created_at', sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'), sa.PrimaryKeyConstraint('id'))
    op.create_index('ix_messages_user_id', 'messages', ['user_id'], unique=False)
    op.create_index('ix_messages_created_at', 'messages', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_messages_created_at', table_name='messages')
    op.drop_index('ix_messages_user_id', table_name='messages')
    op.drop_table('messages')
    op.drop_index('ix_fashion_flow_states_user_id', table_name='fashion_flow_states')
    op.drop_table('fashion_flow_states')
    op.drop_index('ix_users_remote_jid', table_name='users')
    op.drop_table('users')
