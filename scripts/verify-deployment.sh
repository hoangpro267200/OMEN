#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# OMEN Deployment Verification Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# Verifies that OMEN is properly deployed and functioning.
# Run after `docker-compose up` or on a deployed environment.
#
# Usage:
#   ./scripts/verify-deployment.sh [BASE_URL]
#
# Example:
#   ./scripts/verify-deployment.sh http://localhost:8000
#   ./scripts/verify-deployment.sh https://omen.example.com
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Configuration
BASE_URL="${1:-http://localhost:8000}"
TIMEOUT=10
PASSED=0
FAILED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  OMEN DEPLOYMENT VERIFICATION"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Target: $BASE_URL"
echo ""

# Function to check an endpoint
check_endpoint() {
    local name="$1"
    local endpoint="$2"
    local expected="$3"
    
    printf "  %-30s" "$name..."
    
    response=$(curl -sf --max-time $TIMEOUT "$BASE_URL$endpoint" 2>/dev/null) || response=""
    
    if [ -n "$response" ]; then
        if [ -n "$expected" ]; then
            if echo "$response" | grep -q "$expected"; then
                echo -e "${GREEN}✅ PASS${NC}"
                ((PASSED++))
            else
                echo -e "${RED}❌ FAIL${NC} (unexpected response)"
                ((FAILED++))
            fi
        else
            echo -e "${GREEN}✅ PASS${NC}"
            ((PASSED++))
        fi
    else
        echo -e "${RED}❌ FAIL${NC} (no response)"
        ((FAILED++))
    fi
}

# Function to check endpoint returns specific status code
check_status() {
    local name="$1"
    local endpoint="$2"
    local expected_code="$3"
    
    printf "  %-30s" "$name..."
    
    status_code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$BASE_URL$endpoint" 2>/dev/null) || status_code="000"
    
    if [ "$status_code" = "$expected_code" ]; then
        echo -e "${GREEN}✅ PASS${NC} ($status_code)"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC} (got $status_code, expected $expected_code)"
        ((FAILED++))
    fi
}

echo "1. HEALTH CHECKS"
echo "────────────────────────────────────────────────────────────────────────────"
check_endpoint "Basic health" "/health" "healthy"
check_endpoint "Liveness probe" "/health/live" "alive"
check_status "Readiness probe" "/health/ready" "200"

echo ""
echo "2. CORE API ENDPOINTS"
echo "────────────────────────────────────────────────────────────────────────────"
check_status "Signals endpoint" "/api/v1/signals" "200"
check_status "Methodology endpoint" "/api/v1/methodology" "200"
check_status "Stats endpoint" "/api/v1/stats" "200"

echo ""
echo "3. MULTI-SOURCE INTELLIGENCE"
echo "────────────────────────────────────────────────────────────────────────────"
check_status "Sources list" "/api/v1/multi-source/sources" "200"

echo ""
echo "4. OBSERVABILITY"
echo "────────────────────────────────────────────────────────────────────────────"
check_endpoint "Prometheus metrics" "/metrics" "omen_"

echo ""
echo "5. VALIDATION RULES"
echo "────────────────────────────────────────────────────────────────────────────"
# Check that we have validation rules
printf "  %-30s" "Validation rules loaded..."
rules_response=$(curl -sf --max-time $TIMEOUT "$BASE_URL/api/v1/methodology" 2>/dev/null) || rules_response=""
if echo "$rules_response" | grep -q "validation"; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}"
    ((FAILED++))
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  RESULTS"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

TOTAL=$((PASSED + FAILED))
echo "  Passed: $PASSED / $TOTAL"
echo "  Failed: $FAILED / $TOTAL"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "  ${GREEN}✅ ALL CHECKS PASSED - DEPLOYMENT VERIFIED${NC}"
    echo ""
    exit 0
else
    echo -e "  ${RED}❌ SOME CHECKS FAILED - REVIEW DEPLOYMENT${NC}"
    echo ""
    exit 1
fi
