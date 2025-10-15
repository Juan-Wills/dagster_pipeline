# Stage 1: The builder stage. This handles all heavy installations.
FROM python:3.13-bookworm AS builder

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

# Copy all files and directories
COPY . .

# Create and activate virtual environment
RUN chmod +x entrypoint.sh && \
    uv sync --frozen --no-cache --no-dev

# Stage 2: The final, lean production image
FROM python:3.13-bookworm AS final

# Install only the necessary runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /dagster_pipeline

# Copy everything from builder (venv, application code, entrypoint)
COPY --from=builder /dagster_pipeline/pipeline ./pipeline
COPY --from=builder /dagster_pipeline/.venv ./.venv
COPY --from=builder /dagster_pipeline/entrypoint.sh ./entrypoint.sh

# Set environment variable PATH to use the virtual environment  
ENV PATH="/dagster_pipeline/.venv/bin:$PATH"

# Expose ports 
EXPOSE 3000

# Health check 
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

CMD ["sleep", "infinity"]

