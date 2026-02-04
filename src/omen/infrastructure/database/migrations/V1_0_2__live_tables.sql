-- ═══════════════════════════════════════════════════════════════════════════════
-- V1.0.2: Live Schema Tables
-- ═══════════════════════════════════════════════════════════════════════════════
--
-- Creates tables in the live schema for production signals.
-- CRITICAL: live.signals has CHECK constraint requiring source_type = 'REAL'
--
-- The live schema is BLOCKED until:
--   1. OMEN_ALLOW_LIVE_MODE=true (master switch)
--   2. Real source coverage >= 80%
--   3. All required sources are REAL
--
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────────
-- live.signals - Production signal storage (REAL only)
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS live.signals (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Signal identification
    signal_id VARCHAR(64) UNIQUE NOT NULL,
    source_event_id VARCHAR(128),
    trace_id VARCHAR(64),
    input_event_hash VARCHAR(64),
    
    -- Source attestation (CRITICAL: REAL only)
    source_type source_type NOT NULL,
    attestation_id UUID NOT NULL,  -- Required for live signals
    
    -- Signal content
    title TEXT NOT NULL,
    description TEXT,
    probability FLOAT CHECK (probability >= 0 AND probability <= 1),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    confidence_level VARCHAR(16),
    signal_type VARCHAR(32),
    status VARCHAR(16) DEFAULT 'ACTIVE',
    category VARCHAR(32),
    
    -- Structured data
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
    
    -- Data provenance (required for live)
    ingested_from VARCHAR(64) NOT NULL,
    api_response_hash VARCHAR(64) NOT NULL,
    
    -- ═══════════════════════════════════════════════════════════════════════════
    -- CRITICAL CONSTRAINT: Only REAL signals allowed in live schema
    -- ═══════════════════════════════════════════════════════════════════════════
    CONSTRAINT live_signals_source_type_check 
        CHECK (source_type = 'REAL')
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- live.raw_inputs - Verified raw API responses
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS live.raw_inputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Source identification
    source_id VARCHAR(64) NOT NULL,
    source_type source_type NOT NULL,
    
    -- Raw data
    api_endpoint VARCHAR(512) NOT NULL,
    request_headers JSONB,
    response_body JSONB NOT NULL,
    response_hash VARCHAR(64) NOT NULL,
    
    -- Verification
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verification_method verification_method NOT NULL,
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    signal_id VARCHAR(64),
    
    -- Metadata
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- REAL only constraint
    CONSTRAINT live_raw_inputs_source_type_check 
        CHECK (source_type = 'REAL'),
    
    -- Idempotency
    UNIQUE (source_id, response_hash)
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- live.ingestion_logs - Production pipeline logs
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS live.ingestion_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Request tracking
    trace_id VARCHAR(64) NOT NULL,
    request_id VARCHAR(64),
    
    -- Processing details
    source_id VARCHAR(64) NOT NULL,
    source_type source_type NOT NULL,
    stage VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL,
    
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
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- REAL only constraint
    CONSTRAINT live_ingestion_logs_source_type_check 
        CHECK (source_type = 'REAL')
);

-- Add table comments
COMMENT ON TABLE live.signals IS 'Production signals - REAL source type only (CHECK constraint enforced)';
COMMENT ON TABLE live.raw_inputs IS 'Verified raw API responses for production';
COMMENT ON TABLE live.ingestion_logs IS 'Production pipeline logs';

-- Add constraint comments
COMMENT ON CONSTRAINT live_signals_source_type_check ON live.signals IS 
    'CRITICAL: Only REAL signals allowed in live schema. MOCK/HYBRID will be rejected.';
