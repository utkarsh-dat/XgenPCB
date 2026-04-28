#!/bin/bash
# ============================================
# XgenPCB Backend Startup Script
# Initializes database then starts the API server
# ============================================

set -e

echo "[XgenPCB] Initializing database..."
python3.11 init_db.py

echo "[XgenPCB] Starting API server..."
exec uvicorn services.gateway.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --proxy-headers \
    "$@"
