.PHONY: quality quality-backend quality-frontend install-hooks help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  quality          Exécute toute la chaîne qualité (backend + frontend)"
	@echo "  quality-backend  Format (black), lint (ruff), types (mypy), tests (pytest)"
	@echo "  quality-frontend Svelte check, tests (vitest), build, validation design"
	@echo "  install-hooks    Active le hook pre-commit (qualité automatique avant chaque commit)"

quality: quality-backend quality-frontend

quality-backend:
	@echo "=== Backend: format (black) ==="
	uv run black --check app/ tests/
	@echo "=== Backend: lint (ruff) ==="
	uv run ruff check app/ tests/
	@echo "=== Backend: types (mypy) ==="
	uv run mypy app/ tests/
	@echo "=== Backend: tests (pytest --cov-fail-under=80) ==="
	uv run pytest --cov=app --cov-fail-under=80 --cov-report=term-missing
	@echo "=== Backend: OK ==="

install-hooks:
	@echo "🔗 Activation du hook pre-commit (.githooks/pre-commit)..."
	git config core.hooksPath .githooks
	@echo "✅ Hook installé — make quality s'exécutera automatiquement avant chaque commit."

quality-frontend:
	@echo "=== Frontend: Svelte check ==="
	cd frontend && npm run check
	@echo "=== Frontend: Tests (vitest) ==="
	cd frontend && npm run test
	@echo "=== Frontend: Build ==="
	cd frontend && npm run build
	@echo "=== Frontend: Validation design system ==="
	cd frontend && npm run validate:design
	@echo "=== Frontend: OK ==="