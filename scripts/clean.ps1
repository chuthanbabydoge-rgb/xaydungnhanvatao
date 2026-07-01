# Clean build artifacts
Write-Host "=== Cleaning ===" -ForegroundColor Cyan

# Python cache
Get-ChildItem -Path "." -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Python bytecode
Get-ChildItem -Path "." -Recurse -File -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue

# Build artifacts
Remove-Item -Path "dist", "build" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Clean complete!" -ForegroundColor Cyan
