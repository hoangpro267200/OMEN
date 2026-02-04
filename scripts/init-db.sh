#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# OMEN PostgreSQL Initialization Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# This script runs when the PostgreSQL container is first created.
# It creates the required schemas and extensions for OMEN persistence.
#
# Note: Full migrations are run by the OMEN application on startup.
#       This script only sets up the minimal prerequisites.
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  OMEN Database Initialization"
echo "═══════════════════════════════════════════════════════════════════════════════"

# Run as the postgres superuser to create extensions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- ═══════════════════════════════════════════════════════════════════════════
    -- Enable required extensions
    -- ═══════════════════════════════════════════════════════════════════════════
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    
    -- ═══════════════════════════════════════════════════════════════════════════
    -- Create schemas
    -- ═══════════════════════════════════════════════════════════════════════════
    CREATE SCHEMA IF NOT EXISTS demo;
    CREATE SCHEMA IF NOT EXISTS live;
    CREATE SCHEMA IF NOT EXISTS audit;
    CREATE SCHEMA IF NOT EXISTS system;
    
    -- ═══════════════════════════════════════════════════════════════════════════
    -- Grant permissions (for non-superuser access if needed)
    -- ═══════════════════════════════════════════════════════════════════════════
    GRANT ALL PRIVILEGES ON SCHEMA demo TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON SCHEMA live TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON SCHEMA audit TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON SCHEMA system TO $POSTGRES_USER;
    
    -- Set default search path to include our schemas
    ALTER DATABASE $POSTGRES_DB SET search_path TO public, demo, live, audit, system;
    
    -- ═══════════════════════════════════════════════════════════════════════════
    -- Create custom types (if not using migrations)
    -- ═══════════════════════════════════════════════════════════════════════════
    DO \$\$ BEGIN
        CREATE TYPE source_type AS ENUM ('REAL', 'MOCK', 'HYBRID');
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END \$\$;
    
    DO \$\$ BEGIN
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
    END \$\$;
    
    DO \$\$ BEGIN
        CREATE TYPE gate_decision AS ENUM ('ALLOW', 'BLOCK');
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END \$\$;
    
    DO \$\$ BEGIN
        CREATE TYPE operation_type AS ENUM ('INSERT', 'UPDATE', 'DELETE', 'UPSERT');
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END \$\$;
    
    -- ═══════════════════════════════════════════════════════════════════════════
    -- Verify setup
    -- ═══════════════════════════════════════════════════════════════════════════
    SELECT 'Schemas created:' as status;
    SELECT schema_name FROM information_schema.schemata 
    WHERE schema_name IN ('demo', 'live', 'audit', 'system');
    
    SELECT 'Extensions enabled:' as status;
    SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto');
    
    SELECT 'Custom types created:' as status;
    SELECT typname FROM pg_type WHERE typname IN ('source_type', 'verification_method', 'gate_decision', 'operation_type');
EOSQL

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  OMEN Database initialization complete!"
echo "  Schemas: demo, live, audit, system"
echo "  Extensions: uuid-ossp, pgcrypto"
echo "═══════════════════════════════════════════════════════════════════════════════"
