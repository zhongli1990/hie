# HIE - Healthcare Integration Engine
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash hie

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY Engine/ /app/Engine/
COPY config/ /app/config/

# Set Python path
ENV PYTHONPATH=/app

# Create data directories
RUN mkdir -p /data/inbound /data/outbound /data/processed && \
    chown -R hie:hie /app /data

# Switch to non-root user
USER hie

# Environment variables
ENV HIE_CONFIG=/app/config/production.yaml
ENV HIE_LOG_LEVEL=INFO
ENV HIE_LOG_FORMAT=json
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run HIE
ENTRYPOINT ["python", "-m", "Engine.cli"]
CMD ["run", "--config", "/app/config/production.yaml"]
