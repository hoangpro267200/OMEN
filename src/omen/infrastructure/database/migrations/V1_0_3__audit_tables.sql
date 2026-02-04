-- ═══════════════════════════════════════════════════════════════════════════════
-- V1.0.3: Audit Schema Tables
-- ═══════════════════════════════════════════════════════════════════════════════
--
-- Creates IMMUTABLE audit tables. After V1.0.5 triggers are applied:
--   - INSERT: Allowed
--   - UPDATE: Blocked by trigger
--   - DELETE: Blocked by trigger
--
-- Tables:
--   - operation_log: All database write operations
--   - source_attestations: Source type verification records
--   - gate_decisions: Live gate check history
--   - api_access_log: API request audit trail
--
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────────
-- audit.operation_log - All database write operations
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit.operation_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Operation identification
    operation_id VARCHAR(64) NOT NULL,
    trace_id VARCHAR(64),
    
    -- What happened
    operation_type operation_type NOT NULL,
    target_schema VARCHAR(32) NOT NULL,  -- demo, live, system
    target_table VARCHAR(64) NOT NULL,
    target_id VARCHAR(64),  -- Primary key of affected row
    
    -- Who/what performed it
    performed_by VARCHAR(128),  -- API key hash or system identifier
    source_ip VARCHAR(45),
    user_agent TEXT,
    
    -- Change details
    old_value JSONB,  -- For UPDATE/DELETE
    new_value JSONB,  -- For INSERT/UPDATE
    
    -- Attestation link
    attestation_id UUID,
    source_type source_type,
    
    -- Metadata
    reason TEXT,  -- Why the operation was performed
    metadata JSONB,
    
    -- Timestamp (immutable)
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- audit.source_attestations - Source type verification records
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit.source_attestations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- What was attested
    signal_id VARCHAR(64) NOT NULL,
    source_id VARCHAR(64) NOT NULL,
    
    -- Attestation result
    source_type source_type NOT NULL,
    verification_method verification_method NOT NULL,
    
    -- Verification evidence
    api_response_hash VARCHAR(64),  -- Required for REAL
    certificate_chain JSONB,  -- Optional: TLS certificate info
    raw_response_sample TEXT,  -- First 1000 chars for debugging
    
    -- Determination details
    determination_reason TEXT NOT NULL,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Metadata
    attested_by VARCHAR(128) NOT NULL,  -- System or manual
    attested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Index for signal lookups
    UNIQUE (signal_id)
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- audit.gate_decisions - Live gate check history
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit.gate_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Request context
    trace_id VARCHAR(64),
    request_id VARCHAR(64),
    requested_mode VARCHAR(16) NOT NULL,  -- LIVE, DEMO
    
    -- Decision
    decision gate_decision NOT NULL,
    
    -- Block reasons (if blocked)
    block_reasons JSONB,  -- Array of reason codes
    
    -- Gate state at decision time
    master_switch_enabled BOOLEAN NOT NULL,
    real_source_count INTEGER NOT NULL,
    total_source_count INTEGER NOT NULL,
    real_source_ratio FLOAT NOT NULL,
    required_ratio FLOAT NOT NULL,
    mock_sources JSONB,  -- List of mock source IDs
    real_sources JSONB,  -- List of real source IDs
    
    -- Metadata
    checked_by VARCHAR(128),  -- API endpoint or system
    client_ip VARCHAR(45),
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- audit.api_access_log - API request audit trail (90-day retention)
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit.api_access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Request identification
    request_id VARCHAR(64) NOT NULL,
    trace_id VARCHAR(64),
    
    -- Request details
    method VARCHAR(10) NOT NULL,
    path VARCHAR(512) NOT NULL,
    query_params JSONB,
    
    -- Authentication
    api_key_hash VARCHAR(64),  -- SHA256 of API key (never store raw key)
    authenticated BOOLEAN NOT NULL,
    
    -- Response
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    
    -- Client info
    client_ip VARCHAR(45),
    user_agent TEXT,
    
    -- Mode context
    requested_mode VARCHAR(16),
    actual_mode VARCHAR(16),
    
    -- Timestamps
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '90 days')
);

-- Add table comments
COMMENT ON TABLE audit.operation_log IS 'Immutable log of all database write operations';
COMMENT ON TABLE audit.source_attestations IS 'Source type verification records for signals';
COMMENT ON TABLE audit.gate_decisions IS 'History of live gate checks and decisions';
COMMENT ON TABLE audit.api_access_log IS 'API request audit trail (90-day retention)';

-- Add important column comments
COMMENT ON COLUMN audit.operation_log.old_value IS 'Previous state for UPDATE/DELETE (null for INSERT)';
COMMENT ON COLUMN audit.operation_log.new_value IS 'New state for INSERT/UPDATE (null for DELETE)';
COMMENT ON COLUMN audit.source_attestations.api_response_hash IS 'Required for REAL attestation - proves data came from live API';
COMMENT ON COLUMN audit.gate_decisions.block_reasons IS 'Array of reason codes: MASTER_SWITCH_OFF, INSUFFICIENT_COVERAGE, REQUIRED_SOURCE_MOCK';
