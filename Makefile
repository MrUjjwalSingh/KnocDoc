.PHONY: up down seed test lint migrate logs shell-api shell-db

# Start all services
up:
	docker compose up --build -d

# Stop all services
down:
	docker compose down

# Run DB migrations
migrate:
	docker compose exec api alembic upgrade head

# Seed dummy data (adds --reset flag to wipe and re-seed)
seed:
	docker compose exec api python -m db.seed --reset

# Run backend tests
test-api:
	docker compose exec api pytest tests/ -v --tb=short

# Run frontend tests
test-web:
	cd apps/web && npm test

# Run all tests
test: test-api test-web

# Lint backend
lint-api:
	docker compose exec api ruff check app/ && black --check app/

# Lint frontend
lint-web:
	cd apps/web && npm run lint

# Lint all
lint: lint-api lint-web

# View logs
logs:
	docker compose logs -f

# Shell into API container
shell-api:
	docker compose exec api bash

# Shell into DB container
shell-db:
	docker compose exec db psql -U traveldoc -d traveldoc

# Full reset (wipe volumes and restart)
reset:
	docker compose down -v && docker compose up --build -d
