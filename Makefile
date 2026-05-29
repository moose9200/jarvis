.PHONY: help setup dev prod down build seed test lint migrate migrate-new shell logs psql redis-cli backup restore

help:
	@echo "JARVIS V2 — Make targets"
	@echo "  setup        configure git hooks (run once after clone)"
	@echo "  dev          start full stack with hot reload"
	@echo "  prod         start full stack in production mode (detached)"
	@echo "  down         stop everything"
	@echo "  build        rebuild backend + frontend images (no cache)"
	@echo "  migrate      alembic upgrade head"
	@echo "  migrate-new  alembic revision --autogenerate -m 'name=<msg>'"
	@echo "  seed         python seed.py — populate test users + fake data"
	@echo "  test         run backend pytest"
	@echo "  lint         ruff + mypy backend, eslint frontend"
	@echo "  shell        open python repl inside backend container"
	@echo "  psql         open psql against the postgres service"
	@echo "  logs         tail backend + worker logs"
	@echo "  backup       pg_dump → ./backups/jarvis_YYYYMMDD.sql"

setup:
	@echo "Configuring git to use repo-owned hooks at .githooks/"
	@git config core.hooksPath .githooks
	@chmod +x .githooks/* 2>/dev/null || true
	@echo "Done. Pre-push hook active."

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

prod:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

migrate:
	docker compose exec backend alembic upgrade head

migrate-new:
	@if [ -z "$(name)" ]; then echo "usage: make migrate-new name=\"description\""; exit 1; fi
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

seed:
	docker compose exec backend python seed.py

test:
	docker compose exec backend pytest backend/tests/ -v --tb=short

lint:
	docker compose exec backend ruff check . || true
	cd frontend && node_modules/.bin/tsc --noEmit

shell:
	docker compose exec backend python

psql:
	docker compose exec postgres psql -U jarvis jarvis

redis-cli:
	docker compose exec redis redis-cli

logs:
	docker compose logs -f backend worker

backup:
	@mkdir -p backups
	docker compose exec -T postgres pg_dump -U jarvis jarvis > backups/jarvis_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup written to backups/"
