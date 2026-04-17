# =============================================================================
# C&N Tecidos AI Agent — Multi-stage Dockerfile
# =============================================================================
# Stage 1: Install dependencies
FROM python:3.12-slim-bookworm AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.10.7 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (layer cache optimization)
COPY requirements.txt .

# Install dependencies into virtual environment
RUN uv sync --frozen --no-install-project --no-dev

# =============================================================================
# Stage 2: Production image
# =============================================================================
FROM python:3.12-slim-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.10.7 /uv /uvx /bin/

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY . .

# Create non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Health check (shell form for env var expansion)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /bin/sh -c "python -c \"import httpx; httpx.get('http://localhost:' + os.environ.get('PORT', '3000') + '/health', timeout=5)\" || exit 1"

# Use PORT from environment (Easypanel injects this)
EXPOSE ${PORT:-3000}

# Shell form required for environment variable expansion
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-3000} --workers 1
