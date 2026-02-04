-- ═══════════════════════════════════════════════════════════════════════════════
-- V1.0.1: Demo Schema Tables
-- ═══════════════════════════════════════════════════════════════════════════════
--
-- Creates tables in the demo schema for development and demonstration:
--   - signals: Primary signal storage
--   - raw_inputs: Raw API responses before processing
--   - ingestion_logs: Pipeline processing logs
--
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────────
-- demo.signals - Primary signal storage
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS demo.signals (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Signal identification
    signal_id VARCHAR(64) UNIQUE NOT NULL,
    source_event_id VARCHAR(128),
    trace_id VARCHAR(64),
    input_event_hash VARCHAR(64),
    
    -- Source attestation (required for schema routing)
    source_type source_type NOT NULL DEFAULT 'MOCK',
    attestation_id UUID,  -- FK to audit.source_attestations
    
    -- Signal content
    title TEXT NOT NULL,
    description TEXT,
    probability FLOAT CHECK (probability >= 0 AND probability <= 1),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    confidence_level VARCHAR(16),
    signal_type VARCHAR(32),
    status VARCHAR(16) DEFAULT 'ACTIVE',
    category VARCHAR(32),
    
    -- Structured data (JSONB for efficient querying)
    tags JSONB DEFAULT '[]'::jsonb,
    geographic JSONB,
    temporal JSONB,
    evidence JSONB DEFAULT '[]'::jsonb,
    
    -- Full signal payload
    payload JSONB NOT NULL,
    
    -- Timestamps
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Data provenance
    ingested_from VARCHAR(64),  -- Source adapter name
    api_response_hash VARCHAR(64)  -- Hash of raw API response
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- demo.raw_inputs - Raw API responses (72-hour retention)
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS demo.raw_inputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Source identification
    source_id VARCHAR(64) NOT NULL,
    source_type source_type NOT NULL,
    
    -- Raw data
    api_endpoint VARCHAR(512),
    request_headers JSONB,
    response_body JSONB NOT NULL,
    response_hash VARCHAR(64) NOT NULL,
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    signal_id VARCHAR(64),  -- Resulting signal if processed
    
    -- Metadata
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '72 hours'),
    
    -- For idempotency
    UNIQUE (source_id, response_hash)
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- demo.ingestion_logs - Pipeline processing logs (30-day retention)
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS demo.ingestion_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Request tracking
    trace_id VARCHAR(64) NOT NULL,
    request_id VARCHAR(64),
    
    -- Processing details
    source_id VARCHAR(64) NOT NULL,
    source_type source_type NOT NULL,
    stage VARCHAR(32) NOT NULL,  -- INGEST, VALIDATE, ENRICH, PERSIST, PUBLISH
    status VARCHAR(16) NOT NULL,  -- SUCCESS, FAILURE, SKIPPED
    
    -- Timing
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- Details
    input_count INTEGER DEFAULT 0,
    output_count INTEGER DEFAULT 0,
    error_message TEXT,
    error_details JSONB,
    metadata JSONB,
    
    -- Retention
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days')
);

-- Add table comments
COMMENT ON TABLE demo.signals IS 'Primary signal storage for development/demo mode';
COMMENT ON TABLE demo.raw_inputs IS 'Raw API responses before processing (72-hour retention)';
COMMENT ON TABLE demo.ingestion_logs IS 'Pipeline processing logs (30-day retention)';

-- Add column comments for key fields
COMMENT ON COLUMN demo.signals.source_type IS 'Source attestation: REAL, MOCK, or HYBRID';
COMMENT ON COLUMN demo.signals.attestation_id IS 'Reference to audit.source_attestations for verification';
COMMENT ON COLUMN demo.signals.api_response_hash IS 'Hash of raw API response for REAL source verification';
