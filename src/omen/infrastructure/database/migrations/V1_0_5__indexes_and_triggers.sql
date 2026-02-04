-- ═══════════════════════════════════════════════════════════════════════════════
-- V1.0.5: Indexes and Audit Protection Triggers
-- ═══════════════════════════════════════════════════════════════════════════════
--
-- Creates:
--   1. Performance indexes for all tables
--   2. IMMUTABILITY TRIGGERS for audit schema (block UPDATE/DELETE)
--   3. Automatic updated_at triggers
--
-- ═══════════════════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 1: Performance Indexes
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────────
-- demo.signals indexes
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_demo_signals_signal_id 
    ON demo.signals(signal_id);
CREATE INDEX IF NOT EXISTS idx_demo_signals_hash 
    ON demo.signals(input_event_hash);
CREATE INDEX IF NOT EXISTS idx_demo_signals_event_id 
    ON demo.signals(source_event_id);
CREATE INDEX IF NOT EXISTS idx_demo_signals_generated_at 
    ON demo.signals(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_demo_signals_type 
    ON demo.signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_demo_signals_source_type 
    ON demo.signals(source_type);
CREATE INDEX IF NOT EXISTS idx_demo_signals_category 
    ON demo.signals(category);
CREATE INDEX IF NOT EXISTS idx_demo_signals_status 
    ON demo.signals(status);

-- GIN indexes for JSONB fields
CREATE INDEX IF NOT EXISTS idx_demo_signals_tags_gin 
    ON demo.signals USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_demo_signals_payload_gin 
    ON demo.signals USING GIN (payload jsonb_path_ops);

-- ─────────────────────────────────────────────────────────────────────────────────
-- demo.raw_inputs indexes
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_demo_raw_inputs_source_id 
    ON demo.raw_inputs(source_id);
CREATE INDEX IF NOT EXISTS idx_demo_raw_inputs_received_at 
    ON demo.raw_inputs(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_demo_raw_inputs_expires_at 
    ON demo.raw_inputs(expires_at);
CREATE INDEX IF NOT EXISTS idx_demo_raw_inputs_processed 
    ON demo.raw_inputs(processed) WHERE NOT processed;

-- ─────────────────────────────────────────────────────────────────────────────────
-- demo.ingestion_logs indexes
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_demo_ingestion_logs_trace_id 
    ON demo.ingestion_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_demo_ingestion_logs_source_id 
    ON demo.ingestion_logs(source_id);
CREATE INDEX IF NOT EXISTS idx_demo_ingestion_logs_status 
    ON demo.ingestion_logs(status);
CREATE INDEX IF NOT EXISTS idx_demo_ingestion_logs_created_at 
    ON demo.ingestion_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_demo_ingestion_logs_expires_at 
    ON demo.ingestion_logs(expires_at);

-- ─────────────────────────────────────────────────────────────────────────────────
-- live.signals indexes (same structure as demo)
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_live_signals_signal_id 
    ON live.signals(signal_id);
CREATE INDEX IF NOT EXISTS idx_live_signals_hash 
    ON live.signals(input_event_hash);
CREATE INDEX IF NOT EXISTS idx_live_signals_event_id 
    ON live.signals(source_event_id);
CREATE INDEX IF NOT EXISTS idx_live_signals_generated_at 
    ON live.signals(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_signals_type 
    ON live.signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_live_signals_category 
    ON live.signals(category);

CREATE INDEX IF NOT EXISTS idx_live_signals_tags_gin 
    ON live.signals USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_live_signals_payload_gin 
    ON live.signals USING GIN (payload jsonb_path_ops);

-- ─────────────────────────────────────────────────────────────────────────────────
-- audit.operation_log indexes
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_operation_log_trace_id 
    ON audit.operation_log(trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_operation_log_target 
    ON audit.operation_log(target_schema, target_table);
CREATE INDEX IF NOT EXISTS idx_audit_operation_log_logged_at 
    ON audit.operation_log(logged_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_operation_log_operation_type 
    ON audit.operation_log(operation_type);

-- ─────────────────────────────────────────────────────────────────────────────────
-- audit.source_attestations indexes
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_source_attestations_signal_id 
    ON audit.source_attestations(signal_id);
CREATE INDEX IF NOT EXISTS idx_audit_source_attestations_source_id 
    ON audit.source_attestations(source_id);
CREATE INDEX IF NOT EXISTS idx_audit_source_attestations_source_type 
    ON audit.source_attestations(source_type);
CREATE INDEX IF NOT EXISTS idx_audit_source_attestations_attested_at 
    ON audit.source_attestations(attested_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────────
-- audit.gate_decisions indexes
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_gate_decisions_decided_at 
    ON audit.gate_decisions(decided_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_gate_decisions_decision 
    ON audit.gate_decisions(decision);
CREATE INDEX IF NOT EXISTS idx_audit_gate_decisions_trace_id 
    ON audit.gate_decisions(trace_id);

-- ─────────────────────────────────────────────────────────────────────────────────
-- audit.api_access_log indexes
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_api_access_log_requested_at 
    ON audit.api_access_log(requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_api_access_log_path 
    ON audit.api_access_log(path);
CREATE INDEX IF NOT EXISTS idx_audit_api_access_log_status_code 
    ON audit.api_access_log(status_code);
CREATE INDEX IF NOT EXISTS idx_audit_api_access_log_expires_at 
    ON audit.api_access_log(expires_at);

-- ─────────────────────────────────────────────────────────────────────────────────
-- system.health_checks indexes
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_system_health_checks_source_id 
    ON system.health_checks(source_id);
CREATE INDEX IF NOT EXISTS idx_system_health_checks_checked_at 
    ON system.health_checks(checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_health_checks_status 
    ON system.health_checks(status);

-- ─────────────────────────────────────────────────────────────────────────────────
-- system.cleanup_log indexes
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_system_cleanup_log_started_at 
    ON system.cleanup_log(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_cleanup_log_job_name 
    ON system.cleanup_log(job_name);
CREATE INDEX IF NOT EXISTS idx_system_cleanup_log_status 
    ON system.cleanup_log(status);


-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 2: Audit Table Immutability Protection
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────────
-- Function to block modifications on audit tables
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION audit.prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'AUDIT TABLE IMMUTABILITY VIOLATION: % operations are not allowed on audit.%. This table is append-only.',
        TG_OP, TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION audit.prevent_modification() IS 
    'Trigger function that blocks UPDATE and DELETE on audit tables to ensure immutability';

-- ─────────────────────────────────────────────────────────────────────────────────
-- Apply immutability triggers to all audit tables
-- ─────────────────────────────────────────────────────────────────────────────────

-- audit.operation_log
DROP TRIGGER IF EXISTS prevent_operation_log_update ON audit.operation_log;
CREATE TRIGGER prevent_operation_log_update
    BEFORE UPDATE ON audit.operation_log
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_modification();

DROP TRIGGER IF EXISTS prevent_operation_log_delete ON audit.operation_log;
CREATE TRIGGER prevent_operation_log_delete
    BEFORE DELETE ON audit.operation_log
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_modification();

-- audit.source_attestations
DROP TRIGGER IF EXISTS prevent_source_attestations_update ON audit.source_attestations;
CREATE TRIGGER prevent_source_attestations_update
    BEFORE UPDATE ON audit.source_attestations
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_modification();

DROP TRIGGER IF EXISTS prevent_source_attestations_delete ON audit.source_attestations;
CREATE TRIGGER prevent_source_attestations_delete
    BEFORE DELETE ON audit.source_attestations
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_modification();

-- audit.gate_decisions
DROP TRIGGER IF EXISTS prevent_gate_decisions_update ON audit.gate_decisions;
CREATE TRIGGER prevent_gate_decisions_update
    BEFORE UPDATE ON audit.gate_decisions
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_modification();

DROP TRIGGER IF EXISTS prevent_gate_decisions_delete ON audit.gate_decisions;
CREATE TRIGGER prevent_gate_decisions_delete
    BEFORE DELETE ON audit.gate_decisions
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_modification();

-- audit.api_access_log
DROP TRIGGER IF EXISTS prevent_api_access_log_update ON audit.api_access_log;
CREATE TRIGGER prevent_api_access_log_update
    BEFORE UPDATE ON audit.api_access_log
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_modification();

DROP TRIGGER IF EXISTS prevent_api_access_log_delete ON audit.api_access_log;
CREATE TRIGGER prevent_api_access_log_delete
    BEFORE DELETE ON audit.api_access_log
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_modification();


-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 3: Automatic updated_at Triggers
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────────
-- Function to automatically update updated_at timestamp
-- ─────────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to demo.signals
DROP TRIGGER IF EXISTS update_demo_signals_updated_at ON demo.signals;
CREATE TRIGGER update_demo_signals_updated_at
    BEFORE UPDATE ON demo.signals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply to live.signals
DROP TRIGGER IF EXISTS update_live_signals_updated_at ON live.signals;
CREATE TRIGGER update_live_signals_updated_at
    BEFORE UPDATE ON live.signals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply to system.source_registry
DROP TRIGGER IF EXISTS update_source_registry_updated_at ON system.source_registry;
CREATE TRIGGER update_source_registry_updated_at
    BEFORE UPDATE ON system.source_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply to system.config
DROP TRIGGER IF EXISTS update_config_updated_at ON system.config;
CREATE TRIGGER update_config_updated_at
    BEFORE UPDATE ON system.config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ═══════════════════════════════════════════════════════════════════════════════
-- PART 4: Verification Queries (for testing)
-- ═══════════════════════════════════════════════════════════════════════════════

-- These queries can be used to verify the schema is set up correctly:

-- Check schemas exist:
-- SELECT schema_name FROM information_schema.schemata 
-- WHERE schema_name IN ('demo', 'live', 'audit', 'system');

-- Check audit triggers are in place:
-- SELECT trigger_name, event_object_table, action_statement 
-- FROM information_schema.triggers 
-- WHERE trigger_schema = 'audit';

-- Check live.signals constraint:
-- SELECT constraint_name, check_clause 
-- FROM information_schema.check_constraints 
-- WHERE constraint_schema = 'live';

-- Test audit immutability (should fail):
-- INSERT INTO audit.operation_log (operation_id, operation_type, target_schema, target_table)
-- VALUES ('test', 'INSERT', 'demo', 'signals');
-- UPDATE audit.operation_log SET target_table = 'changed' WHERE operation_id = 'test';  -- Should fail!
