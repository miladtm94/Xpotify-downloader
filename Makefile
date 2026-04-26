PYTHON ?= ./.venv/bin/python
PIP ?= ./.venv/bin/pip
UV ?= ./.venv/bin/uv
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8800
FRONTEND_DIR := app/frontend
COMMIT_MSG ?= Update LynkOo local media manager

.PHONY: help setup backend stop-backend frontend docker-up docker-down docker-logs test build audit check lock status pull push git-update clean

help:
	@echo "LynkOo shortcuts"
	@echo ""
	@echo "Setup:"
	@echo "  make setup        Create .venv, install backend deps, install frontend deps"
	@echo ""
	@echo "Run:"
	@echo "  make backend      Run FastAPI backend on $(BACKEND_HOST):$(BACKEND_PORT)"
	@echo "  make stop-backend Stop an existing LynkOo backend on $(BACKEND_PORT)"
	@echo "  make frontend     Run Vite frontend"
	@echo "  make docker-up    Run backend + frontend in Docker with hot reload"
	@echo "  make docker-down  Stop Docker dev services"
	@echo "  make docker-logs  Follow Docker dev logs"
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
	@command -v brew >/dev/null && brew install python@3.13 python-tk@3.13 || echo "Warning: Homebrew not found, skipping Python/tkinter installation"
	@test -x "$(PYTHON)" || /opt/homebrew/bin/python3.13 -m venv .venv || python3 -m venv .venv
	$(PIP) install -e . pytest pytest-asyncio "httpx>=0.24,<0.25" uv
	cd $(FRONTEND_DIR) && npm install

backend: stop-backend
	$(PYTHON) -m uvicorn app.backend.main:app --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload

stop-backend:
	@if command -v lsof >/dev/null; then \
		while true; do \
			pids=$$(lsof -tiTCP:$(BACKEND_PORT) -sTCP:LISTEN 2>/dev/null); \
			[ -n "$$pids" ] || break; \
			for pid in $$pids; do \
				command=$$(ps -p $$pid -o command= 2>/dev/null || true); \
				cwd=$$(lsof -a -p $$pid -d cwd -Fn 2>/dev/null | sed -n 's/^n//p'); \
				if echo "$$command" | grep -q "uvicorn.*app.backend.main:app" || [ "$$cwd" = "$(CURDIR)" ]; then \
					echo "Stopping existing backend on $(BACKEND_HOST):$(BACKEND_PORT) (PID $$pid)"; \
					if ! kill $$pid; then \
						echo "Could not stop backend PID $$pid. Stop it manually or run BACKEND_PORT=<port> make backend."; \
						exit 1; \
					fi; \
					for attempt in 1 2 3 4 5; do \
						sleep 1; \
						lsof -tiTCP:$(BACKEND_PORT) -sTCP:LISTEN 2>/dev/null | grep -q . || exit 0; \
					done; \
					echo "Backend PID $$pid did not exit after TERM; forcing it to stop"; \
					if ! kill -9 $$pid 2>/dev/null; then \
						echo "Could not force-stop backend PID $$pid. Stop it manually or run BACKEND_PORT=<port> make backend."; \
						exit 1; \
					fi; \
					sleep 1; \
				else \
					echo "Port $(BACKEND_PORT) is already used by PID $$pid: $$command"; \
					echo "Stop that process or run BACKEND_PORT=<port> make backend."; \
					exit 1; \
				fi; \
			done; \
		done; \
	else \
		echo "lsof not available; skipping backend port cleanup."; \
	fi

frontend:
	cd $(FRONTEND_DIR) && npm run dev

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

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
