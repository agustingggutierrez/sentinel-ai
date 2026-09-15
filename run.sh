#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is required but was not found."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "Error: .env was not found."
    echo "Copy .env.example to .env and configure the required credentials."
    exit 1
fi

echo "Starting SentinelAI..."
docker compose up --build
