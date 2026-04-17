.PHONY: dev test lint

dev: ## Start all backend services in development mode
	uvicorn services.gateway.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir services --reload-dir shared

test: ## Run tests
	pytest -v --cov=services --cov=shared

lint: ## Lint code
	ruff check . && ruff format --check .

lint-fix: ## Fix lint errors
	ruff check --fix . && ruff format .
