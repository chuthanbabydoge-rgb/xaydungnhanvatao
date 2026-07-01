# Deploy script
param(
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev"
)

Write-Host "=== Deploying to $Environment ===" -ForegroundColor Cyan

switch ($Environment) {
    "dev" {
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    }
    "staging" {
        docker-compose -f docker-compose.yml up -d
    }
    "prod" {
        Write-Host "Production deploy not yet automated" -ForegroundColor Yellow
    }
}

Write-Host "Deploy complete!" -ForegroundColor Cyan
