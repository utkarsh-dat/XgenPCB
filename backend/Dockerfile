FROM ubuntu:22.04

WORKDIR /app

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    gnupg2 \
    ca-certificates \
    curl \
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

# Install Python dependencies with compatible versions
RUN python3.11 -m pip install --no-cache-dir aiosqlite psycopg2-binary 'bcrypt>=4.0.1' 'passlib[bcrypt]>=1.7.4'

# Copy requirements first (for better caching)
COPY pyproject.toml ./

# Install dependencies using pip
RUN python3.11 -m pip install --no-cache-dir -e .

# Copy application source
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