PYTHON ?= ./.venv/bin/python
PIP ?= ./.venv/bin/pip
UV ?= ./.venv/bin/uv
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8800
FRONTEND_DIR := app/frontend
COMMIT_MSG ?= Update Xpotify local media manager

.PHONY: help setup backend frontend test build audit check lock status pull push git-update clean

help:
	@echo "Xpotify shortcuts"
	@echo ""
	@echo "Setup:"
	@echo "  make setup        Create .venv, install backend deps, install frontend deps"
	@echo ""
	@echo "Run:"
	@echo "  make backend      Run FastAPI backend on $(BACKEND_HOST):$(BACKEND_PORT)"
	@echo "  make frontend     Run Vite frontend"
	@echo ""
	@echo "Verify:"
	@echo "  make test         Run backend app tests"
	@echo "  make build        Build frontend"
	@echo "  make audit        Run npm audit"
	@echo "  make check        Run test + build + audit"
	@echo "  make lock         Refresh uv.lock"
	@echo ""
	@echo "Git:"
	@echo "  make status       Show git status"
	@echo "  make pull         Pull latest origin/main"
	@echo "  make push         Push current branch"
	@echo "  make git-update   Stage all, commit with COMMIT_MSG, push"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        Remove generated caches/build outputs"

setup:
	@test -x "$(PYTHON)" || /opt/homebrew/bin/python3.11 -m venv .venv || python -m venv .venv
	$(PIP) install -e . pytest pytest-asyncio "httpx>=0.24,<0.25" uv
	cd $(FRONTEND_DIR) && npm install

backend:
	$(PYTHON) -m uvicorn app.backend.main:app --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload

frontend:
	cd $(FRONTEND_DIR) && npm run dev

test:
	$(PYTHON) -m pytest tests/app_backend -q

build:
	cd $(FRONTEND_DIR) && npm run build

audit:
	cd $(FRONTEND_DIR) && npm audit --audit-level=moderate

check: test build audit

lock:
	$(UV) lock

status:
	git status --short --branch

pull:
	git pull --ff-only origin main

push:
	git push origin HEAD

git-update: check
	git add .
	git commit -m "$(COMMIT_MSG)"
	git push origin HEAD

clean:
	find . -path ./.venv -prune -o -path ./$(FRONTEND_DIR)/node_modules -prune -o -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage $(FRONTEND_DIR)/dist

