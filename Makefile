# ============================================
# XgenPCB - Makefile
# ============================================

.PHONY: help build up down restart logs shell migrate test clean dev prod

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "XgenPCB - Available Commands:"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ── Docker Compose ──────────────────────────────────────────

build: ## Build all Docker images
	docker-compose build --no-cache

up: ## Start all services in background
	docker-compose up -d

up-logs: ## Start all services with logs
	docker-compose up

down: ## Stop all services
	docker-compose down

down-volumes: ## Stop all services and remove volumes
	docker-compose down -v

restart: ## Restart all services
	docker-compose restart

# ── Development ─────────────────────────────────────────────

dev: ## Start development environment
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

dev-logs: ## Start development environment with logs
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

dev-down: ## Stop development environment
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# ── Individual Services ─────────────────────────────────────

backend: ## Start backend only
	docker-compose up -d postgres redis backend

backend-logs: ## Show backend logs
	docker-compose logs -f backend

frontend: ## Start frontend only
	docker-compose up -d frontend nginx

frontend-logs: ## Show frontend logs
	docker-compose logs -f frontend nginx

workers: ## Start Celery workers
	docker-compose up -d celery-worker-ai celery-worker-eda celery-beat

workers-logs: ## Show Celery worker logs
	docker-compose logs -f celery-worker-ai celery-worker-eda celery-beat

# ── Database ────────────────────────────────────────────────

migrate: ## Run database migrations
	docker-compose exec backend python -m alembic upgrade head

migrate-dev: ## Run database migrations (development)
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m alembic upgrade head

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U pcbbuilder -d pcbbuilder

db-reset: ## Reset database (DANGER: All data lost!)
	docker-compose down -v postgres
	docker-compose up -d postgres
	@sleep 5
	$(MAKE) migrate

# ── Testing ─────────────────────────────────────────────────

test: ## Run backend tests
	docker-compose exec backend python -m pytest tests/ -v --cov=shared --cov-report=term-missing

test-fast: ## Run tests without coverage
	docker-compose exec backend python -m pytest tests/ -v

# ── Monitoring ──────────────────────────────────────────────

logs: ## Show all logs
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-frontend: ## Show frontend logs
	docker-compose logs -f frontend nginx

logs-workers: ## Show worker logs
	docker-compose logs -f celery-worker-ai celery-worker-eda

status: ## Show service status
	docker-compose ps

# ── Shell Access ────────────────────────────────────────────

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-db: ## Open shell in database container
	docker-compose exec postgres /bin/bash

shell-redis: ## Open Redis CLI
	docker-compose exec redis redis-cli

# ── Cleanup ─────────────────────────────────────────────────

clean: ## Remove stopped containers, unused networks, images
	docker system prune -f

docker-compose down -v --remove-orphans

purge: ## Full cleanup including all volumes and images
	docker-compose down -v --rmi all --remove-orphans
	docker system prune -af --volumes

# ── Utilities ───────────────────────────────────────────────

api-docs: ## Open API documentation
	@echo "API Docs: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"

grafana: ## Open Grafana dashboard
	@echo "Grafana: http://localhost:3000"

minio-console: ## Open MinIO console
	@echo "MinIO Console: http://localhost:9001"

health: ## Check all service health
	@echo "Checking services..."
	@curl -s http://localhost/health | jq . || true
	@curl -s http://localhost:8000/health | jq . || true
	@curl -s http://localhost:8000/health/deep | jq . || true

# ── Production ──────────────────────────────────────────────

prod-build: ## Build production images
	docker-compose -f docker-compose.yml build

prod-up: ## Start production environment
	docker-compose -f docker-compose.yml up -d

prod-down: ## Stop production environment
	docker-compose -f docker-compose.yml down

prod-logs: ## Show production logs
	docker-compose -f docker-compose.yml logs -f

# ── Local Development (without Docker) ──────────────────────

dev-local: ## Start local development (backend + frontend separately)
	@echo "Starting backend..."
	cd backend && python -m uvicorn services.gateway.main:app --reload --port 8000 &
	@echo "Starting frontend..."
	cd frontend/apps/web && npm run dev &
	@echo "Services started!"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"

install: ## Install all dependencies locally
	cd backend && pip install -e .
	cd frontend/apps/web && npm install
