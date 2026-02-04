-- ═══════════════════════════════════════════════════════════════════════════════
-- V1.0.0: Create OMEN Persistence Schemas
-- ═══════════════════════════════════════════════════════════════════════════════
--
-- Creates the 4-schema architecture for OMEN data persistence:
--   - demo: Development/demo signals (MOCK, REAL, HYBRID)
--   - live: Production signals (REAL only, blocked until 80%+ coverage)
--   - audit: Immutable audit trail (INSERT only, no UPDATE/DELETE)
--   - system: System configuration and metadata
--
-- ═══════════════════════════════════════════════════════════════════════════════

-- Create schemas
CREATE SCHEMA IF NOT EXISTS demo;
CREATE SCHEMA IF NOT EXISTS live;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS system;

-- Add schema comments for documentation
COMMENT ON SCHEMA demo IS 'Development and demo signals - accepts MOCK, REAL, and HYBRID source types';
COMMENT ON SCHEMA live IS 'Production signals - REAL source type only, gated by 80% real source coverage';
COMMENT ON SCHEMA audit IS 'Immutable audit trail - INSERT only, UPDATE/DELETE blocked by triggers';
COMMENT ON SCHEMA system IS 'System configuration, source registry, and operational metadata';

-- Create custom types for source attestation
DO $$ BEGIN
    CREATE TYPE source_type AS ENUM ('REAL', 'MOCK', 'HYBRID');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE verification_method AS ENUM (
        'API_RESPONSE_HASH',
        'CERTIFICATE_CHAIN',
        'SIGNATURE_VERIFICATION',
        'TIMESTAMP_VALIDATION',
        'MOCK_SOURCE_REGISTRY',
        'MANUAL_OVERRIDE'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE gate_decision AS ENUM ('ALLOW', 'BLOCK');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE operation_type AS ENUM ('INSERT', 'UPDATE', 'DELETE', 'UPSERT');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
