# Build script
param(
    [string]$Service = "all"
)

Write-Host "=== Building AITAONHANVATAO ===" -ForegroundColor Cyan

if ($Service -eq "all") {
    Write-Host "Building all Docker images..." -ForegroundColor Green
    docker-compose build
}
else {
    Write-Host "Building $Service..." -ForegroundColor Green
    docker-compose build $Service
}

Write-Host "Build complete!" -ForegroundColor Cyan
