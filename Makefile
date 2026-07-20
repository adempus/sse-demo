# SSE State Demo — one-command fullstack dev + docker workflow.
#
# Quick start:  make up   (builds & runs the whole stack in Docker)
#               open http://localhost:8080

SHELL := /bin/bash
COMPOSE := docker compose
BACKEND_DIR := backend
FRONTEND_DIR := frontend

# Ensure pnpm (installed via corepack into ~/.local/bin) is reachable.
export PATH := $(HOME)/.local/bin:$(PATH)

.DEFAULT_GOAL := help

## ---- Docker (primary workflow) ----

.PHONY: up
up: ## Build and start the full stack (frontend on :8080)
	$(COMPOSE) up --build

.PHONY: start
start: up ## Alias for `up`

.PHONY: down
down: ## Stop and remove containers
	$(COMPOSE) down

.PHONY: clean
clean: ## Stop containers and remove the data volume
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Tail container logs
	$(COMPOSE) logs -f

## ---- Local dev (no Docker) ----

.PHONY: install
install: ## Install backend + frontend dependencies
	cd $(BACKEND_DIR) && uv sync
	cd $(FRONTEND_DIR) && pnpm install

.PHONY: dev-backend
dev-backend: ## Run backend with autoreload on :8000
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --port 8000

.PHONY: dev-frontend
dev-frontend: ## Run frontend dev server on :5173 (proxies /api to :8000)
	cd $(FRONTEND_DIR) && pnpm dev

## ---- Quality gates ----

.PHONY: lint
lint: ## Lint backend (ruff) + frontend (eslint)
	cd $(BACKEND_DIR) && uv run ruff check .
	cd $(FRONTEND_DIR) && pnpm lint

.PHONY: format
format: ## Format backend (ruff) + frontend (prettier)
	cd $(BACKEND_DIR) && uv run ruff format .
	cd $(FRONTEND_DIR) && pnpm format

.PHONY: typecheck
typecheck: ## Type-check backend (ty) + frontend (tsc)
	cd $(BACKEND_DIR) && uv run ty check
	cd $(FRONTEND_DIR) && pnpm exec tsc -b

.PHONY: test
test: ## Run backend (pytest) + frontend (vitest) tests
	cd $(BACKEND_DIR) && uv run pytest -q
	cd $(FRONTEND_DIR) && pnpm test

.PHONY: check
check: lint typecheck test ## Run all quality gates

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
