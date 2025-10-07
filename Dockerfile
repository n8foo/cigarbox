# Multi-stage build for smaller image
FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy application code
COPY *.py ./
COPY templates/ ./templates/
COPY static/ ./static/

# Create necessary directories
RUN mkdir -p /app/logs /app/static/cigarbox /tmp/cigarbox

# Create non-root user
RUN useradd -m -u 1000 cigarbox && \
    chown -R cigarbox:cigarbox /app && \
    chown -R cigarbox:cigarbox /tmp/cigarbox

USER cigarbox

# Expose ports
EXPOSE 9600 9601

# Default command (can be overridden in docker-compose)
CMD ["gunicorn", "--config", "gunicorn_config.py", "web:app"]
