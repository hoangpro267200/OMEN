# ═══════════════════════════════════════════════════════════════════════════════
# OMEN Production Dockerfile
# Multi-stage build for minimal, secure image
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./
COPY src/ ./src/

# Create wheels for project (deps installed in runtime from wheel metadata)
RUN pip install --no-cache-dir build wheel \
    && pip wheel --no-cache-dir --wheel-dir /wheels .

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: Create non-root user
RUN groupadd -r omen && useradd -r -g omen omen

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy wheels from builder and install (pip will fetch deps from PyPI at build time)
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

# Copy application code
COPY src/ ./src/

# Create data directories with correct permissions
RUN mkdir -p /data/ledger /data/archive \
    && chown -R omen:omen /data /app

# Switch to non-root user
USER omen

# Environment defaults
ENV OMEN_LEDGER_BASE_PATH=/data/ledger \
    OMEN_LOG_LEVEL=INFO \
    OMEN_LOG_FORMAT=json \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "-m", "uvicorn", "omen.main:app", "--host", "0.0.0.0", "--port", "8000"]
