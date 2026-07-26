.PHONY: dev test validate safety-eval migrate lint seed clean help

help:
	@echo "Usage:"
	@echo "  make dev         - Start all services with docker-compose"
	@echo "  make test        - Run all tests (Flutter + Django + FastAPI)"
	@echo "  make validate    - Full validation: lint + safety eval + all tests"
	@echo "  make safety-eval - Print the safety-classifier evaluation report"
	@echo "  make migrate     - Run Django migrations"
	@echo "  make lint        - Run linters (dart analyze + ruff + mypy)"
	@echo "  make seed        - Load dev fixtures"
	@echo "  make clean       - Remove build artifacts and containers"

dev:
	docker-compose up --build

test:
	@echo "Running Flutter tests..."
	cd mobile && flutter test
	@echo "Running Django tests..."
	@if [ -d "backend-django/venv" ]; then \
		cd backend-django && ./venv/bin/python -m pytest; \
	else \
		cd backend-django && python3 -m pytest; \
	fi
	@echo "Running FastAPI tests..."
	@if [ -d "backend-fastapi/venv" ]; then \
		cd backend-fastapi && ./venv/bin/python -m pytest; \
	else \
		cd backend-fastapi && python3 -m pytest; \
	fi

# One-command validation: linters, the safety-classifier evaluation report, and
# every test suite. See VALIDATION.md for the runbook (incl. the live end-to-end
# checks that need real keys/infra).
validate: lint safety-eval test

safety-eval:
	@echo "Running safety classifier evaluation..."
	@if [ -d "backend-fastapi/venv" ]; then \
		cd backend-fastapi && ./venv/bin/python -m tests.validation.test_safety_eval; \
	else \
		cd backend-fastapi && python3 -m tests.validation.test_safety_eval; \
	fi

migrate:
	docker-compose exec django python manage.py migrate

lint:
	@echo "Linting Flutter..."
	cd mobile && flutter analyze
	@echo "Linting Python (Django)..."
	cd backend-django && ruff check .
	@echo "Linting Python (FastAPI)..."
	cd backend-fastapi && ruff check .

seed:
	docker-compose exec django python manage.py loaddata fixtures/*.json

clean:
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
