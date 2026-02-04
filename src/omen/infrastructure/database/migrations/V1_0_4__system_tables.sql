-- ═══════════════════════════════════════════════════════════════════════════════
-- V1.0.4: System Schema Tables
-- ═══════════════════════════════════════════════════════════════════════════════
--
-- Creates system configuration and metadata tables:
--   - source_registry: Data source registration and status
--   - config: System configuration key-value store
--   - cleanup_log: Record of cleanup job executions
--   - health_checks: Source health check history
--
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────────
-- system.source_registry - Data source registration
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system.source_registry (
    -- Source identification
    source_id VARCHAR(64) PRIMARY KEY,
    source_name VARCHAR(128) NOT NULL,
    
    -- Source classification
    source_type source_type NOT NULL,
    category VARCHAR(32),  -- MARKET, WEATHER, FREIGHT, AIS, NEWS, etc.
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_required BOOLEAN NOT NULL DEFAULT FALSE,  -- Required for LIVE mode
    
    -- Connection details (encrypted in production)
    api_endpoint VARCHAR(512),
    auth_method VARCHAR(32),  -- API_KEY, OAUTH, CERTIFICATE, NONE
    
    -- Health monitoring
    last_health_check TIMESTAMPTZ,
    health_status VARCHAR(16) DEFAULT 'UNKNOWN',  -- HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN
    consecutive_failures INTEGER DEFAULT 0,
    
    -- Rate limiting
    rate_limit_requests INTEGER,
    rate_limit_window_seconds INTEGER,
    
    -- Metadata
    description TEXT,
    documentation_url VARCHAR(512),
    metadata JSONB,
    
    -- Timestamps
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- system.config - System configuration key-value store
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system.config (
    -- Configuration key
    key VARCHAR(128) PRIMARY KEY,
    
    -- Value (stored as JSONB for flexibility)
    value JSONB NOT NULL,
    value_type VARCHAR(32) NOT NULL,  -- STRING, INTEGER, FLOAT, BOOLEAN, JSON
    
    -- Metadata
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,  -- If true, value is encrypted
    is_runtime BOOLEAN DEFAULT TRUE,  -- Can be changed at runtime
    
    -- Validation
    validation_regex VARCHAR(256),
    min_value FLOAT,
    max_value FLOAT,
    allowed_values JSONB,  -- Array of allowed values
    
    -- Change tracking
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128)
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- system.cleanup_log - Cleanup job execution history
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system.cleanup_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Job identification
    job_name VARCHAR(64) NOT NULL,
    job_type VARCHAR(32) NOT NULL,  -- CLEANUP, ARCHIVE, VACUUM
    
    -- Target
    target_schema VARCHAR(32) NOT NULL,
    target_table VARCHAR(64) NOT NULL,
    
    -- Execution details
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- Results
    status VARCHAR(16) NOT NULL,  -- RUNNING, SUCCESS, FAILED, PARTIAL
    rows_affected INTEGER DEFAULT 0,
    bytes_freed BIGINT,
    
    -- Criteria used
    retention_hours INTEGER,
    cutoff_timestamp TIMESTAMPTZ,
    
    -- Error details
    error_message TEXT,
    error_details JSONB,
    
    -- Metadata
    dry_run BOOLEAN DEFAULT FALSE,
    triggered_by VARCHAR(128),  -- SCHEDULER, MANUAL, SYSTEM
    metadata JSONB
);

-- ─────────────────────────────────────────────────────────────────────────────────
-- system.health_checks - Source health check history
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system.health_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Source
    source_id VARCHAR(64) NOT NULL REFERENCES system.source_registry(source_id),
    
    -- Check results
    status VARCHAR(16) NOT NULL,  -- HEALTHY, DEGRADED, UNHEALTHY, TIMEOUT, ERROR
    response_time_ms INTEGER,
    
    -- Details
    endpoint_checked VARCHAR(512),
    http_status_code INTEGER,
    error_message TEXT,
    
    -- Metadata
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

-- Add table comments
COMMENT ON TABLE system.source_registry IS 'Data source registration and status tracking';
COMMENT ON TABLE system.config IS 'System configuration key-value store';
COMMENT ON TABLE system.cleanup_log IS 'History of cleanup and archive job executions';
COMMENT ON TABLE system.health_checks IS 'Health check history for registered sources';

-- Add important column comments
COMMENT ON COLUMN system.source_registry.is_required IS 'If true, source must be REAL for LIVE mode to be allowed';
COMMENT ON COLUMN system.source_registry.health_status IS 'Current health: HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN';
COMMENT ON COLUMN system.config.is_sensitive IS 'If true, value is encrypted at rest';
COMMENT ON COLUMN system.config.is_runtime IS 'If true, changes take effect without restart';

-- ─────────────────────────────────────────────────────────────────────────────────
-- Insert default configuration values
-- ─────────────────────────────────────────────────────────────────────────────────
INSERT INTO system.config (key, value, value_type, description, is_runtime) VALUES
    ('LIVE_MODE_ENABLED', 'false', 'BOOLEAN', 'Master switch for LIVE mode', TRUE),
    ('MIN_REAL_SOURCE_RATIO', '0.80', 'FLOAT', 'Minimum ratio of REAL sources for LIVE mode', TRUE),
    ('RAW_INPUT_RETENTION_HOURS', '72', 'INTEGER', 'Hours to retain raw inputs', TRUE),
    ('INGESTION_LOG_RETENTION_DAYS', '30', 'INTEGER', 'Days to retain ingestion logs', TRUE),
    ('API_LOG_RETENTION_DAYS', '90', 'INTEGER', 'Days to retain API access logs', TRUE),
    ('SIGNAL_ARCHIVE_AFTER_DAYS', '90', 'INTEGER', 'Days before signals are archived', TRUE),
    ('GATE_CACHE_TTL_SECONDS', '30', 'INTEGER', 'Seconds to cache gate status', TRUE)
ON CONFLICT (key) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────────
-- Insert default source registry (current OMEN sources)
-- ─────────────────────────────────────────────────────────────────────────────────
INSERT INTO system.source_registry (source_id, source_name, source_type, category, is_required, description) VALUES
    ('polymarket', 'Polymarket', 'REAL', 'MARKET', TRUE, 'Prediction market data from Polymarket'),
    ('openweather', 'OpenWeather', 'REAL', 'WEATHER', FALSE, 'Weather data from OpenWeather API'),
    ('ais_mock', 'AIS Mock', 'MOCK', 'AIS', FALSE, 'Mock AIS ship tracking data'),
    ('freight_mock', 'Freight Mock', 'MOCK', 'FREIGHT', FALSE, 'Mock freight rate data'),
    ('news_mock', 'News Mock', 'MOCK', 'NEWS', FALSE, 'Mock news data'),
    ('commodities_mock', 'Commodities Mock', 'MOCK', 'COMMODITIES', FALSE, 'Mock commodity price data'),
    ('stock_mock', 'Stock Mock', 'MOCK', 'STOCK', FALSE, 'Mock stock market data')
ON CONFLICT (source_id) DO NOTHING;
