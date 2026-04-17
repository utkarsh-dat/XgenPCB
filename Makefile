.PHONY: help dev dev-backend dev-frontend db-up db-down db-migrate db-seed test lint clean

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PCB Builder - Build Automation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Infrastructure ────────────────────────────────────────────

db-up: ## Start all infrastructure services
	docker-compose up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 5
	@echo "✅ Infrastructure is up"
	@echo "   PostgreSQL: localhost:5432"
	@echo "   Redis:      localhost:6379"
	@echo "   Elastic:    localhost:9200"
	@echo "   MinIO:      localhost:9000 (console: 9001)"
	@echo "   pgAdmin:    localhost:5050"

db-down: ## Stop all infrastructure services
	docker-compose down

db-reset: ## Reset all data volumes (DESTRUCTIVE)
	docker-compose down -v
	@echo "🗑️  All data volumes removed"

# ── Database ──────────────────────────────────────────────────

db-migrate: ## Run database migrations
	@echo "🔄 Running migrations..."
	cd backend && python -m scripts.migrate
	@echo "✅ Migrations complete"

db-seed: ## Seed database with sample data
	@echo "🌱 Seeding database..."
	cd backend && python -m scripts.seed
	@echo "✅ Seed complete"

# ── Development ───────────────────────────────────────────────

dev: db-up ## Start full development environment
	@echo "🚀 Starting development servers..."
	cd backend && make dev &
	cd frontend/apps/web && npm run dev &
	@echo "✅ Dev servers starting..."
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:5173"
	@echo "   API Docs: http://localhost:8000/docs"

dev-backend: ## Start backend services only
	cd backend && make dev

dev-frontend: ## Start frontend only
	cd frontend/apps/web && npm run dev

# ── Backend Services ─────────────────────────────────────────

install-backend: ## Install Python dependencies
	cd backend && pip install -e ".[dev]"

install-frontend: ## Install frontend dependencies
	cd frontend/apps/web && npm install

install: install-backend install-frontend ## Install all dependencies

# ── Testing ───────────────────────────────────────────────────

test: ## Run all tests
	cd backend && pytest -v
	cd frontend/apps/web && npm test

test-backend: ## Run backend tests only
	cd backend && pytest -v --cov=services --cov=shared

test-frontend: ## Run frontend tests only
	cd frontend/apps/web && npm test

# ── Linting ───────────────────────────────────────────────────

lint: ## Run linters
	cd backend && ruff check . && ruff format --check .
	cd frontend/apps/web && npm run lint

lint-fix: ## Fix lint errors
	cd backend && ruff check --fix . && ruff format .
	cd frontend/apps/web && npm run lint -- --fix

# ── Cleanup ───────────────────────────────────────────────────

clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@echo "🧹 Cleaned"
