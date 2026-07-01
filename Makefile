.PHONY: dev build up down test lint clean

dev:
	powershell -File scripts/dev.ps1

build:
	powershell -File scripts/build.ps1

up:
	docker-compose up -d

down:
	docker-compose down

test:
	powershell -File scripts/test.ps1

lint:
	ruff check src/
	black --check src/

clean:
	powershell -File scripts/clean.ps1
