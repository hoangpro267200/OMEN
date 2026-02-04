#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# OMEN API - cURL Examples
# ═══════════════════════════════════════════════════════════════════════════
#
# Usage:
#   chmod +x basic_requests.sh
#   ./basic_requests.sh
#
# Prerequisites:
#   - curl installed
#   - jq installed (for JSON formatting)
#   - OMEN server running on localhost:8000

# Configuration
BASE_URL="${OMEN_BASE_URL:-http://localhost:8000}"
API_KEY="${OMEN_API_KEY:-demo-key}"

echo "═══════════════════════════════════════════════════════════════════"
echo "OMEN API - cURL Examples"
echo "Base URL: $BASE_URL"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Health Check (No Auth Required)
# ═══════════════════════════════════════════════════════════════════════════
echo "=== Health Check ==="
curl -s "$BASE_URL/health/ready" | jq '.'
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Live Health Check
# ═══════════════════════════════════════════════════════════════════════════
echo "=== Live Check ==="
curl -s "$BASE_URL/health/live" | jq '.'
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Get All Signals
# ═══════════════════════════════════════════════════════════════════════════
echo "=== Get Signals (limit=5) ==="
curl -s \
  -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/v1/signals?limit=5" | jq '.signals[:2]'
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Get Signals by Category
# ═══════════════════════════════════════════════════════════════════════════
echo "=== Get Geopolitical Signals ==="
curl -s \
  -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/v1/signals?category=geopolitical&limit=3" | jq '.signals | length'
echo " signals found"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Get High Confidence Signals
# ═══════════════════════════════════════════════════════════════════════════
echo "=== Get High Confidence Signals (>70%) ==="
curl -s \
  -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/v1/signals?min_confidence=0.7&limit=3" | jq '.signals[:1]'
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Get Pipeline Statistics
# ═══════════════════════════════════════════════════════════════════════════
echo "=== Pipeline Statistics ==="
curl -s \
  -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/v1/signals/stats" | jq '{
    total_processed: .total_processed,
    pass_rate: .pass_rate,
    latency_ms: .latency_ms
  }'
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Get Methodology Summary
# ═══════════════════════════════════════════════════════════════════════════
echo "=== Methodology Summary ==="
curl -s \
  -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/v1/methodology" | jq '.signal_engine_principles[:2]'
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Get Source Health
# ═══════════════════════════════════════════════════════════════════════════
echo "=== Source Health ==="
curl -s \
  -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/v1/health/sources" 2>/dev/null | jq 'if .sources then .sources | keys else "N/A" end'
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# WebSocket Connection (just test if available)
# ═══════════════════════════════════════════════════════════════════════════
echo "=== WebSocket Endpoint Info ==="
echo "WebSocket URL: ws://${BASE_URL#http://}/api/v1/realtime/ws"
echo "Use wscat or similar tool to connect:"
echo "  wscat -c 'ws://localhost:8000/api/v1/realtime/ws?api_key=$API_KEY'"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo "Examples complete!"
echo "═══════════════════════════════════════════════════════════════════"
