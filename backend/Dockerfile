# ============================================
# XgenPCB - Backend Production Dockerfile
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy and install dependencies
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -e ".[ai]"

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "services.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
