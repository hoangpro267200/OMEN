#!/usr/bin/env bash
# Smoke tests for OMEN API — call after deployment (e.g. blue-green green).
# Usage: ./scripts/smoke-tests.sh https://omen-green.internal

set -e

BASE_URL="${1:-http://localhost:8000}"

echo "Smoke testing OMEN API at $BASE_URL"

curl -sf "${BASE_URL}/health/" || { echo "Health check failed"; exit 1; }
curl -sf "${BASE_URL}/health/live" || { echo "Liveness check failed"; exit 1; }

echo "Smoke tests passed"
