# Stage 1: The builder stage. This handles all heavy installations.
FROM python:3.13-bookworm AS builder

# Install build-time dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN pip install --no-cache-dir dagster dagster-docker dagster-postgres dagster-webserver

# Stage 2: The final, lean production image
FROM python:3.13-bookworm AS final

# Install only the necessary runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR /dagster_pipeline

# Set $DAGSTER_HOME environment variable
ENV DAGSTER_HOME=/dagster_pipeline/config/

# Create DAGSTER_HOME and storage directories
RUN mkdir -p $DAGSTER_HOME && \
    mkdir -p /dagster_pipeline/.dagster/compute_logs && \
    mkdir -p /dagster_pipeline/.dagster/storage

# Copy config and dagster_pipeline directories
COPY config/ ./config/
COPY dagster_pipeline/ ./dagster_pipeline/

# Set Python path to include the parent directory for proper module imports
ENV PYTHONPATH=/dagster_pipeline:$PYTHONPATH

# Expose port for webserver
EXPOSE 3000
