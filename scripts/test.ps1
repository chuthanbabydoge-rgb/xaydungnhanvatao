# Run tests
Write-Host "=== Running Tests ===" -ForegroundColor Cyan

# Unit/integration tests
Write-Host "`nRunning integration tests..." -ForegroundColor Green
pytest tests/integration/ -v

# Stress tests (if locust is available)
if (Get-Command locust -ErrorAction SilentlyContinue) {
    Write-Host "`nRunning stress tests..." -ForegroundColor Green
    locust --headless --users 10 --spawn-rate 1 --run-time 30s --host http://localhost:8000
}

Write-Host "Tests complete!" -ForegroundColor Cyan
