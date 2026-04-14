#!/bin/bash
set -e

PORT="${LISTEN_PORT:-5010}"

echo "=== Signature Manager ==="
echo "Starting on port ${PORT}..."

exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    run:app
