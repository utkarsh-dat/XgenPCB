# ============================================
# XgenPCB Backend - Production Dockerfile
# ============================================
FROM ubuntu:22.04 AS base

WORKDIR /app

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    gnupg2 \
    ca-certificates \
    curl \
    git \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && add-apt-repository -y ppa:kicad/kicad-9.0-releases \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-distutils \
    build-essential \
    libpq-dev \
    kicad \
    && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Set python3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --set python3 /usr/bin/python3.11

# Production stage
FROM base AS production

WORKDIR /app

# Create non-root user
RUN groupadd -r xgenpcb && useradd -r -g xgenpcb xgenpcb

# Copy requirements first for better caching
COPY backend/pyproject.toml ./

# Install dependencies
RUN python3.11 -m pip install --no-cache-dir \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg pydantic pydantic-settings \
    python-jose[cryptography] passlib[bcrypt] python-multipart httpx redis \
    boto3 stripe celery slowapi python-dotenv alembic tenacity structlog orjson \
    email-validator aiosqlite psycopg2-binary 'bcrypt>=4.0.1'

# Copy application source
COPY backend/ ./

# Make startup script executable
RUN chmod +x start.sh

# Create necessary directories
RUN mkdir -p /app/storage/designs /app/data /app/logs \
    && chown -R xgenpcb:xgenpcb /app

# Switch to non-root user
USER xgenpcb

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run startup script (init DB + start server)
CMD ["bash", "start.sh"]
