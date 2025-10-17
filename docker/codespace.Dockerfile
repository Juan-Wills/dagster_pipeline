# Stage 1: The builder stage. This handles all heavy installations.
FROM python:3.13-slim-bookworm AS builder

# Install build-time dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /dagster_pipeline

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies including google-api group (better caching)
RUN uv sync --frozen --all-groups

# Copy application files
COPY dagster_pipeline ./dagster_pipeline
COPY config ./config

# Stage 2: The final, lean production image
FROM python:3.13-slim-bookworm AS final

# Install only the necessary runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /dagster_pipeline

# Copy everything from builder (venv, application code)
COPY --from=builder /dagster_pipeline/dagster_pipeline ./dagster_pipeline
COPY --from=builder /dagster_pipeline/config ./config
COPY --from=builder /dagster_pipeline/.venv ./.venv

# Set environment variable PATH to use the virtual environment  
ENV PATH="/dagster_pipeline/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    DAGSTER_HOME=/dagster_pipeline/config

# Expose ports 
EXPOSE 4000

# Health check - check if process is listening on port 4000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:4000/ || exit 1

# Use exec form with module-based loading
CMD ["dagster", "code-server", "start", "-h", "0.0.0.0", "-p", "4000", "-m", "dagster_pipeline.definitions"]

