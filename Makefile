.PHONY: help install dev test lint format clean docker-up docker-down docker-build \
        li-up li-down li-build li-test li-shell li-logs

help:
	@echo "LI Engine - Lightweight Integration Engine"
	@echo ""
	@echo "Usage:"
	@echo "  make install      Install production dependencies"
	@echo "  make dev          Install development dependencies"
	@echo "  make test         Run tests (host)"
	@echo "  make lint         Run linters"
	@echo "  make format       Format code"
	@echo "  make clean        Clean build artifacts"
	@echo ""
	@echo "Docker Commands (all dev runs in Docker):"
	@echo "  make li-up        Start LI Engine dev stack (9300-9320 ports)"
	@echo "  make li-down      Stop LI Engine dev stack"
	@echo "  make li-build     Build LI Engine Docker image"
	@echo "  make li-test      Run tests in Docker"
	@echo "  make li-shell     Open shell in LI Engine container"
	@echo "  make li-logs      View LI Engine logs"
	@echo ""
	@echo "Legacy Docker Commands:"
	@echo "  make docker-up    Start Docker services (old)"
	@echo "  make docker-down  Stop Docker services (old)"
	@echo "  make docker-build Build Docker image (old)"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v --cov=hie --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

lint:
	ruff check hie/ tests/
	mypy hie/

format:
	ruff format hie/ tests/
	ruff check --fix hie/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f hie

run:
	python -m hie.cli run --config config/example.yaml --log-level DEBUG --log-format console

init-config:
	python -m hie.cli init --output config/my-config.yaml

validate-config:
	python -m hie.cli validate --config config/production.yaml

# =============================================================================
# LI Engine Docker Commands (all development runs in Docker)
# Port range: 9300-9350
# =============================================================================

li-build:
	docker-compose -f docker-compose.dev.yml build

li-up:
	docker-compose -f docker-compose.dev.yml up -d
	@echo ""
	@echo "LI Engine dev stack started:"
	@echo "  - LI Engine:    http://localhost:9300 (HTTP), localhost:9301 (MLLP)"
	@echo "  - Management:   http://localhost:9302"
	@echo "  - PostgreSQL:   localhost:9310"
	@echo "  - Redis:        localhost:9311"
	@echo "  - MLLP Echo:    localhost:9320"
	@echo ""
	@echo "Run 'make li-shell' to open a shell in the container"
	@echo "Run 'make li-test' to run tests"

li-down:
	docker-compose -f docker-compose.dev.yml down

li-restart:
	docker-compose -f docker-compose.dev.yml restart li-engine

li-logs:
	docker-compose -f docker-compose.dev.yml logs -f li-engine

li-shell:
	docker-compose -f docker-compose.dev.yml exec li-engine /bin/bash

li-test:
	docker-compose -f docker-compose.dev.yml run --rm test pytest tests/ -v --tb=short

li-test-li:
	docker-compose -f docker-compose.dev.yml run --rm test pytest tests/li/ -v --tb=short

li-test-unit:
	docker-compose -f docker-compose.dev.yml run --rm test pytest tests/ -v --tb=short -m "not integration"

li-test-integration:
	docker-compose -f docker-compose.dev.yml run --rm test pytest tests/ -v --tb=short -m "integration"

li-python:
	docker-compose -f docker-compose.dev.yml exec li-engine python

li-clean:
	docker-compose -f docker-compose.dev.yml down -v --remove-orphans
