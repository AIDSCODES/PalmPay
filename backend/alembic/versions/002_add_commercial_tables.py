"""Add business, staff, payment_device, payment_request, consent, subscription tables

Revision ID: 002
Revises: 001_initial
Create Date: 2026-10-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from pgvector.sqlalchemy import Vector

revision = '002'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    business_status_enum = ENUM('PENDING', 'ACTIVE', 'SUSPENDED', 'REJECTED', name='business_status', create_type=True)
    branch_status_enum = ENUM('ACTIVE', 'INACTIVE', name='branch_status', create_type=True)
    staff_role_enum = ENUM('OWNER', 'MANAGER', 'CASHIER', 'VIEWER', name='staff_role', create_type=True)
    staff_status_enum = ENUM('ACTIVE', 'INACTIVE', 'REVOKED', name='staff_status', create_type=True)
    device_type_enum = ENUM('ESP32', 'MOBILE', 'KIOSK', name='device_type', create_type=True)
    pairing_status_enum = ENUM('UNPAIRED', 'PAIRED', 'PENDING', name='pairing_status', create_type=True)
    connection_status_enum = ENUM('ONLINE', 'OFFLINE', name='connection_status', create_type=True)
    payment_request_status_enum = ENUM('CREATED', 'SENT_TO_DEVICE', 'AWAITING_CUSTOMER', 'PROCESSING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'EXPIRED', name='payment_request_status', create_type=True)
    consent_type_enum = ENUM('BIOMETRIC_ENROLLMENT', 'BIOMETRIC_IDENTIFICATION', 'DATA_PROCESSING', 'MARKETING', 'PAYMENT_PROCESSING', name='consent_type', create_type=True)
    consent_status_enum = ENUM('GIVEN', 'WITHDRAWN', 'EXPIRED', name='consent_status', create_type=True)
    subscription_plan_enum = ENUM('FREE', 'BASIC', 'PROFESSIONAL', 'ENTERPRISE', name='subscription_plan', create_type=True)
    subscription_status_enum = ENUM('ACTIVE', 'PAST_DUE', 'CANCELLED', 'EXPIRED', 'TRIALING', name='subscription_status', create_type=True)
    billing_interval_enum = ENUM('MONTHLY', 'YEARLY', name='billing_interval', create_type=True)

    # Businesses table
    op.create_table(
        'businesses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('legal_name', sa.String(255), nullable=True),
        sa.Column('business_type', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', business_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('verification_status', sa.String(50), nullable=False, server_default='unverified'),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('gst_number', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_businesses_status', 'businesses', ['status'])
    op.create_index('ix_businesses_owner_id', 'businesses', ['owner_id'])
    op.create_index('ix_businesses_verification_status', 'businesses', ['verification_status'])

    # Branches table
    op.create_table(
        'branches',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('pincode', sa.String(20), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('status', branch_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_branches_business_id', 'branches', ['business_id'])
    op.create_index('ix_branches_status', 'branches', ['status'])

    # Business staff table
    op.create_table(
        'business_staff',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', staff_role_enum, nullable=False, server_default='CASHIER'),
        sa.Column('status', staff_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('invited_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('business_id', 'user_id', name='uq_business_staff_user'),
    )
    op.create_index('ix_business_staff_business_id', 'business_staff', ['business_id'])
    op.create_index('ix_business_staff_user_id', 'business_staff', ['user_id'])
    op.create_index('ix_business_staff_branch_id', 'business_staff', ['branch_id'])
    op.create_index('ix_business_staff_status', 'business_staff', ['status'])

    # Payment devices table
    op.create_table(
        'payment_devices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('device_name', sa.String(255), nullable=False),
        sa.Column('device_type', device_type_enum, nullable=False, server_default='ESP32'),
        sa.Column('firmware_version', sa.String(50), nullable=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('device_key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('pairing_status', pairing_status_enum, nullable=False, server_default='UNPAIRED'),
        sa.Column('paired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paired_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('connection_status', connection_status_enum, nullable=False, server_default='OFFLINE'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_payment_devices_business_id', 'payment_devices', ['business_id'])
    op.create_index('ix_payment_devices_branch_id', 'payment_devices', ['branch_id'])
    op.create_index('ix_payment_devices_pairing_status', 'payment_devices', ['pairing_status'])
    op.create_index('ix_payment_devices_connection_status', 'payment_devices', ['connection_status'])
    op.create_index('ix_payment_devices_device_key_hash', 'payment_devices', ['device_key_hash'], unique=True)

    # Payment requests table
    op.create_table(
        'payment_requests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('request_reference', sa.String(50), nullable=False, unique=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', UUID(as_uuid=True), sa.ForeignKey('branches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('device_id', UUID(as_uuid=True), sa.ForeignKey('payment_devices.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', payment_request_status_enum, nullable=False, server_default='CREATED'),
        sa.Column('idempotency_key', sa.String(100), nullable=True, unique=True),
        sa.Column('sent_to_device_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('device_acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('customer_identified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('customer_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('transaction_id', UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('request_metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Indexes are defined in the model's __table_args__ and will be created by SQLAlchemy

    # Consent records table
    op.create_table(
        'consent_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('consent_type', consent_type_enum, nullable=False),
        sa.Column('policy_version', sa.String(50), nullable=False),
        sa.Column('status', consent_status_enum, nullable=False, server_default='GIVEN'),
        sa.Column('consent_given_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('revocation_reason', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('policy_content', sa.Text(), nullable=True),
        sa.Column('consent_metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Indexes are defined in the model's __table_args__ and will be created by SQLAlchemy

    # Subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan', subscription_plan_enum, nullable=False, server_default='FREE'),
        sa.Column('status', subscription_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('billing_interval', billing_interval_enum, nullable=False, server_default='MONTHLY'),
        sa.Column('amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('trial_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('provider_subscription_id', sa.String(255), nullable=True),
        sa.Column('provider_customer_id', sa.String(255), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('subscription_metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Indexes are defined in the model's __table_args__ and will be created by SQLAlchemy


def downgrade() -> None:
    op.drop_table('subscriptions')
    op.drop_table('consent_records')
    op.drop_table('payment_requests')
    op.drop_table('payment_devices')
    op.drop_table('business_staff')
    op.drop_table('branches')
    op.drop_table('businesses')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS billing_interval')
    op.execute('DROP TYPE IF EXISTS subscription_status')
    op.execute('DROP TYPE IF EXISTS subscription_plan')
    op.execute('DROP TYPE IF EXISTS consent_status')
    op.execute('DROP TYPE IF EXISTS consent_type')
    op.execute('DROP TYPE IF EXISTS payment_request_status')
    op.execute('DROP TYPE IF EXISTS connection_status')
    op.execute('DROP TYPE IF EXISTS pairing_status')
    op.execute('DROP TYPE IF EXISTS device_type')
    op.execute('DROP TYPE IF EXISTS staff_status')
    op.execute('DROP TYPE IF EXISTS staff_role')
    op.execute('DROP TYPE IF EXISTS branch_status')
    op.execute('DROP TYPE IF EXISTS business_status')