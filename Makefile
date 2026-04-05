.PHONY: dev test migrate lint seed clean help

help:
	@echo "Usage:"
	@echo "  make dev      - Start all services with docker-compose"
	@echo "  make test     - Run all tests (Flutter + Django + FastAPI)"
	@echo "  make migrate  - Run Django migrations"
	@echo "  make lint     - Run linters (dart analyze + ruff + mypy)"
	@echo "  make seed     - Load dev fixtures"
	@echo "  make clean    - Remove build artifacts and containers"

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
