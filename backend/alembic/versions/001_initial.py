"""Initial migration - Create all tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from pgvector.sqlalchemy import Vector

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    user_status_enum = ENUM('ACTIVE', 'SUSPENDED', 'DELETED', name='user_status', create_type=True)
    wallet_status_enum = ENUM('ACTIVE', 'FROZEN', 'CLOSED', name='wallet_status', create_type=True)
    transaction_type_enum = ENUM('PAYMENT', 'REFUND', 'TOPUP', name='transaction_type', create_type=True)
    transaction_status_enum = ENUM('PENDING', 'SUCCESS', 'FAILED', 'REVERSED', name='transaction_status', create_type=True)
    device_status_enum = ENUM('ACTIVE', 'REVOKED', 'PENDING', name='device_status', create_type=True)

    # Users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True, unique=True),
        sa.Column('status', user_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_users_status', 'users', ['status'])
    op.create_index('ix_users_created_at', 'users', ['created_at'])

    # Biometric templates table
    op.create_table(
        'biometric_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('embedding', Vector(512), nullable=False),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_biometric_templates_user_id', 'biometric_templates', ['user_id'])
    op.create_index('ix_biometric_templates_model_version', 'biometric_templates', ['model_version'])
    op.create_index('ix_biometric_templates_created_at', 'biometric_templates', ['created_at'])

    # Wallets table
    op.create_table(
        'wallets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('balance', sa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('status', wallet_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_wallets_user_id', 'wallets', ['user_id'])
    op.create_index('ix_wallets_status', 'wallets', ['status'])

    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('transaction_reference', sa.String(50), nullable=False, unique=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('wallet_id', UUID(as_uuid=True), sa.ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('merchant_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('transaction_type', transaction_type_enum, nullable=False),
        sa.Column('status', transaction_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('idempotency_key', sa.String(100), nullable=True, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('ix_transactions_wallet_id', 'transactions', ['wallet_id'])
    op.create_index('ix_transactions_merchant_id', 'transactions', ['merchant_id'])
    op.create_index('ix_transactions_status', 'transactions', ['status'])
    op.create_index('ix_transactions_type', 'transactions', ['transaction_type'])
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'])
    op.create_index('ix_transactions_reference', 'transactions', ['transaction_reference'], unique=True)
    op.create_index('ix_transactions_idempotency_key', 'transactions', ['idempotency_key'], unique=True)

    # Devices table
    op.create_table(
        'devices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('device_name', sa.String(255), nullable=False),
        sa.Column('device_key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('status', device_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', sa.Text(), nullable=True),
    )
    op.create_index('ix_devices_status', 'devices', ['status'])
    op.create_index('ix_devices_created_at', 'devices', ['created_at'])
    op.create_index('ix_devices_device_key_hash', 'devices', ['device_key_hash'], unique=True)

    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('device_id', UUID(as_uuid=True), sa.ForeignKey('devices.id', ondelete='SET NULL'), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=False),
        sa.Column('metadata', JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_device_id', 'audit_logs', ['device_id'])
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('devices')
    op.drop_table('transactions')
    op.drop_table('wallets')
    op.drop_table('biometric_templates')
    op.drop_table('users')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS user_status')
    op.execute('DROP TYPE IF EXISTS wallet_status')
    op.execute('DROP TYPE IF EXISTS transaction_type')
    op.execute('DROP TYPE IF EXISTS transaction_status')
    op.execute('DROP TYPE IF EXISTS device_status')