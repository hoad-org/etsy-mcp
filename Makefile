.PHONY: help install dev test coverage lint format type-check check security clean

help:
	@echo "Etsy MCP - Development Commands"
	@echo "==============================="
	@echo "make install      - Install dependencies"
	@echo "make dev          - Install dev dependencies"
	@echo "make test         - Run tests"
	@echo "make coverage     - Run tests with coverage report"
	@echo "make lint         - Run ruff linter"
	@echo "make format       - Format code with black"
	@echo "make type-check   - Run mypy type checking"
	@echo "make security     - Run bandit security scan"
	@echo "make check        - Run all checks (lint, format, type-check, security)"
	@echo "make clean        - Remove build artifacts and cache"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

lint:
	ruff check src tests

format:
	black src tests
	ruff check --fix src tests

type-check:
	mypy src

security:
	bandit -r src

check: lint type-check security
	@echo "All checks passed!"

clean:
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
