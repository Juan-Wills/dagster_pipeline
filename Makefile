.PHONY: help install test test-unit test-integration test-coverage test-fast clean lint format

help:
	@echo "Dagster Pipeline Test Commands"
	@echo "==============================="
	@echo ""
	@echo "install          Install all dependencies including test dependencies"
	@echo "test             Run all tests with coverage"
	@echo "test-unit        Run only unit tests"
	@echo "test-integration Run only integration tests"
	@echo "test-coverage    Run tests and generate HTML coverage report"
	@echo "test-fast        Run tests without coverage (faster)"
	@echo "test-watch       Run tests in watch mode (requires pytest-watch)"
	@echo "lint             Run code linting (black, flake8)"
	@echo "format           Format code with black"
	@echo "clean            Clean up test artifacts and cache"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -e .
	pip install --group dev --group dagster --group google-api --group databases
	pip install pytest pytest-cov pytest-mock
	@echo "Dependencies installed successfully!"

test:
	@echo "Running all tests with coverage..."
	pytest --cov=dagster_pipeline --cov-report=term-missing --cov-report=html -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/test_assets.py tests/test_resources.py tests/test_sensors.py tests/test_schedules.py -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/test_integration.py -v

test-coverage:
	@echo "Running tests and generating coverage report..."
	pytest --cov=dagster_pipeline --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

test-fast:
	@echo "Running tests without coverage (fast mode)..."
	pytest -v --tb=short

test-watch:
	@echo "Running tests in watch mode..."
	pytest-watch

test-specific:
	@echo "Run a specific test file or test case"
	@echo "Usage: make test-specific TEST=tests/test_assets.py::TestExtractionAssets::test_extracted_csv_files_success"
	pytest $(TEST) -v

lint:
	@echo "Running linters..."
	@echo "Checking code style with black..."
	black --check dagster_pipeline/ tests/ || true
	@echo "Checking with flake8..."
	flake8 dagster_pipeline/ tests/ --count --max-line-length=127 --statistics || true

format:
	@echo "Formatting code with black..."
	black dagster_pipeline/ tests/
	@echo "Code formatted!"

clean:
	@echo "Cleaning up..."
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf **/__pycache__
	rm -rf **/*.pyc
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup complete!"

# Database testing commands
test-db:
	@echo "Running database tests..."
	pytest tests/test_database_connections.py -v

start-services:
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	sleep 5
	@echo "Services started!"

stop-services:
	@echo "Stopping Docker services..."
	docker-compose down
	@echo "Services stopped!"

test-with-services: start-services test stop-services

# CI/CD simulation
ci:
	@echo "Running CI/CD pipeline simulation..."
	make clean
	make lint
	make test
	@echo "CI/CD simulation complete!"

# Development helpers
dev-setup: install
	@echo "Setting up development environment..."
	pre-commit install || true
	@echo "Development environment ready!"

# Coverage threshold check
test-coverage-threshold:
	@echo "Running tests and checking coverage threshold (80%)..."
	pytest --cov=dagster_pipeline --cov-report=term --cov-fail-under=80
