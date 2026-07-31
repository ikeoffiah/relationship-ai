.PHONY: dev test validate scenarios e2e safety-eval migrate lint seed clean help

help:
	@echo "Usage:"
	@echo "  make dev         - Start all services with docker-compose"
	@echo "  make test        - Run all tests (Flutter + Django + FastAPI)"
	@echo "  make validate    - Full validation: lint + safety eval + all tests"
	@echo "  make scenarios   - Replay intelligence scenarios against a running stack"
	@echo "  make e2e         - Two-process couple-thread checks against a running stack"
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
#
# `scenarios` is deliberately NOT in here yet. docs/intelligence-test-plan.md §4
# says to wire it in "once green", and it is not: three of its assertions
# describe behaviour we have decided is wrong rather than behaviour that broke,
# and they are meant to stay red until somebody decides what to do about them.
# Adding a permanently-failing suite to `validate` teaches people to ignore
# `validate`, which costs more than the coverage gains. Add it here on the day
# the last of those is settled.
validate: lint safety-eval test

# Scripted conversations against a running stack. Needs docker compose up and a
# real OPENAI_API_KEY: the point is what the live model actually decides, which
# is not something a mock can answer.
#   make scenarios                  — all of them
#   make scenarios ARGS="S1 quiet"  — one scenario, or one group
scenarios:
	@echo "Replaying intelligence scenarios against the running stack..."
	backend-django/venv/bin/python scripts/e2e/run_scenarios.py $(ARGS)

# The other live suite: two processes, two sockets, and the plumbing between
# them. Complementary rather than overlapping — that one checks that a receipt
# written by one process reaches the other's socket, this one checks what the
# intelligence decides across a whole conversation.
e2e:
	backend-django/venv/bin/python scripts/e2e/couple_thread.py

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
