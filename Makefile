.PHONY: help install install-dev test test-unit test-integration lint format clean deploy destroy

# Default target
help:
	@echo "Available commands:"
	@echo "  install       - Install production dependencies"
	@echo "  install-dev   - Install development dependencies"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code with black"
	@echo "  clean         - Clean up temporary files"
	@echo "  deploy        - Deploy infrastructure with Pulumi"
	@echo "  destroy       - Destroy infrastructure with Pulumi"

# Installation
install:
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt

# Testing
test: test-unit test-integration

test-unit:
	pytest tests/unit/ -v -m "not slow"

test-integration:
	pytest tests/integration/ -v -m "integration"

test-all:
	pytest tests/ -v

test-coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

# Code quality
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/

format-check:
	black --check src/ tests/

# Infrastructure
deploy:
	pulumi up

destroy:
	pulumi destroy

# Utilities
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/

# Development workflow
dev-setup: install-dev
	@echo "Development environment setup complete"
	@echo "Run 'make test' to verify everything works"

# CI/CD helpers
ci-test: install-dev lint test

validate: format-check lint test