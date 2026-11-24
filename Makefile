.PHONY: help clean clean-build clean-pyc clean-test lint format typecheck test test-all coverage docs servedocs dist install develop pre ruff
.DEFAULT_GOAL := help

help:
	@awk -F ':.*## ' '/^[a-z-]+:.*## / { printf "%-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -rf build/ dist/ .eggs/ src/*.egg-info

clean-pyc: ## remove compiled Python files
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +

clean-test: ## remove test and coverage artifacts
	rm -rf .coverage coverage.xml htmlcov/ .pytest_cache/

lint: ## check style with Ruff
	uv run --extra dev ruff check .
	uv run --extra dev ruff format --check .

format: ## auto-fix style issues with Ruff
	uv run --extra dev ruff check --fix .
	uv run --extra dev ruff format .

typecheck: ## check types with mypy
	uv run --extra dev mypy

test: ## run tests with both plotting backends installed
	uv run --extra test --extra plotly pytest

test-all: ## run tests on each Python version in the CI matrix
	@status=0; for version in 3.10 3.11 3.12 3.13; do \
		uv run --isolated --python "$$version" --extra test --extra plotly pytest || status=1; \
	done; exit "$$status"

coverage: ## generate terminal and HTML coverage reports
	uv run --extra test --extra plotly pytest --cov --cov-report=term-missing --cov-report=html

docs: ## build the MkDocs documentation
	uvx --python 3.12 --with-requirements requirements-docs.txt mkdocs build --strict

servedocs: ## preview the MkDocs documentation locally
	uvx --python 3.12 --with-requirements requirements-docs.txt mkdocs serve

dist: ## build the source distribution and wheel
	uv build

install: ## install the package into the project environment
	uv sync --no-editable

develop: ## install the editable package and development tools
	uv sync --extra dev --extra plotly

pre: ## run all pre-commit hooks
	uv run --extra dev pre-commit run --all-files

ruff: lint
