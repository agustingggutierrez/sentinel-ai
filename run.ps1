$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is required but was not found."
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Error ".env was not found. Copy .env.example to .env and configure the required credentials."
    exit 1
}

Write-Host "Starting SentinelAI..."
docker compose up --build

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
