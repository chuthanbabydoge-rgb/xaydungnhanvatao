# Dev environment setup script
Write-Host "=== AITAONHANVATAO Development Environment ===" -ForegroundColor Cyan

# Check Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is required. Install Python 3.12+" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $pythonVersion"

# Check Docker
$dockerVersion = docker --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Docker is not installed. Some features won't work." -ForegroundColor Yellow
}
else {
    Write-Host "Docker: $dockerVersion"
}

# Install shared package in dev mode
Write-Host "`nInstalling shared packages..." -ForegroundColor Green
pip install -e "$PSScriptRoot\..\packages\shared-python\" 2>$null

# Add shared package to PYTHONPATH
$env:PYTHONPATH = "$PSScriptRoot\..\packages\shared-python\;$env:PYTHONPATH"
[Environment]::SetEnvironmentVariable("PYTHONPATH", $env:PYTHONPATH, "Process")

# Install dev dependencies
pip install -r "$PSScriptRoot\..\requirements.txt" 2>$null

# Setup .env if not exists
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example - please configure your API keys" -ForegroundColor Yellow
}

# Start infrastructure services
Write-Host "`nStarting infrastructure (PostgreSQL, Redis, MongoDB, Qdrant, Neo4j, RabbitMQ)..." -ForegroundColor Green
docker-compose up -d postgres redis mongodb qdrant neo4j rabbitmq

Write-Host "`nDev environment ready!" -ForegroundColor Cyan
Write-Host "Run individual services with: uvicorn src/services/<name>/main:app --reload" -ForegroundColor Gray
