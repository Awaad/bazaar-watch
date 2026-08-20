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
	uv sync --all-groups
	pnpm install
	$(MAKE) hooks

.PHONY: hooks-run
hooks-run: ## Run every hook against all files. Verifies, never modifies.
	uv run pre-commit run --all-files

.PHONY: hooks
hooks: ## Install git hooks
	uv run pre-commit install --install-hooks

.PHONY: fmt
fmt: ## Fix everything a tool can fix
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: lint
lint: ## Lint
	uv run ruff format --check .
	uv run ruff check .

.PHONY: gates
gates: ## Run the custom silent-corruption gates
	@bash tools/gates/no-naive-casing.sh
	@bash tools/gates/no-float-money.sh
	@bash tools/gates/no-naive-datetime.sh
	@uv run python tools/gates/updated-at-triggers.py
	@uv run python tools/gates/workflow-jobs.py
	@uv run python tools/gates/enum-parity.py
	@uv run python tools/gates/branch-scope.py
	@echo "gates passed"

# --- local stack -----------------------------------------------------------

.PHONY: env
env: ## Create .env from the template if absent
	@test -f .env || { cp .env.example .env; \
		echo ".env created. Set POSTGRES_PASSWORD before 'make up'."; }
	@test -f .env && echo ".env present"

.PHONY: up
up: ## Start postgres and redis, wait until healthy
	docker compose up -d --build --wait
	@$(MAKE) --no-print-directory db-versions

.PHONY: down
down: ## Stop the stack, keep volumes
	docker compose down

.PHONY: ps
ps: ## Service status
	docker compose ps

.PHONY: logs
logs: ## Tail logs
	docker compose logs -f --tail=100

.PHONY: psql
psql: ## Interactive psql
	docker compose exec -it postgres psql -U $${POSTGRES_USER:-bazaarwatch} -d $${POSTGRES_DB:-bazaarwatch}

.PHONY: redis-cli
redis-cli: ## Interactive redis-cli
	docker compose exec -it redis redis-cli

.PHONY: db-versions
db-versions: ## Report installed extension versions
	@echo "image build recorded:"
	@docker compose exec -T postgres cat /etc/bazaarwatch-extension-versions 2>/dev/null \
		| sed 's/^/  /' || echo "  (container not running)"
	@echo "server reports:"
	@docker compose exec -T postgres psql -U $${POSTGRES_USER:-bazaarwatch} \
		-d $${POSTGRES_DB:-bazaarwatch} -At \
		-c "SELECT '  ' || extname || '=' || extversion FROM pg_extension ORDER BY extname;" \
		2>/dev/null || echo "  (not reachable)"

.PHONY: db-reset
db-reset: ## Destroy volumes and rebuild. All local data is lost.
	@printf 'This destroys the local database and redis volumes. Continue? [y/N] '; \
		read ans; [ "$$ans" = "y" ] || { echo "aborted"; exit 1; }
	docker compose down -v
	$(MAKE) up


# --- migrations ---

.PHONY: migrate
migrate: ## Apply migrations
	uv run alembic -c apps/api/alembic.ini upgrade head

.PHONY: migrate-down
migrate-down: ## Roll back one migration
	uv run alembic -c apps/api/alembic.ini downgrade -1

.PHONY: migration
migration: ## Autogenerate a revision: make migration m="add x"
	@test -n "$(m)" || { echo 'usage: make migration m="description"'; exit 1; }
	uv run alembic -c apps/api/alembic.ini revision --autogenerate -m "$(m)"

.PHONY: db-current
db-current: ## Show the applied revision
	uv run alembic -c apps/api/alembic.ini current

# --- checks ----------------------------------------------------------------

.PHONY: typecheck
typecheck: ## mypy --strict over the API
	MYPYPATH=apps/api/src uv run mypy --strict apps/api/src/bazaarwatch

.PHONY: boundaries
boundaries: ## Enforce module boundaries (docs/01-architecture.md)
	PYTHONPATH=apps/api/src uv run lint-imports --config apps/api/pyproject.toml

.PHONY: test
test: ## Run the test suite. No database needed.
	uv run pytest -m "not integration"

.PHONY: test-integration
test-integration: ## Run the tests that need Postgres. Requires `make up`.
	uv run pytest -m integration

.PHONY: test-all
test-all: ## Everything, integration included. Requires `make up`.
	uv run pytest -m ""

.PHONY: api
api: ## Run the API against the local stack
	uv run python -m bazaarwatch

.PHONY: check
check: ## Everything CI runs
	$(MAKE) lint
	$(MAKE) gates
	$(MAKE) typecheck
	$(MAKE) boundaries
	$(MAKE) test
	$(MAKE) hooks-run
