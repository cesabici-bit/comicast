.PHONY: help install lint format types test smoke deps-verify check-all clean

PYTHON := python
VENV := .venv
ifeq ($(OS),Windows_NT)
    VENV_BIN := $(VENV)/Scripts
else
    VENV_BIN := $(VENV)/bin
endif

help:
	@echo "make install      - install package + dev deps"
	@echo "make lint         - ruff check"
	@echo "make format       - ruff format"
	@echo "make types        - mypy strict"
	@echo "make test         - pytest"
	@echo "make smoke        - smoke test E2E"
	@echo "make deps-verify  - check verified-deps.toml"
	@echo "make check-all    - all of the above"
	@echo "make clean        - remove caches and build artifacts"

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install -U pip
	$(VENV_BIN)/pip install -e ".[dev]"

lint:
	$(VENV_BIN)/ruff check src tests

format:
	$(VENV_BIN)/ruff format src tests

types:
	$(VENV_BIN)/mypy src

test:
	$(VENV_BIN)/pytest -m "not slow"

test-all:
	$(VENV_BIN)/pytest

smoke:
	$(VENV_BIN)/pytest -m golden -v

deps-verify:
	$(VENV_BIN)/python -m comicast.tools.verify_deps

check-all: lint types test deps-verify
	@echo "All checks passed."

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	rm -rf src/comicast.egg-info build dist
	find . -type d -name __pycache__ -exec rm -rf {} +
