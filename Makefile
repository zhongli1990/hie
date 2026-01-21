.PHONY: help install dev test lint format clean docker-up docker-down docker-build

help:
	@echo "HIE - Healthcare Integration Engine"
	@echo ""
	@echo "Usage:"
	@echo "  make install      Install production dependencies"
	@echo "  make dev          Install development dependencies"
	@echo "  make test         Run tests"
	@echo "  make lint         Run linters"
	@echo "  make format       Format code"
	@echo "  make clean        Clean build artifacts"
	@echo "  make docker-up    Start Docker services"
	@echo "  make docker-down  Stop Docker services"
	@echo "  make docker-build Build Docker image"

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
