# Bazaar Watch
#
# There are no stubs:
# if a target exists, it does something real.

SHELL := bash
.DEFAULT_GOAL := help

# Non-default ports throughout, so nothing collides with a local install.
export POSTGRES_PORT ?= 55432
export REDIS_PORT    ?= 56379
export API_PORT      ?= 58000
export CONSOLE_PORT  ?= 53000
export WEB_PORT      ?= 53001

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install tooling (uv, pnpm deps, pre-commit)
	@command -v uv >/dev/null || { echo "uv not found: https://docs.astral.sh/uv/"; exit 1; }
	@command -v pnpm >/dev/null || { echo "pnpm not found: corepack enable"; exit 1; }
	uv tool install pre-commit --quiet || true
	uv tool install ruff --quiet || true
	pnpm install
	$(MAKE) hooks

.PHONY: hooks
hooks: ## Install git hooks
	pre-commit install --install-hooks

.PHONY: fmt
fmt: ## Format
	ruff format .
	ruff check --fix .

.PHONY: lint
lint: ## Lint
	ruff format --check .
	ruff check .

.PHONY: gates
gates: ## Run the custom silent-corruption gates
	@bash tools/gates/no-naive-casing.sh
	@bash tools/gates/no-float-money.sh
	@bash tools/gates/no-naive-datetime.sh
	@echo "gates passed"

.PHONY: check
check: ## Everything CI runs
	$(MAKE) lint
	$(MAKE) gates
	pre-commit run --all-files
