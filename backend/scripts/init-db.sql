-- Database initialization script for Docker
-- This runs automatically when PostgreSQL container starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create enum types (will be created by alembic, but safe to have here)
DO $$ BEGIN
    CREATE TYPE user_status AS ENUM ('ACTIVE', 'SUSPENDED', 'DELETED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE wallet_status AS ENUM ('ACTIVE', 'FROZEN', 'CLOSED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE transaction_type AS ENUM ('PAYMENT', 'REFUND', 'TOPUP');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE transaction_status AS ENUM ('PENDING', 'SUCCESS', 'FAILED', 'REVERSED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE device_status AS ENUM ('ACTIVE', 'REVOKED', 'PENDING');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE palmpay TO palmpay;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO palmpay;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO palmpay;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO palmpay;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO palmpay;