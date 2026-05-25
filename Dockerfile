# syntax=docker/dockerfile:1.7
# =============================================================================
# OKX Scanner - Multi-stage Dockerfile
# =============================================================================
# Stage 1: Builder - install dependencies into a venv
# Stage 2: Runtime - copy venv + source, run as non-root user
# =============================================================================

ARG PYTHON_VERSION=3.14
ARG DEBIAN_RELEASE=bookworm

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# System build deps (psycopg, etc.)
RUN apt-get update && apt-get install --no-install-recommends -y \
        build-essential \
        libpq-dev \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create venv
RUN python -m venv ${VIRTUAL_ENV}

WORKDIR /build

# Copy only dependency files first to leverage layer cache
COPY pyproject.toml ./
COPY README.md* ./

# Install deps (production only)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install .

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app

# Runtime system deps only (libpq for psycopg, curl for healthcheck)
RUN apt-get update && apt-get install --no-install-recommends -y \
        libpq5 \
        curl \
        tini \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system --gid 1000 okx && \
    useradd --system --uid 1000 --gid okx --home-dir ${APP_HOME} --shell /sbin/nologin okx

# Copy venv from builder
COPY --from=builder --chown=okx:okx ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR ${APP_HOME}

# Copy application code
COPY --chown=okx:okx ./src ./src
COPY --chown=okx:okx ./config ./config
COPY --chown=okx:okx ./alembic ./alembic
COPY --chown=okx:okx ./alembic.ini ./alembic.ini
COPY --chown=okx:okx ./pyproject.toml ./pyproject.toml

USER okx

EXPOSE 8000

# Healthcheck hits the FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Use tini as PID 1 to handle signals/zombies properly
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command: run API. Override in docker-compose for worker service.
CMD ["uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--no-access-log"]
